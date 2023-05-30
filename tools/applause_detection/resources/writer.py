import ffmpeg
import os

def save_json(dict, file, dir):
    import json
    with open(os.path.join(dir, f'{file[1]}.json'), "w") as out:
        json.dump(dict, out, indent=4, default = lambda x: x.__dict__)
