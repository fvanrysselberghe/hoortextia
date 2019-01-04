from __future__ import division

import re
import sys

from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import pyaudio
from six.moves import queue
import time
import threading
import tkinter

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms


class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=1, rate=self._rate,
            input=True, frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def get(self):
        if self.closed:
            return None
        
        # Use a blocking get() to ensure there's at least one chunk of
        # data, and stop iteration if the chunk is None, indicating the
        # end of the audio stream.
        chunk = self._buff.get()
        if chunk is None:
            return None

        data = [chunk]

        # Consume whatever other data's still buffered.
        while True:
            try:
                chunk = self._buff.get(block=False)
                if chunk is None:
                    return
                data.append(chunk)
            except queue.Empty:
                break

        return data

class RequestPackage:
    """Yields the audio chunks for one request (i.e. less than 1 minute for google cloud)"""

    def __init__(self, stream):
        self._stream = stream
        self.closed = False

    def generator(self):
        while not self.closed:
            chunk = self._stream.get()
            if chunk is None:
                return

            yield b''.join(chunk)



class GoogleCloudTranscriptionService:
    def __init__(self, language_code, rawStream, model):
        self._client = speech.SpeechClient()
        
        config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=RATE,
            language_code=language_code,
            enable_automatic_punctuation=True)
        self._streaming_config = types.StreamingRecognitionConfig(
            config=config,
            interim_results=True)
        self._inputStream = rawStream

        self.model = model
        self._currentTranscriptKey = None

    def updateTranscript(self, responses):
        """Iterates through server responses and adds them to the model

        The responses passed is a generator that will block until a response
        is provided by the server.
    
        Each response may contain multiple results, and each result may contain
        multiple alternatives; for details, see https://goo.gl/tjCPAU. 
    
        In this case we add all results to the model. If there are multiple
        results their confidence level will vary. The presentation can use
        this for providing visual clues. For each result only the first 
        alternative is taken into account. A final result will result in
        a new transcript line in the model.
        """
        for response in responses:
            if not response.results:
                continue
    
            capture = None

            print('capture:')
            for result in response.results: 
                if not result.alternatives:
                    continue

                print('result:' + result.alternatives[0].transcript + ' ' + str(result.is_final) + '\n')

                if result.is_final:
                    confidence = 1.0
                else:
                    confidence = result.stability

                newCapture = TranscriptCapture(confidence, result.alternatives[0].transcript)
                if result.is_final:
                    newCapture.confidence = 1

                if not capture:
                    capture = newCapture
                else:
                    capture.add(newCapture)

                if self._currentTranscriptKey is None:
                    self._currentTranscriptKey = self.model.add( capture )
                else:
                    self.model.update( self._currentTranscriptKey, capture )
                
                if result.is_final:
                    self._currentTranscriptKey = None

    def transcribe(self):
            while True:
                singleRequest = RequestPackage(self._inputStream)
                audio_generator = singleRequest.generator()

                endRequestGuard = threading.Timer(50.0, stopGenerator, [singleRequest] )
                endRequestGuard.start()

                requests = (types.StreamingRecognizeRequest(audio_content=content)
                            for content in audio_generator)

                responses = self._client.streaming_recognize(self._streaming_config, requests)

                self.updateTranscript(responses)
                print('End request')


def stopGenerator(stream):
    print("Timer went off")
    stream.closed = True

def updateUI(textView, model):
    textView.delete('1.0', 'end')
    for item in model.lines:
        for itemDetail in item.parts:
            if itemDetail.confidence < 0.5:
                tag = 'unstable'
            else: 
                tag = 'stable'
            
            textView.insert('end', itemDetail.text, tag)
        textView.insert('end', '\n')

    textView.after(50, updateUI, textView, model)

class Transcript:
    def __init__(self):
        self.lines = []

    def add(self, item):
        self.lines.append(item)
        return len(self.lines) - 1 
    
    def update(self, key, item):
        if key >= len(self.lines):
            return
        else:
            self.lines[key] = item

class TranscriptCapture:
    def __init__(self, confidence, text):
        self.parts = [TranscriptItem(confidence, text)]
    
    def add(self, capture):
        self.parts.extend(capture.parts)

class TranscriptItem:
    def __init__(self, confidence, text):
        self.confidence = confidence
        self.text = text
        self.offset = 0

def main():
    uiRoot = tkinter.Tk()

    textView = tkinter.Text(uiRoot, width = uiRoot.winfo_screenwidth(), height = uiRoot.winfo_screenheight(), font = ('Helvetica', 21))
    textView.tag_config('unstable', foreground = 'gray')
    textView.tag_config('stable', foreground = 'black')
    textView.pack()

    language_code = 'nl-NL'  # a BCP-47 language tag

    model = Transcript()

    with MicrophoneStream(RATE, CHUNK) as rawStream:
        service = GoogleCloudTranscriptionService(language_code, rawStream, model)
        serviceThread = threading.Thread(target=service.transcribe, name='transcribe')
        serviceThread.start()

        textView.after(50, updateUI, textView, model)

        uiRoot.mainloop()

if __name__ == '__main__':
    main()