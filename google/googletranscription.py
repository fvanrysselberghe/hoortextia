from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import time
import threading
from transcript import TranscriptCapture


class RequestPackage:
    """Yields the audio chunks for one request (i.e. less than 1 minute for google cloud)"""

    def __init__(self, stream, queue=None):
        self._stream = stream
        self.closed = False
        self._queue = queue

    def generator(self):
        while not self.closed:
            chunk = self._stream.get()
            if chunk is None:
                return

            if self._queue is not None:
                self._queue.put(chunk)

            yield b''.join(chunk)


class TranscriptionEngine:
    def __init__(self, language_code, rawStream, model, rate):
        self._client = speech.SpeechClient()

        config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=rate,
            language_code=language_code,
            enable_automatic_punctuation=True)
        self._streaming_config = types.StreamingRecognitionConfig(
            config=config,
            interim_results=True)
        self._inputStream = rawStream

        self.model = model
        self._currentTranscriptKey = None
        self._active = True

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

                print(
                    'result:' + result.alternatives[0].transcript + ' ' + str(result.is_final) + '\n')

                if result.is_final:
                    confidence = 1.0
                else:
                    confidence = result.stability

                newCapture = TranscriptCapture(
                    confidence, result.alternatives[0].transcript)
                if result.is_final:
                    newCapture.confidence = 1

                if not capture:
                    capture = newCapture
                else:
                    capture.add(newCapture)

                if self._currentTranscriptKey is None:
                    self._currentTranscriptKey = self.model.add(capture)
                else:
                    self.model.update(self._currentTranscriptKey, capture)

                if result.is_final:
                    self._currentTranscriptKey = None

    def transcribe(self):
        while self._active:
            singleRequest = RequestPackage(self._inputStream)
            audio_generator = singleRequest.generator()

            endRequestGuard = threading.Timer(
                50.0, stopGenerator, [singleRequest])
            endRequestGuard.start()

            requests = (types.StreamingRecognizeRequest(audio_content=content)
                        for content in audio_generator)

            responses = self._client.streaming_recognize(
                self._streaming_config, requests)

            self.updateTranscript(responses)
            print('End request')

    def stopTranscription(self):
        self._active = False


def stopGenerator(stream):
    print("Timer went off")
    stream.closed = True
