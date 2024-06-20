#!/usr/bin/env amp_python.sif

import argparse
import paramiko
import logging
import getpass
import uuid
from pathlib import Path
import yaml
from stat import S_ISDIR
from amp.config import load_amp_config, get_config_value
import amp.logging
from amp.lwlw import LWLW
from amp.cloudutils import generate_persistent_name
from amp.fileutils import read_json_file, write_json_file
from amp.vtt_helper import gen_vtt, words2phrases
import json
from tempfile import NamedTemporaryFile

class Cluster_Whisper(LWLW):
    def __init__(self, input_file, model="medium", language="en", prompt=None,
                 web_vtt=None, amp_transcript=None, transcript_text=None, 
                 transcript_json=None, amp_diarization=None,
                 vtt_phrase_gap=1.5, vtt_max_duration=3):
        self.input_file = input_file        
        self.model = model
        self.language = language
        self.prompt = prompt
        self.web_vtt = web_vtt
        self.amp_transcript = amp_transcript
        self.transcript_text = transcript_text
        self.transcript_json = transcript_json
        self.amp_diarization = amp_diarization     
        self.vtt_phrase_gap = vtt_phrase_gap
        self.vtt_max_duration = vtt_max_duration   
        self.config = load_amp_config()

        # get our parameters from the system
        self.hpchost = get_config_value(self.config, ['mgms', 'cluster_whisper', 'hpchost'])
        self.hpcuser = get_config_value(self.config, ['mgms', 'cluster_whisper', 'hpcuser'])
        self.hpcworkdir = get_config_value(self.config, ['mgms', 'cluster_whisper', 'hpcworkdir'])
        self.hpcscript = get_config_value(self.config, ['mgms', 'cluster_whisper', 'hpcscript'])
        self.hpcsubmit = get_config_value(self.config, ['mgms', 'cluster_whisper', 'hpcsubmit'])

        # generate a persistent job name
        self.jobid = generate_persistent_name('CLUSTER_WHISPER', self.input_file, 
                                              self.web_vtt, self.amp_transcript, 
                                              self.transcript_text, self.transcript_json,
                                              self.amp_diarization)

        # connect to the HPC cluster
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.connect(self.hpchost, username=self.hpcuser)


    def exists(self):
        """return information about job or None if it doesn't exist"""        
        sftp = self.ssh.open_sftp()
        if not valid_job(sftp, self.hpcworkdir, self.jobid):
            return None
        done, total = determine_job_status(sftp, self.hpcworkdir, self.jobid)    
        hpcjobid = get_hpc_job_id(sftp, self.hpcworkdir)
        stext = "FINISHED" if done == total else "IN_PROGRESS"
        return {
            'status': stext,
            'done': done,
            'total': total,
            'hpcjobid': hpcjobid
        }


    def submit(self):
        "Upload the audio file to S3 and submit the transcription job"
     
        sftp = self.ssh.open_sftp()
        sftp.chdir(self.hpcworkdir)    
        
        # create the job directory in the hpc workspace...
        jobname = self.jobid
        sftp.mkdir(jobname)
        sftp.chdir(jobname)
        logging.info(f"Created job directory {jobname}")

        # copy the submit script to the queue if it isn't already there...
        try:
            sftp.stat(self.hpcworkdir + "/.submit")
        except:
            # if we get here then .submit doesn't exist...
            logging.info("Copying .submit script")
            with sftp.open(self.hpcworkdir + "/.submit", "w") as f:
                f.write(sftp.open(self.hpcsubmit).read())


        # copy the individual files to the job directory
        config = {
            'manifest': [],
            'language': self.language,
            'prompt': self.prompt,
            'model': self.model
        }        
        
        f = Path(self.input_file)
        logging.info(f"Uploading {f}")
        sftp.put(str(f.resolve()), f.name)
        config['manifest'].append(f.name)

        logging.info("Creating job file")
        # write the whisper.job parameters file.
        file = sftp.file('whisper.job', 'w', -1)
        yaml.safe_dump(config, file)

        # tell the system we've got something new to do
        logging.info("Submitting the job to HPC")        
        command = f'bash -c "{self.hpcscript} {self.hpcworkdir}; echo \\$?"'
        logging.debug(f"Submit command: {command}")
        (_, stdout, stderr) = self.ssh.exec_command(command)
        # the last line of stdout should be the return code from the command.
        sout = [x.strip() for x in stdout.readlines()]
        if not sout or sout[-1] != '0':
            logging.error("Submission to HPC failed:\n" + "".join(stderr.readlines())) 
            self.cleanup()
            return LWLW.ERROR
        else:
            logging.debug("Submission stdout:\n" + '\n'.join(sout) + "\nstderr:\n" + "".join(stderr.readlines()))
            return LWLW.WAIT


    def check(self):
        "Check on the status of the running job"
        job = self.exists()
        if job is None:
            logging.error(f"The job {self.job_name} should exist but it doesn't!")
            return LWLW.ERROR
        status = job['status']
        if status == 'IN_PROGRESS':
            return LWLW.WAIT
        elif status == "FINISHED":
            # retrieve the result file and put it where it belongs locally
            jobinfo = None
            try:
                sftp = self.ssh.open_sftp()
                jobinfo = yaml.safe_load(sftp.open(f"{self.hpcworkdir}/{self.jobid}/whisper.job").read())
                # get the whisper output...
                whisper_transcript_raw = sftp.open(f"{self.hpcworkdir}/{self.jobid}/{jobinfo['manifest'][0]}.whisper.json").read()
                whisper_transcript = json.loads(str(whisper_transcript_raw, encoding='utf-8'))

                if self.transcript_json:
                    with open(self.transcript_json, "wb") as f:
                        f.write(whisper_transcript_raw)

                if self.transcript_text:
                    with open(self.transcript_text, "w") as f:
                        f.write(whisper_transcript['text'])

                # the rest of the bits require a whisper json file on disk
                with NamedTemporaryFile() as tf:
                    tf.write(whisper_transcript_raw)
                    tf.flush()
                
                    if self.web_vtt:
                        generate_webvtt(tf.name, self.web_vtt, self.vtt_phrase_gap, self.vtt_max_duration)

                    if self.amp_transcript:
                        generate_amp_transcript(tf.name, self.amp_transcript, self.input_file)

                    if self.amp_diarization:
                        generate_amp_diarization(tf.name, self.amp_diarization, self.input_file)

                return LWLW.OK
            except Exception as e:
                logging.error(f"jobinfo: {jobinfo}, jobid: {self.jobid}, workdir: {self.hpcworkdir}")
                logging.exception(f"Failed to download the result: {e}")
                return LWLW.ERROR
        else:
            return LWLW.ERROR


    def cleanup(self):
        "Remove the job and generatd data"
        sftp = self.ssh.open_sftp()
        if not valid_job(sftp, self.hpcworkdir, self.jobid):
            logging.error(f"Cannot purge job: Jobid {self.jobid} is not valid")
            return
        jobdir = f"{self.hpcworkdir}/{self.jobid}"
        logging.warning(f"Purging job directory at {jobdir}")
        file_list = recursive_list(sftp, jobdir)
        for f in file_list:
            if f.endswith("/"):
                logging.debug(f"RMDIR: {f}")
                sftp.rmdir(f)
            else:
                logging.debug(f"UNLINK: {f}")
                sftp.unlink(f)
        # remove the job directory
        logging.debug(f"UNLINK {jobdir}")
        sftp.rmdir(jobdir)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False, help="Turn on debugging")
    parser.add_argument("--lwlw", default=False, action="store_true", help="Use LWLW protocol")
    parser.add_argument("--model", choices=['base', 'tiny', 'small', 'medium', 'large', 'large-v2', 'large-v3'], default='medium', help="Language model")
    parser.add_argument("--language", choices=['auto', 'en', 'zh', 'de', 'es', 'ru', 'ko', 'fr', 'ja'], default="en", help="Language")
    parser.add_argument("--prompt", default=None, help="Model prompt")
    parser.add_argument("--web_vtt", type=str, help="output webvtt filename")
    parser.add_argument("--amp_transcript", type=str, help="output amp transcript")
    parser.add_argument("--transcript_text", type=str, help="output text transcript")
    parser.add_argument("--transcript_json", type=str, help="output json transcript")
    parser.add_argument("--amp_diarization", type=str, help="output amp diarization")
    parser.add_argument("--vtt_phrase_gap", type=float, default=1.5, help="Minimum gap between VTT subtitle phrases")
    parser.add_argument("--vtt_max_duration", type=float, default=3.0, help="Maximum duration of VTT subtitle")
    parser.add_argument("input_file", help="Input file")

    args = parser.parse_args()
    amp.logging.setup_logging("cluster_whisper", args.debug)
    # tell paramiko that I don't want messages unless they're important, even if
    # I've set the root logger to debug.
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    
    logging.info(f"Starting args={args}")
    cwhisper = Cluster_Whisper(args.input_file, 
                               model=args.model, language=args.language.lower(), prompt=args.prompt,
                               web_vtt=args.web_vtt, amp_transcript=args.amp_transcript,
                               transcript_text=args.transcript_text, 
                               transcript_json=args.transcript_json, 
                               amp_diarization=args.amp_diarization,
                               vtt_phrase_gap=args.vtt_phrase_gap, 
                               vtt_max_duration=args.vtt_max_duration)
    
    exit(cwhisper.run(lwlw=args.lwlw))



