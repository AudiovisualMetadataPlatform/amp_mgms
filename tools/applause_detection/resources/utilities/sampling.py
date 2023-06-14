import os
import shutil
import librosa
import random
from pydub import AudioSegment
from feature import labels


TARGET = 300

def count_type(dir):
    label_counter = {label: 0 for label in labels}

    files = os.listdir(dir)
    for f in files:
        label = f.split('-')[0]
        label_counter[label] += 1
    return label_counter


def find_available_name(dir, fname):
    copy_num = 1
    while True:
        if not os.path.exists(f"{dir}\\{fname[:-4]}_copy{copy_num}.wav"):
            fname = f"{fname[:-4]}_copy{copy_num}.wav"
            break
        copy_num += 1
    return fname


def take_three_seconds(in_file, in_dir, out_dir):
    # Extract three seconds if necessary, and put 3 second file in out dir
    audio = AudioSegment.from_file(f'{in_dir}\\{in_file}', format='wav')
    duration_in_milliseconds = len(audio)
    if duration_in_milliseconds > 3000:
        start = random.randint(0, duration_in_milliseconds-3000)
        three_seconds = audio[start:start+3000]
        new_name = f'{in_file[:-4]}_{start/1000}-{start/1000+3}.wav'
    else:
        three_seconds = audio
        new_name = in_file

    if os.path.exists(f'{out_dir}\\{new_name}'): # if the file exists, add suffix
        new_name = find_available_name(out_dir, new_name)

    three_seconds.export(f'{out_dir}\\{new_name}', format="wav")

hipstas = "d:\\Desktop\\amppd\\applause\\training_data\\hipstas\\relabelled"
#counts = count_type(hipstas)

training_dir = "d:\\Desktop\\amppd\\applause\\training_data\\full train"

# Speech
def select_from_dir(dir, num):
    files = [f for f in os.listdir(dir) if f[-4:len(f)] == '.wav']
    if len(files) >= num:
        keep = random.sample(files, num)
    else:
        keep = files
        difference = num - len(files)
        while difference > 0:
            toSample = min(difference, len(files))
            keep.extend(random.sample(files, toSample))
            difference -= toSample

    for f in keep:
        take_three_seconds(f, dir, training_dir)


# # Speech
# select_from_dir("d:\\Desktop\\amppd\\applause\\training_data\\hipstas\\relabelled\\speech", 150)
# select_from_dir("d:\\Desktop\\amppd\\applause\\training_data\\musan\\speech\\librivox", 75)
# select_from_dir("d:\\Desktop\\amppd\\applause\\training_data\\musan\\speech\\us-gov", 75)
# # Applause
# select_from_dir("d:\\Desktop\\amppd\\applause\\training_data\\hipstas\\relabelled\\applause", 300)
# # Noise
# select_from_dir("d:\Desktop\\amppd\\applause\\training_data\hipstas\\relabelled\\noise", 100)
# select_from_dir("d:\Desktop\\amppd\\applause\\training_data\musan\\noise\\free-sound", 100)
# select_from_dir("d:\Desktop\\amppd\\applause\\training_data\musan\\noise\sound-bible", 100)
# # Music
# select_from_dir("d:\\Desktop\\amppd\\applause\\training_data\\hipstas\\relabelled\\music", 20)
# select_from_dir("d:\Desktop\\amppd\\applause\\training_data\musan\music\\fma", 56)
# select_from_dir("d:\Desktop\\amppd\\applause\\training_data\musan\music\\fma-western-art", 56)
# select_from_dir("d:\Desktop\\amppd\\applause\\training_data\musan\music\\hd-classical", 56)
# select_from_dir("d:\Desktop\\amppd\\applause\\training_data\musan\music\\jamendo", 56)
# select_from_dir("d:\Desktop\\amppd\\applause\\training_data\musan\music\\rfm", 56)
# # Silence
# select_from_dir("d:\\Desktop\\amppd\\applause\\training_data\\hipstas\\relabelled\\silence", 300)
