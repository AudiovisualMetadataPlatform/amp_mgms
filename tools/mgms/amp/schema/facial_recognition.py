
class FaceRecognition:
    def __init__(self, media = None, frames = None):
        if media is None:
            self.media = FaceRecognitionMedia()
        else:
            self.media = media
        if frames is None:
            self.frames = []
        else:
            self.frames = frames
     
    @classmethod
    def from_json(cls, json_data):
        media = FaceRecognitionMedia.from_json(json_data["media"])
        frames = list(map(FaceRecognitionFrame.from_json, json_data["frames"]))
        return cls(media, frames)
             
class FaceRecognitionMedia:
    def __init__(self, filename = "", duration = 0, frameRate = 0, numFrames = 0, resolution = None):
        self.filename = filename
        self.duration = duration
        self.frameRate = frameRate
        self.numFrames = numFrames
        if resolution is None:
            self.resolution = FaceRecognitionMediaResolution()
        else:
            self.resolution = resolution

    @classmethod
    def from_json(cls, json_data: dict):
        media = cls(**json_data)
        media.resoluation = FaceRecognitionMediaResolution.from_json(json_data["resolution"])
        return media

class FaceRecognitionMediaResolution:
    def __init__(self, width = 0, height = 0):
        self.width = width
        self.height = height

    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)

class FaceRecognitionFrame:
    def __init__(self, start = 0, objects = None):
        self.start = start
        if objects is None:
            self.objects = []
        else:
            self.objects = objects

    @classmethod
    def from_json(cls, json_data):
        start = json_data["start"]
        objects = list(map(FaceRecognitionFrameObject.from_json, json_data["objects"]))
        return cls(start, objects)

class FaceRecognitionFrameObject:
    def __init__(self, name = "", score = None, vertices = None):
        self.name = name
        if score is None:
            self.score = FaceRecognitionFrameObjectScore()
        else:
            self.score = score
        if vertices is None:
            self.vertices = FaceRecognitionFrameObjectVertices()
        else:
            self.vertices = vertices

    @classmethod
    def from_json(cls, json_data: dict):
        score = FaceRecognitionFrameObjectScore.from_json(json_data["score"])
        vertices = FaceRecognitionFrameObjectVertices.from_json(json_data["vertices"])
        return cls(json_data["name"], score, vertices)

class FaceRecognitionFrameObjectScore:
    def __init__(self, type = "", value = 0):
        self.type = type
        self.value = value
        
    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)

class FaceRecognitionFrameObjectVertices:
    def __init__(self, xmin = 0, ymin = 0, xmax = 0, ymax = 0):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        
    @classmethod
    def from_json(cls, json_data: dict):
        return cls(**json_data)