def valid_job(sftp: paramiko.SFTPClient, workdir, jobid):
    "return true or false if the jobid is valid"
    try:
        # make sure the job directory exists
        jobdir = f"{workdir}/{jobid}"
        s = sftp.stat(jobdir)
        if not S_ISDIR(s.st_mode):
            logging.debug(f"{jobdir} isn't a directory")
            return False
        # make sure we have a whisper.job file
        s = sftp.stat(f"{jobdir}/whisper.job")
        return True
    except Exception as e:
        logging.debug(f"Couldn't check for valid job: {e}")
        return False
    


def recursive_list(sftp, path):
    """Return a list of all of the (file) paths rooted at the given path"""
    results = []
    logging.debug(f"Scanning {path}")    
    for item in sftp.listdir_attr(path):        
        if S_ISDIR(item.st_mode):
            results.extend(recursive_list(sftp, f"{path}/{item.filename}"))            
            results.append(f"{path}/")
        else:                
            results.append(f"{path}/{item.filename}")
    return results


def determine_job_status(sftp, hpcworkdir, jobid):
    "read the whisper.job file to get the manifest and determine status"
    job = yaml.safe_load(sftp.open(f"{hpcworkdir}/{jobid}/whisper.job").read())    
    done = 0
    for n in job['manifest']:
        try:
            sftp.stat(f"{hpcworkdir}/{jobid}/{n}.whisper.json")
            done += 1
        except:
            pass
    return done, len(job['manifest'])


