#!/bin/env python3
import argparse
from time import sleep
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
    parser.add_argument("--fixtures", type=str, default=sys.path[0] + "/fixtures", help="Fixtures directory")
    parser.add_argument("mgm_dir", help="Directory with MGMs")
    parser.add_argument("suite", help="Test suite YAML file")
    parser.add_argument("only_these_tests", nargs="*", help="Only run the named tests")
    args = parser.parse_args()
    logging.basicConfig(format="%(asctime)s [%(levelname)-8s] (%(filename)s:%(lineno)d)  %(message)s",
                        level=logging.DEBUG if args.debug else logging.INFO)
            
    # load the fixture file names
    fixtures = {}    
    for f in Path(args.fixtures).glob("*"):
        fixtures[f.name] = str(f.absolute())

    # load the test suite
    with open(args.suite) as f:
        tests = yaml.safe_load(f)        
    logging.info(f"Loaded {len(tests)} tests")

    # remove tests that aren't requested
    if args.only_these_tests:
        tests = [x for x in tests if x['name'] in args.only_these_tests]
        logging.info(f"Selected {len(tests)} tests")
    
    # Run the selected tests.
    results = {'pass': 0, 'fail': 0, 'skip': 0}
    total_tests = len(tests)
    for i in range(total_tests):
        test = tests[i]
        leader = f"({i + 1}/{total_tests})"

        # some tests will be skipped due to configuration
        if 'skip' in test:
            logging.info(f"{leader} Skipping {test['name']}:  {test['skip']}")
            results['skip'] += 1
            continue

        logging.info(f"{leader} Running test {test['name']}")
        try:
            with tempfile.TemporaryDirectory() as tempdir:
                # build the runscript and the output map.
                outputs = build_script(test, args.mgm_dir, fixtures, tempdir)

                # execute the runscript                
                runscript(tempdir)

                # run the tests on the output
                run_tests(test, outputs, tempdir)


        except Exception as e:
            logging.error(f"{leader} Failed: {e}")
            results['fail'] += 1




    logging.info(f"Results:  {total_tests} tests, {results['pass']} passed, {results['fail']} failed, {results['skip']} skipped.")



def build_script(test, mgm_dir, fixtures, tempdir):
    """Build the text of the script, based on the environment, and return a 
       dict of the output name -> tempdir/name files"""
    tool_file = Path(mgm_dir, test['tool'])
    if not tool_file.exists():
        raise FileNotFoundError(f"Tool file {tool_file.absolute()!s} not found")

    # get the text of the command from the tool
    tool_root = ET.parse(tool_file).getroot()
    command_text = tool_root.findtext("command").strip()

    # build the parameters needed for substitution        
    params = {'__tool_directory__': str(tool_file.parent.absolute())}
    if 'params' in test:
        params.update(test["params"])

    # get the input fixtures
    missing_fixture = False
    for k, v in test["inputs"].items():
        if v not in fixtures:
            logging.error(f"Fixture for {k}={v} not found.")
            missing_fixture = True
        else:
            params[k] = fixtures[v]
    if missing_fixture:
        raise FileNotFoundError("One or more fixtures cannot be found")

    # create the output file map
    outputs = {}
    for o in test['outputs']:
        outputs[o] = tempdir + "/" + o + ".dat"
        params[o] = outputs[o]

    # replace the parameters in the command text
    for k in sorted(params.keys(), reverse=True, key=len):
        command_text = command_text.replace("$" + k, str(params[k]))
    if '$' in command_text:
        raise ValueError(f"The command text still contains a '$': {command_text}")
        
    # write the script
    runscript = Path(tempdir, "runscript.sh")
    # build the shell script
    script = f"""#!/bin/bash
set -e
{command_text}
    """        
    with open(runscript, "w") as f:
        f.write(script)
    runscript.chmod(0o755)
    logging.debug(f"Runscript text:\n{script}")

    return outputs

def runscript(tempdir, debug=False):
    "Run the runscript.sh in the directory specified"
    if debug:
        os.environ['AMP_DEBUG'] = '1'

    rc = 255    
    while rc == 255:
        logging.debug(f"Starting {tempdir}/runscript.sh")                
        p = subprocess.run([tempdir + "/runscript.sh"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")        
        rc = p.returncode
        logging.debug(f"Return code {rc}, output:\n{p.stdout}")
        if rc == 255:
            sleep(10)
    if rc != 0:
        raise Exception(f"Runscript failed with rc {rc} and this output:\n{p.stdout}")


def run_tests(test, outputs, tempdir):
    "Run the specified tests on the output"
    has_failures = False
    for outname in outputs:
        outfile = outputs[outname]        
        if not Path(outfile).exists():
            logging.error(f"{outname}: Output file {outfile!s} doesn't exist")
            has_failures = True
            continue

        for args in test['outputs'][outname]:
            testname = args['test']
            comp = args.get('comp', '==')
            setop = args.get('setop', 'all')
            if testname == 'pass':                
                # this test always passes
                pass
            elif testname == "debug":
                # this isn't a test, so much as it is a file copy
                if args.get("save", False):
                    logging.info(f"Copying {outfile} to {args['save']}")
                    shutil.copy(outfile, args["save"])
            elif testname == 'magic':
                # this is a file magic check
                p = subprocess.run(['file', '-b', '--mime-type', outfile], stdout=subprocess.PIPE, encoding='utf-8')
                mime = p.stdout.strip()                
                if not comparitor(mime, args['mime'], comp):                
                    logging.error(f"{outname} mime-type: {mime} {comp} {args['mime']} is false.")
                    has_failures = True
                    continue
            elif testname == 'size':
                # file size check
                size = Path(outfile).stat().st_size
                csize = int(args['size'])                
                if not comparitor(csize, size, comp):
                    logging.error(f"{outfile} file size: {size} {comp} {csize} is false.")
                    has_failures = True
                    continue
            elif testname == 'strings':
                # check to make sure any/all strings are present
                data = Path(outfile).read_text(encoding='utf-8')                
                if not isinstance(args['strings'], list):
                    args['strings'] = [args['strings']]
                found = set()
                for s in args['strings']:
                    if s in data:                        
                        found.add(s)
                if setop == "all" and len(found) != len(args['strings']):
                    logging.error(f"{outfile} strings: Some strings not found: {set(args['strings']).difference(found)}")
                    has_failures = True
                    continue
                if setop == "any" and len(found) == 0:
                    logging.error(f"{outfile} strings: None of the strings were found")
                    has_failures = True
                    continue

    if has_failures:
        raise Exception("Some tests have failed")


def comparitor(a, b, comp='=='):
    if comp == '==':
        return a == b
    if comp == '!=':
        return a != b
    if comp == '>':
        return a > b
    if comp == '>=':
        return a >= b
    if comp == '<':
        return a < b
    if comp == '<=':
        return a <= b
    if comp == 'in':
        return a in b

#################################################################




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






if __name__ == "__main__":
    main()