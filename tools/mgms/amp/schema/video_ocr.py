import json
import csv

class VideoOcr:
    def __init__(self, media=None, frames = []):
        self.frames = frames
        if media is None:
            self.media = VideoOcrMedia()
        else:
            self.media = media
   
    # Return a new VideoOcr instance with the duplicate frames removed. 
    def dedupe(self, duration):
        frames = []
        current = None
        for frame in self.frames:
            if not frame.duplicate(current, duration):
                current = frame
                frames.append(current)
        return VideoOcr(self.media, frames)
          
    def toCsv(self, csvFile):
        # Write as csv
        with open(csvFile, mode='w') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(['Start Time', 'Text', 'Language', 'X Min', 'Y Min', 'X Max', 'Y Max', 'Score Type', 'Score Value'])
            for f in self.frames:
                for o in f.objects:
                    if o.score is not None:
                        scoreType = o.score.type
                        scoreValue = o.score.value
                    else:
                        scoreType = ''
                        scoreValue = ''
                    if o.language is not None:
                        language = o.language
                    else:
                        language = ''
                    v = o.vertices
                    csv_writer.writerow([f.start, o.text, language, v.xmin, v.ymin, v.xmax, v.ymax, scoreType, scoreValue])                    
        
    @classmethod
    def from_json(cls, json_data: dict):
        media = VideoOcrMedia.from_json(json_data["media"])                  
        frames = list(map(VideoOcrFrame.from_json, json_data["frames"]))
        return cls(media, frames)
                                 
class VideoOcrResolution:
    width = None
    height = None
    frames = []
    
    def __init__(self, width = None, height = None):
        self.width = width
        self.height = height

    @classmethod
    def from_json(cls, json_data):
        return cls(**json_data)

class VideoOcrMedia:
    filename = ""
    duration = 0
    frameRate = None
    numFrames = None
    resolution = VideoOcrResolution()

    def __init__(self, duration = 0, filename = "", frameRate = None, numFrames = None, resolution = None):
        self.duration = duration
        self.filename = filename
        self.frameRate = frameRate
        self.numFrames = numFrames
        self.resolution = resolution

    @classmethod
    def from_json(cls, json_data):
        return cls(**json_data)

class VideoOcrFrame:
    start = 0
    objects = []
    
    def __init__(self, start = None, objects = None):
        self.start = start
        self.objects = objects

    # Return true if the given (previous) frame is a duplicate of this one.
    # Frames are considered duplicate if they have the same texts and are consecutive within the given duration.
    def duplicate(self, frame, duration):
        # if the given frame is None return false
        if frame == None:
            return False
        
        # the given frame is assumed to be prior to this one; 
        # if the difference between the start time is beyond the duration, they are not considered consecutive, thus not duplicate
        if self.start - frame.start >= duration:
            return false
        
        # if the frames contain different number of objects, return false
        if len(self.objects) != len(frame.objects):
            return false
        
        # otherwise compare the text in each object
        # Note: In theory, the order of the objects could be random, in which case we can't compare by index, 
        # but need to match whole list for each object; an efficient way is to use hashmap.
        # For our use case, it's probably fine to assume that the VOCR tool will generate the list 
        # in the same order for duplicate frames
        for i, object in enumerate(self.objects):
            if not object.match(frame.objects[i]):
                # if one doesn't match return false
                return false
            
        # if all texts match return true
        return true
    
    @classmethod
    def from_json(cls, json_data: dict):                  
        objects = list(map(VideoOcrObject.from_json, json_data["objects"]))
        return cls(json_data["start"], objects)
    
class VideoOcrObject:
    text = ""
    language = ""
    score = None
    vertices = None
    def __init__(self, text = "", language = "", score = None, vertices = None):
        self.text = text
        self.language = language
        self.score = score
        self.vertices = vertices
        
    # Return true if the text in this object equals that in the given object.
    def match(self, object):
        return self.text == object.text
        
    @classmethod
    def from_json(cls, json_data: dict):
        language = None
        score = None
        if 'language' in json_data.keys():
            language = json_data['language']
        if 'score' in json_data.keys():
            score = VideoOcrObjectScore.from_json(json_data['score'])
        return cls(json_data['text'], language, score, VideoOcrObjectVertices.from_json(json_data['vertices']))


class VideoOcrObjectScore:
    type = ""
    value = None
    def __init__(self, type = "", value = None):
        self.type = type
        self.value = value
        
    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)
    

class VideoOcrObjectVertices:
    xmin = 0
    ymin = 0
    xmax = 0
    ymax = 0
    def __init__(self, xmin = 0, ymin = 0, xmax = 0, ymax = 0):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        
    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)
    
     

     