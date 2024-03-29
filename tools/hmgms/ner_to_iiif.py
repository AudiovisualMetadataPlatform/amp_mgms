#!/usr/bin/env amp_python.sif

import json
import sys
import traceback
import argparse
import logging
import amp.logging
from amp.fileutils import valid_file, create_empty_file, read_json_file, write_json_file

# Convert NER generated JSON file to IIIF manifest JSON file.
# Usage: ner_to_iiif.py root_dir from_ner to_iiif context_json
def main():
    # parse command line arguments  
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("from_ner", help="json file generated by previous NER tool in standard AMP NER format to convert from")
    parser.add_argument("to_iiif", help="json file fed to HMGM NER editor in IIIF format to convert to")
    parser.add_argument("context_json", help="context info as json string needed for creating HMGM tasks")
    args = parser.parse_args()
    amp.logging.setup_logging("ner_to_iiif", args.debug)
    logging.debug(f"Starting with args {args}")
       
    # using output instead of input filename as the latter is unique while the former could be used by multiple jobs 
    try:
        # exit to requeue here if NER->IIIF conversion already done
        if valid_file(args.to_iiif):
            logging.debug("IIIF has already been generated (exit 255)")
            exit(255)
    
        logging.info("Converting from NER " + args.from_ner + " to IIIF: " + args.to_iiif)   
        # parse input NER and context JSON
        context = json.loads(args.context_json)
        ner_data = read_json_file(args.from_ner)
    
        # generate IIIF JSON from inputs 
        iiif_data = generate_iiif_other_fields(context, ner_data)
        iiif_data["annotations"] = generate_iiif_annotations(ner_data)
    
        # write IIIF JSON to file
        write_json_file(iiif_data, args.to_iiif)
        
        logging.info(f"Successfully converted from NER {args.from_ner} to IIIF {args.to_iiif}")
        sys.stdout.flush()
        # implicitly exit 0 as the current command completes
    except Exception as e:
        # empty out to_iiif to tell the following HMGM task command to fail
        create_empty_file(args.to_iiif)
        logging.exception(f"Failed to convert from NER {args.from_ner} to IIIF {args.to_iiif}")
        exit(1)


# Populate IIIF fields other than annotations, using the provide context and ner_data.
def generate_iiif_other_fields(context, ner_data):
    primaryfile_name = context["primaryfileName"]
    primaryfile_url = context["primaryfileUrl"]
    media_info_path = context["primaryfileMediaInfo"]
    duration = get_media_duration(media_info_path)

    iiif_data = {
        "@context": [
            "http://digirati.com/ns/timeliner",
            "http://www.w3.org/ns/anno.jsonld",
            "http://iiif.io/api/presentation/3/context.json"
        ],
        "id": ner_data["media"]["filename"],    # use NER media filename as Timeliner ID
        "type": "Manifest",
        "label": { "en": [ "Primaryfile " + primaryfile_name ] },
        "summary": { "en": [ "Named Entity Recognition for " + primaryfile_name ] },
        "items": [
            {
            "id": "canvas-1",
            "type": "Canvas",
            "duration": duration,
            "items": [
                {
                "id": "annotation-1",
                "type": "AnnotationPage",
                "items": [
                    {
                    "id": "annotation-1/1",
                    "type": "Annotation",
                    "motivation": "painting",
                    "body": {
                        "id": primaryfile_url,    # media file played by Timeliner, start from beginning
                        "type": "Audio",
                        "duration": duration
                    },
                    "target": "canvas-1"
                    }
                ]
                }
                ]
            }
            ],
        "structures": [
            {
            "id": "range-1",
            "type": "Range",
            "label": { "en": [ "Unique Bubble" ] },
            "tl:backgroundColour": "#ACD4E2",
            "items": [
                {
                "type": "Canvas",
                "id": f"canvas-1#t=0,{duration}"
                }
            ]
            }
        ],
        "tl:settings": {    # CSS features for Timeliner display
            "tl:bubblesStyle": "rounded",
            "tl:blackAndWhite": False,
            "tl:showTimes": False,
            "tl:autoScaleHeightOnResize": False,
            "tl:startPlayingWhenBubbleIsClicked": False,
            "tl:stopPlayingAtTheEndOfSection": False,
            "tl:startPlayingAtEndOfSection": False,
            "tl:zoomToSectionIncrementally": False,
            "tl:showMarkers": True,
            "tl:bubbleHeight": 80,
            "tl:backgroundColour": "#fff",
            "tl:colourPalette": "default"
        }        
    }

    return iiif_data


# Generate IIIF annotations for the given ner_data.
def generate_iiif_annotations(ner_data):
    annotations_items = []

    # create a IIIF annotation for each entity in ner_data 
    for i, entity in enumerate(ner_data["entities"]):
        annotation = {
          "id": f"marker-{i+1}",
          "type": "Annotation",
          "label": { "en": [ entity["text"]  ]  },
          "body": {
            "type": "TextualBody",
            "value": entity["type"],
            "format": "text/plain",
            "language": "en"
          },
          "target": {
            "type": "SpecificResource",
            "source": "canvas-1",
            "selector": {
              "type": "PointSelector",
              "t":  entity["start"]
            }
          }
        }
        annotations_items.append(annotation)

    annotations = [ {
      "type": "AnnotationPage",
      "items": annotations_items
    } ]
    return annotations


# Get media duration from the media info file with the given mediaInfoPath.
def get_media_duration(media_info_path):
    try:
        media_info = read_json_file(media_info_path)
        duration = media_info['streams']['audio'][0]['duration']
    except Exception as e:
        traceback.print_exc()
        raise Exception("Exception reading media info from " + media_info_path, e)
    return duration


if __name__ == "__main__":
    main()    