def get_hpc_job_id(sftp, hpcworkdir):
    "Get the HPC job id"
    try:
        job = yaml.safe_load(sftp.open(f"{hpcworkdir}/jobinfo.yaml").read())
        return job['jobid']
    except Exception:        
        return None


# these functions are shamelessly stolen from our whisper mgm



def generate_webvtt(whisper_json, output_vtt, phrase_gap, max_duration):
    "Generate a VTT without underlines and with reasonable timestamps"
    # original version parsed the output VTT, but it makes more sense to
    # just use the json that was generated and generate it fresh.    
    data = read_json_file(whisper_json)
    # the output of whisper's cli puts all of the words into their segments
    # but we need a single word list for words2phrases
    words = []
    for s in data['segments']:
        words.extend(s['words'])

    # also, for some reason whisper likes to prepend spaces to the words so
    # let's strip that too
    for w in words:
        w['word'] = w['word'].strip()

    phrases = words2phrases(words, phrase_gap=phrase_gap, 
                            max_duration=max_duration)
    
    with open(output_vtt, "w") as o:
        o.write(gen_vtt(phrases))


def generate_amp_transcript(whisper_file, amp_file, input_media):
    # convert the native json transcript to an amp transcript
    data = read_json_file(whisper_file)
    amp_transcript = {
        'media': {
            'filename': input_media,
            'duration': 0
        },
        'results': {
            'transcript': data['text'].strip(),
            'words': []
        }
    }                
    duration = 0
    offset = 0
    for seg in data['segments']:
        for word in seg['words']:
            xword = word['word'][1:]
            amp_transcript['results']['words'].append({
                'type': "pronunciation",
                'text': xword,
                'start': word['start'],
                'end': word['end'],
                'offset': offset
            })                        
            tword = amp_transcript['results']['transcript'][offset:offset + len(xword)]
            if tword != xword:
                logging.warning(f"Transcript mismatch @{offset}: word='{xword}', transcript='{tword}'")
            else:
                logging.debug(f"Transcript correct: @{offset}: word={xword}, transcript={tword}")
            offset += len(word['word'])
            duration = max(duration, word['end'])
    
    amp_transcript['results']['duration'] = duration 
    amp_transcript['media']['duration'] = duration
    write_json_file(amp_transcript, amp_file)


def generate_amp_diarization(whisper_json, amp_diarization, input_media):
    "Generate an amp diarization file from the input"
    d = {
        'media': {'filename': input_media,
                  'duration': 0},
        'numSpeakers': 1,
        'segments': []
    }

    data = read_json_file(whisper_json)
    seg_start, seg_end = None, None
    for seg in data['segments']:
        if seg_start is None:
            # new diarization segment
            seg_start = seg['start']
            seg_end = seg['end']
        elif int(seg_end * 10) == int(seg['start'] * 10):
            # within 1/10th second we're the same, so continuation
            seg_end = seg['end']
        else:
            # there's a gap, so so write this one and start a new one
            d['segments'].append({'label': None,
                                  'start': seg_start,
                                  'end': seg_end,
                                  'speakerLabel': 'spk_0'})
            seg_start = seg['start']
            seg_end = seg['end']

    if seg_start is not None:
        d['segments'].append({'label': None,
                              'start': seg_start,
                              'end': seg['end'],
                              'speakerLabel': 'spk_0'})

    d['media']['duration'] = seg_end

    write_json_file(d, amp_diarization)






if __name__ == "__main__":
    main()