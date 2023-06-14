import tkinter as tk
import winsound
import os, time


def tagger(directory, labels, buttons=None, filter=None):
    if filter:
        filelist = [f for f in os.listdir(directory) if f.split('-')[0] == filter]
    else:
        filelist = os.listdir(directory)
    if len(filelist) < 1: exit()
    i = 0

    results = {}

    def finish():
        print(results)
        window.destroy()

    window = tk.Tk()
    window.geometry("800x200")
    window.protocol("WM_DELETE_WINDOW", finish)

    currentSound = f"{directory}\{filelist[i]}"
    play = lambda: winsound.PlaySound(currentSound, winsound.SND_FILENAME|winsound.SND_ASYNC)
    button = tk.Button(window, text='Play ▶', command=play)
    name = tk.Label(window, text=currentSound.split('\\')[-1])
    button.config(font=("Courier", 20))
    name.config(font=("Courier", 20))

    button.pack()
    name.pack()

    labelFrame = tk.Frame()

    def nextFile():
        global i, currentSound
        i = i + 1
        if i >= len(filelist): exit()
        currentSound = f"{directory}\{filelist[i]}"
        name["text"] = currentSound.split('\\')[-1]
        time.sleep(.3)
        button.invoke()

    def labelAudio(currentSound, label):
        winsound.PlaySound(None, winsound.SND_FILENAME)
        results[currentSound] = label
        newName = f"{directory}\{label}-{'-'.join(filelist[i].split('-')[1:])}"  # TODO: Handle totally unlabelled tracks
        if newName != currentSound:
            os.rename(currentSound, newName)
            print(newName)
        nextFile()

    for l in labels:
        b = tk.Button(labelFrame, text=buttons[l], command= lambda l=l: labelAudio(currentSound, labels[l]))
        b.config(font=("Courier", 44))
        b.pack(side=tk.LEFT)

    labelFrame.pack()
    window.after(100, lambda :button.invoke())
    window.mainloop()


if __name__ == '__main__':
    tagger("d:\\Desktop\\amppd\\applause\\training_data\\hipstas\\original",
           labels = {0: "speech", 1: "music", 2: "applause", 3: "noise", 4: "silence"},
           buttons={0: "😀", 1: "🎵", 2: "👏", 3: "💨", 4: "🚫"},
           filter = "notapplause")
