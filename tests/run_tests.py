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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("mgm_dir", help="Directory with MGMs")
    parser.add_argument("suite", help="Test suite YAML file")
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
        cur_test += 1
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

            logging.debug(f"{context} Starting runscript")
            p = subprocess.run([str(runscript)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8")
            if p.returncode != 0:
                logging.error(f"{context} runscript failed with return code {p.returncode}")
                logging.error(p.stderr)
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
                logging.error(f"{context} {test_errors} -> {test_items} file tests failed")
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
    ffprobe = ffprobes[file]
    return _test_xml(file, ffprobe, args)


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



test_functions = {
    'pass': test_pass,
    'ffprobe': test_ffprobe
}


if __name__ == "__main__":
    main()