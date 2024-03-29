#!/usr/bin/env amp_python.sif
# TODO: This calls a getchildren() function that doesn't exist and was broken
# prior to the refactoring.

import json
import xml.etree.ElementTree as ET
from datetime import datetime
import argparse
from amp.fileutils import read_json_file

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("context_json")
    parser.add_argument("output_xml")
    args = parser.parse_args()
    
    context = json.loads(args.context_json)
    item_name = context["itemName"]
    primary_file_name = context["primaryfileName"]
    applause_segments = read_json_file(args.input_file)
    segment_start = None
    segment_count = 1
    item = ET.Element('Item')
    item.set('label', item_name)
    primary_file = ET.SubElement(item, 'Div')
    primary_file.set('label', primary_file_name)

    for segment in applause_segments["segments"]:
        # This should start a segment
        if segment["label"] == "applause":
            # If this is the first segment, set the start time
            if segment_start is None:
                segment_start = segment["start"]
            #  Applause item, create the element
            create_work_item(primary_file, segment_start, segment["end"], 'Work')
            segment_start = None
        elif segment["label"] == "non-applause":
            # Non applause should be added to the next applause segment
            segment_start = segment["start"]
            # If this is the last segment, output it
            if segment_count == len(applause_segments["segments"]):
                create_work_item(primary_file, segment_start, segment["end"], 'Other')
                segment_start = None
        segment_count+=1
    mydata = ET.tostring(element=item, method="xml")
    myfile = open(args.output_xml, "wb")
    myfile.write(mydata)
    
    exit(0)

def create_work_item(xml_parent, begin, end, label):
    work_item = ET.SubElement(xml_parent, 'Span')
    work_item.set('begin', to_time_string(begin))
    work_item.set('end', to_time_string(end))
    work_item.set('label', label + str(len(xml_parent.getchildren())))

def to_time_string(seconds):
    dt = datetime.utcfromtimestamp(seconds)
    return dt.strftime("%H:%M:%S.%f")[:-3]

if __name__ == "__main__":
    main()
