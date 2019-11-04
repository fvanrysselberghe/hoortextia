from __future__ import division

import re
import sys

import tkinter
import threading
from stream import MicrophoneStream
from google.googletranscription import TranscriptionEngine
from transcript import Transcript

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms


def updateUI(textView, model):
    # Updates the transcript in the user interface
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


class TranscriptionService():
    def __init__(self, language_code, model):
        self.service = None

        # We don't want to block the UI by our continuous transcription process
        self.thread = threading.Thread(target=self.transcribe, name='transcribe', args=[
            language_code, model])

    def transcribe(self, language_code, model):
        with MicrophoneStream(RATE, CHUNK) as rawStream:
            self.service = TranscriptionEngine(
                language_code, rawStream, model, RATE)

            self.service.transcribe()

    def start(self):
        self.thread.start()

    def stop(self):
        if (self.service != None):
            self.service.stopTranscription()

        # Wait until the thread stops
        self.thread.join()


def main():
    uiRoot = tkinter.Tk()
    uiRoot.configure(background="black")

    textView = tkinter.Text(uiRoot,  font=('Tiresias', 21))
    textView.configure(background='black')
    textView.tag_config('unstable', foreground='gray')
    textView.tag_config('stable', foreground='white')

    language_code = 'nl-NL'  # a BCP-47 language tag
    model = Transcript()
    service = TranscriptionService(language_code, model)

    stopButton = tkinter.Button(
        uiRoot, text='stop', command=lambda: service.stop())
    stopButton.pack(fill=tkinter.X)

    textView.after(50, updateUI, textView, model)
    textView.pack()

    service.start()
    uiRoot.mainloop()


if __name__ == '__main__':
    main()
