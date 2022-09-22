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
import os
import json
import csv

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
                run_tests(test, outputs, args.debug)


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


def run_tests(test, outputs, debug=False):
def run_tests(test, outputs, debug=False):
    "Run the specified tests on the output"
    has_failures = False
    for outname in outputs:
        outfile = outputs[outname]        
        if not Path(outfile).exists():
            logging.error(f"{outname}: Output file {outfile!s} doesn't exist")
            has_failures = True
            continue

        cache = {}
        sub_error = False
        for t in test['outputs'][outname]:
            try:
                logging.debug(f"Running {t} on {outfile}")
                if test_eval(outfile, t, cache):
                    logging.info(f"{outname}: Test OK {t}")
                else:
                    logging.info(f"{outname}: Test failed {t}")
                    has_failures = True
                    sub_error = True
            except Exception as e:
                if debug:
                    logging.exception(f"{outname} Test {t} threw exception {e}")
                else:
                    logging.error(f"{outname} Test {t} threw exception {e}")
                
        if sub_error:
            logging.error(f"Cache for {outname}:\n" + yaml.safe_dump(cache))
                    sub_error = True
            except Exception as e:
                if debug:
                    logging.exception(f"{outname} Test {t} threw exception {e}")
                else:
                    logging.error(f"{outname} Test {t} threw exception {e}")
                
        if sub_error:
            logging.error(f"Cache for {outname}:\n" + yaml.safe_dump(cache))

    if has_failures:
        raise Exception("Some tests have failed")


#######################
# test language bits.
#######################
def test_eval(subject, expr, cache=None):
    "Evaluate a test expression"
    if cache is None:
        cache = dict()
    if not isinstance(expr, list):        
        raise ValueError(f"Test expression {expr} is not a list.")
    func, *args = expr
    # evaluate the args in advance
    for i in range(len(args)):
        if isinstance(args[i], list):
            args[i] = test_eval(subject, args[i], cache)
    
    # boolean functions
    if func == 'true':
        return True
    elif func == 'false':
        return False
    elif func == 'and':
        r = True
        for a in args:
            r = r and a
        return r
    elif func == 'or':
        r = False
        for a in args:
            r = r or a
        return r
    elif func == 'not':
        return not args[0]
    
    # comparison ops
    elif func in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
        args = coerce(args)
        if len(args) < 2:
            raise ValueError(f"Cannot run {func} with these args: {args}")
        if func == 'eq':
            return args[0] == args[1]
        elif func == 'ne':
            return args[0] != args[1]
        elif func == 'lt':
            return args[0] < args[1]
        elif func == 'le':
            return args[0] <= args[1]
        elif func == 'gt':
            return args[0] > args[1]
        elif func == 'ge':
            return args[0] >= args[1]
    
    # other comparisons
    elif func == 'any':
        args = coerce(args)
        return args[0] in args[1:]
    elif func == 're':
        return re.search(str(args[0]), str(args[1])) is not None
    elif func == 'and':
        r = True
        for a in args:
            r = r and a
        return r
    elif func == 'or':
        r = False
        for a in args:
            r = r or a
        return r
    elif func == 'not':
        return not args[0]
    
    # comparison ops
    elif func in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
        args = coerce(args)
        if len(args) < 2:
            raise ValueError(f"Cannot run {func} with these args: {args}")
        if func == 'eq':
            return args[0] == args[1]
        elif func == 'ne':
            return args[0] != args[1]
        elif func == 'lt':
            return args[0] < args[1]
        elif func == 'le':
            return args[0] <= args[1]
        elif func == 'gt':
            return args[0] > args[1]
        elif func == 'ge':
            return args[0] >= args[1]
    
    # other comparisons
    elif func == 'any':
        args = coerce(args)
        return args[0] in args[1:]
    elif func == 're':
        return re.search(str(args[0]), str(args[1])) is not None
    
    # data functions
    elif func == 'size':
        return Path(subject).stat().st_size
    elif func == 'mime':
        # this is a file magic check
        p = subprocess.run(['file', '-b', '--mime-type', subject], stdout=subprocess.PIPE, encoding='utf-8', check=True)
        return p.stdout.strip()
    elif func == 'json':
        if 'json' not in cache:
            with open(subject) as f:
                cache['json'] = json.load(f)
            return find_json_value(cache['json'], args[0])
    elif func == 'xpath':
        if 'xpath' not in cache:
            cache['xpath'] = ET.parse(subject)
        node = cache['xpath'].find(args[0])
        if len(args) > 1:
            return node.attrib[args[1]].strip()
        else:
            return node.text.strip()
    elif func == 'media':
        if 'media' not in cache:
            mediaprobe = os.environ['AMP_ROOT'] + "/data/MediaProbe/media_probe.py"
            p = subprocess.run([mediaprobe, '--json', subject], stdout=subprocess.PIPE, encoding='utf-8', check=True)
            cache['media'] = json.loads(p.stdout)
        return find_json_value(cache['media'], args[0])
    elif func == 'data':
        if 'data' not in cache:
            cache['data'] = Path(subject).read_text(encoding='utf-8')
        return cache['data']        
    elif func == 'contains':
        return args[0] in args[1]
    elif func == 'int':
        return coerce([0, args[0]])[1]
    elif func == 'str':
        return coerce(['', args[0]])[1]
    elif func == 'bool':
        return coerce([True, args[0]])[1]
    elif func == 'float':
        return coerce([0.0, args[0]])[1]
    elif func == 'lower':
        return str(args[0]).lower()
    else:
        raise ValueError(f"No such function: {func}")


def find_json_value(data, path):
    "find a value in the json data using dotted-path notation"
    if isinstance(path, str):
        path = path.split('.')
    value = data[int(path[0])] if isinstance(data, list) else data[path[0]]
    if len(path) > 1:
        return find_json_value(value, list(path[1:]))
    else:
        return value


def coerce(data):
    logging.debug(f"Coerce: {data}")
    "Convert the type of all objects to match the first item"
    if not len(data):
        raise ValueError("Got 0 arguments for coercion")
    if isinstance(data[0], str):
        data = [str(x) for x in data]
    elif isinstance(data[0], bool):
        # this one is special:  I also want to catch strings like 'yes'
        for i in range(len(data)):
            if str(data[i]).lower() in ('y', 'yes', 'true'):
                data[i] = True
            elif str(data[i]).lower() in ('n', 'no', 'false'):
                data[i] = False
            else:
                data[i] = bool(data[i])
        data = [bool(x) for x in data]
    elif isinstance(data[0], float):
        for i in range(len(data)):
            try:
                data[i] = float(data[i])
            except:
                data[i] = 0.0
    elif isinstance(data[0], int):
        for i in range(len(data)):
            try:
                data[i] = int(data[i])
            except:
                data[i] = 0
    else:
        logging.debug(f"Cannot coerce {data} into something I understand")
    return data


if __name__ == "__main__":
    main()