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
        self.engine = None
        self.language_code = language_code
        self.model = model

        # We don't want to block the UI by our continuous transcription process
        self.thread = None

    def transcribe(self, language_code, model):
        with MicrophoneStream(RATE, CHUNK) as rawStream:
            self.engine = TranscriptionEngine(
                language_code, rawStream, model, RATE)

            self.engine.transcribe()

    def start(self):
        self.thread = threading.Thread(target=self.transcribe, name='transcribe', args=[
            self.language_code, self.model])
        self.thread.start()

    def stop(self):
        if (self.engine != None):
            self.engine.stopTranscription()

        # Wait until the thread stops
        self.thread.join()


class Switch():
    def __init__(self, button, implementation):
        self.button = button
        self.on = False
        self.button.configure(text='Start')
        self.button.configure(command=self.switch)
        self.implementation = implementation

    def switch(self):
        if (self.on):
            self.implementation.stop()
            self.on = False
            self.button.configure(text='Start')
        else:
            self.implementation.start()
            self.on = True
            self.button.configure(text='Stop')


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

    def close_window():
        service.stop()
        uiRoot.destroy()
    uiRoot.protocol("WM_DELETE_WINDOW", close_window)

    textView.after(50, updateUI, textView, model)
    textView.pack()

    stopButton = tkinter.Button(uiRoot)
    buttonDecoration = Switch(stopButton, service)
    stopButton.pack(fill=tkinter.X)

    uiRoot.mainloop()


if __name__ == '__main__':
    main()
