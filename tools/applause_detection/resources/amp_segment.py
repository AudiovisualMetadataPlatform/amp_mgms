import json


class AmpSegment:
	def __init__(self, filename = "", segments=[]):
		self.media = SegmentationMedia(filename)
		self.segments = segments
		
		# populate media duration with the end timestamp of the last segment if exists
		# assuming segments are ordered by start/end timestamp
		if len(segments) > 0:
			self.media.duration = segments[-1]['end']

	@classmethod
	def from_json(cls, json_data: dict):
		segments = list(map(SegmentationSegment.from_json, json_data["segments"]))
		media = SegmentationMedia(json_data["media"]["duration"], json_data["media"]["filename"])
		return cls(segments, media)
				
			
class SegmentationMedia:
	def __init__(self, filename = "", duration = 0):
		self.filename = filename
		self.duration = duration

	@classmethod
	def from_json(cls, json_data):
		return cls(**json_data)


def main():
	segments = [
	    {
	        "label": "non-applause",
	        "start": 0.0,
	        "end": 0.64
	    },
	    {
	        "label": "applause",
	        "start": 0.65,
	        "end": 6.78
	    }
	]
	amp_segment = AmpSegment("audio.wav", segments)
	with open("/srv/amp/audio.json", 'w') as file:
		json.dump(amp_segment, file, indent=4, default = lambda x: x.__dict__)

		
if __name__ == "__main__":
	main()
