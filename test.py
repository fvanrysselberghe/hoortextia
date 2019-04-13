import datetime
import tkinter
import time

def printIt(text):
    text.delete('1.0', 'end')
    for index in range(len(myText)):
        if (index < 2):
            text.insert('end', myText[index] + '\n', 'stable')
        else:
            text.insert('end', myText[index] + '\n', 'unstable')
    
    root.after(50, printIt, text)

root = tkinter.Tk()

text = tkinter.Text(root, font = ('Helvetica', 21))
text.tag_config('stable', foreground = 'black')
text.tag_config('unstable', foreground = 'gray')
text.pack()

myText = ['lijn 1', 'lijn 2', 'lijn 3', 'lijn 4', 'lijn 5']

root.after(50, printIt, text)

root.mainloop()
