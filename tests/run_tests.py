#!/bin/env python3
import argparse
import yaml
import subprocess
from pathlib import Path
import sys
import logging
import re
import xml.etree.ElementTree as ET
import tempfile
import shutil
import os
import json

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("mgm_dir", help="Directory with MGMs")
    parser.add_argument("suite", help="Test suite YAML file")
    parser.add_argument("only_these_tests", nargs="*", help="Only run the named tests")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)
    
        
    # load the fixture file names
    fixtures = {}
    for f in Path(sys.path[0], "fixtures").glob("*"):
        fixtures[f.name] = f.absolute()

    # load our test suite
    with open(args.suite) as f:
        tests = yaml.safe_load(f)    
    logging.info(f"Loaded {len(tests)} tests")

    mgm_dir = Path(args.mgm_dir)
    cur_test = 0
    passes = 0
    fails = 0
    for test in tests:
        if args.only_these_tests and test['name'] not in args.only_these_tests:
            logging.debug(f"Skipping {test['name']} because it's not in {args.only_these_tests}")
            continue
        cur_test += 1

        if test.get("skip", False):
            logging.info(f"Skipping {test['name']}")
            continue

        tool_file = mgm_dir / test["tool"]        
        context = f"({cur_test}/{len(tests)}) '{test['name']}'"
        if not tool_file.exists():
            logging.error(f"{context} failed:  tool file {tool_file} doesn't exist")
            fails += 1
            continue

        tool_root = ET.parse(tool_file).getroot()
        command_text = tool_root.findtext("command").strip()
        logging.debug(f"{context} Tool text: {command_text}")

        # build the parameters needed for substitution
        params = {'__tool_directory__': str(mgm_dir.absolute())}
        if 'params' in test:
            params.update(test["params"])

        # get the input fixtures
        missing_fixture = False
        for k, v in test["inputs"].items():
            if v not in fixtures:
                logging.error(f"{context} fixture for {k}={v} not found.")
                missing_fixture = True
            else:
                params[k] = str(fixtures[v])
        if missing_fixture:
            logging.error(f"{context} test failed because of missing fixtures")
            fails += 1
            continue

        with tempfile.TemporaryDirectory(prefix="mgm_tests-") as tempdir:
            # get the output files
            outputs = {}
            for o in test['outputs']:
                outputs[o] = tempdir + "/" + o
                params[o] = outputs[o]

            logging.debug(f"{context} Test parameters: {params}")

            # replace the parameters in the command text
            for k, v in params.items():
                command_text = command_text.replace("$" + k, str(v))
            if '$' in command_text:
                logging.warn(f"{context} Command text still contains a '$':  are all parameters substituted?")
                logging.warn(f"{command_text}")            


            runscript = Path(tempdir, "runscript.sh")
            # build the shell script
            script = f"""#!/bin/bash
set -e
{command_text}
            """
            logging.debug(f"{context} script: {script}")
            with open(runscript, "w") as f:
                f.write(script)
            runscript.chmod(0o755)

            if args.debug:
                os.environ['MGM_DEBUG'] = '1'

            logging.debug(f"{context} Starting runscript")
            p = subprocess.run([str(runscript)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")
            if p.returncode != 0:
                logging.error(f"{context} runscript failed with return code {p.returncode}")
                logging.error(p.stdout)
                fails += 1
                continue

            # Since the script worked OK, run any tests on the output file
            test_errors = 0
            test_items = 0
            for out in outputs:
                test_items += 1
                if not Path(outputs[out]).exists():
                    logging.error(f"{context} output file {out} doesn't exist")
                    test_errors += 1
                    continue
                for ftest in test['outputs'][out]:
                    test_items += 1
                    if ftest['test'] not in test_functions:
                        logging.error(f"{context}/{out} test function {ftest['test']} doesn't exist")
                        test_errors +=1 
                        continue
                    try:
                        res = test_functions[ftest['test']](outputs[out], ftest)
                        if not res:
                            logging.error(f"{context} -> {out} {ftest} Failed")
                            test_errors +=1
                            continue
                    except Exception as e:
                        logging.error(f"{context} -> {out} test failed with exception")
                        logging.error(e)
                        test_errors += 1
                        continue

            if test_errors != 0:
                logging.error(f"{context} {test_errors}/{test_items} file tests failed")
                fails += 1
                continue

        logging.info(f"{context} Passed")
        passes += 1

    logging.info(f"Results:  {len(tests)} tests, {passes} passed, {fails} failed.")



def test_pass(file, args):
    "pass/fail the test automatically"
    return args['status']


ffprobes = {}
def test_ffprobe(file, args):
    "use ffprobe to test some aspect of the file"
    if(file not in ffprobes):
        logging.debug(f"Looking up ffprobe for {file}")
        p = subprocess.run(['ffprobe', '-loglevel', 'panic', '-print_format', 'xml', '-show_streams', '-show_format', file], 
                           stdout=subprocess.PIPE, encoding='utf-8')
        ffprobes[file] = ET.fromstring(p.stdout)    
        logging.debug(ET.tostring(ffprobes[file], encoding='utf-8'))
    ffprobe = ffprobes[file]
    return _test_xml(file, ffprobe, args)

def test_xml(file, args):
    "Just read the xml file and pass it along"
    xml = ET.parse(file)
    return _test_xml(file, xml, args)

def _test_xml(context, xml, args):    
    node = xml.find(args['path'])
    if 'attrib' in args:
        val = node.attrib[args['attrib']]
    else:
        val = node.text
    val = val.strip()

    if val != args['value']:
        logging.error(f"File {context}:  got {val} but expected {args['value']}")
        logging.debug(ET.tostring(xml, encoding='utf-8'))
        return False
    return True

def test_json(file, args):
    return _test_json(file, file, args)

def _test_json(context, filename, args):
    with open(filename) as f:
        json_data = json.load(f)
    xml_string = "<data>" + _data_to_xml_string(json_data) + "</data>"
    
    try:
        xml = ET.fromstring(xml_string)
    except Exception as e:
        logging.error("Cannot parse XML from _data_to_xml_string:")
        logging.error(xml_string)
        raise e

    return _test_xml(context, xml, args)


def _data_to_xml_string(data):
    xml = ""
    if isinstance(data, list):
        for k, v in enumerate(data):
            xml += f"<i{k}>" + _data_to_xml_string(v) + f"</i{k}>"
    elif isinstance(data, dict):
        for k, v in data.items():
            if k[0] in "0123456789":
                k = "_" + k
            xml += f"<{k}>" + _data_to_xml_string(v) + f"</{k}>"
    else:
        xml = str(data).replace('&', '&amp;')
        xml = xml.replace('<', '&lt;')
        xml = xml.replace('>', '&gt;')
    return xml

def test_magic(file, args):
    "compare the mime type"
    p = subprocess.run(['file', '-b', '--mime-type', file], stdout=subprocess.PIPE, encoding='utf-8')
    mime = p.stdout.strip()
    if mime != args['mime']:
        logging.error(f"{file} should be type {args['mime']} but got {mime}")
        return False
    return True

def test_size(file, args):
    "compare the file size"
    size = Path(file).stat().st_size
    if int(args['size']) != size:
        logging.error(f"{file} expected file size of {args['size']} but got {size} instead")
        return False
    return True

def test_debug(file, args):
    """Allow some thigns that make debugging easier"""
    if args.get("save", False):
        logging.info(f"Copying {file} to {args.get('save')}")
        shutil.copy(file, args.get("save"))
            
    return True

def test_strings(file, args):
    "check if the file contains the strings"
    with open(file, encoding='utf-8') as f:
        data = f.read()
        if not isinstance(args['strings'], list):
            args['strings'] = [args['strings']]
        for s in args['strings']:
            if s not in data:
                logging.error(f"{file} String '{s}' not in the file")
                return False

    return True

def test_md5(file, args):
    "compare the MD5 of the file"
    pass


test_functions = {
    'pass': test_pass,
    'magic': test_magic,
    'ffprobe': test_ffprobe,
    'xmlfile': test_xml,
    'size': test_size,
    'debug': test_debug,
    'strings': test_strings,
    'md5': test_md5,
    'json': test_json,
}


if __name__ == "__main__":
    main()