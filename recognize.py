from __future__ import division

import re
import sys

import tkinter
import threading
from stream import MicrophoneStream
from googletranscription import GoogleCloudTranscriptionService
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


def main():
    uiRoot = tkinter.Tk()
    uiRoot.configure(background="black")

    textView = tkinter.Text(uiRoot,  font=('Tiresias', 21))
    textView.configure(background='black')
    textView.tag_config('unstable', foreground='gray')
    textView.tag_config('stable', foreground='white')

    stopButton = tkinter.Button(
        uiRoot, text='stop', command=lambda: service.stopTranscription())
    stopButton.pack(fill=tkinter.X)

    textView.pack()

    language_code = 'nl-NL'  # a BCP-47 language tag

    model = Transcript()

    with MicrophoneStream(RATE, CHUNK) as rawStream:
        service = GoogleCloudTranscriptionService(
            language_code, rawStream, model, RATE)

        serviceThread = threading.Thread(
            target=service.transcribe, name='transcribe')
        serviceThread.start()

        textView.after(50, updateUI, textView, model)

        uiRoot.mainloop()


if __name__ == '__main__':
    main()
