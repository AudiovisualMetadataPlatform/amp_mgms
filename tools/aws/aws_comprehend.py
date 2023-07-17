#!/usr/bin/env amp_python.sif

import tempfile
import tarfile
import boto3
import argparse
import tempfile
import logging
from amp.config import load_amp_config, get_config_value, get_cloud_credentials
import amp.logging
from amp.fileutils import read_json_file, write_json_file
import amp.nerutils
from amp.lwlw import LWLW
from amp.cloudutils import generate_persistent_name
import json
from amp.schema.speech_to_text import SpeechToText


class AWS_Comprehend(LWLW):
    def __init__(self, transcript, aws_entities, amp_entities, 
                 ignore_types="QUANTITY,DATE"):
        self.transcript = transcript
        self.aws_entities = aws_entities
        self.amp_entities = amp_entities
        self.ignore_types = ignore_types

        # fixup the default arguments...
        self.config = load_amp_config()        
        self.role_arn = get_config_value(self.config, ['mgms', 'aws_comprehend', 'role_arn'], None)
        if self.role_arn is None:
            logging.error('mgms.aws_comprehend.role_arn is not specified in the config file')
            exit(1)
        self.s3_bucket = get_config_value(self.config, ['mgms', 'aws_comprehend', 's3_bucket'], None)    
        if self.s3_bucket is None:
            logging.error("mgms.aws_comprehend.s3_bucket is not specified in the config file")
            exit(1)

        aws_creds = get_cloud_credentials(self.config, "aws")
        self.comprehend_client = boto3.client('comprehend', **aws_creds)
        self.s3_client = boto3.client("s3", **aws_creds)

        self.job_name = generate_persistent_name("AWSC", transcript, amp_entities)


    def exists(self):
        "get comprehend job information"
        try:
            response = self.comprehend_client.list_entities_detection_jobs(Filter={"JobName": self.job_name})
            for job in response['EntitiesDetectionJobPropertiesList']:
                if job['JobName'] == self.job_name:
                    return job
            return None
        except Exception as e:
            logging.error(f"Cannot get job list or comprehend job: {e}")
        

    def submit(self):
        "Submit the comprehension job"
        try:
            # get things formatted correctly
            (amp_transcript_obj, amp_entities_obj, ignore_types_list) = amp.nerutils.initialize_amp_entities(self.transcript, self.amp_entities, self.ignore_types)
            self.s3_client.put_object(Body=json.dumps(amp_transcript_obj.results.transcript, default=lambda x: x.__dict__), Bucket=self.s3_bucket, Key=self.job_name + ".json")

            # submit the job
            inputs3uri = f"s3://{self.s3_bucket}/{self.job_name}.json"
            response = self.comprehend_client.start_entities_detection_job(
                InputDataConfig={
                    'S3Uri': inputs3uri,
                    "InputFormat": "ONE_DOC_PER_FILE"
                },
                OutputDataConfig={
                    'S3Uri': f"s3://{self.s3_bucket}/"
                },
                DataAccessRoleArn=self.role_arn,
                JobName=self.job_name,
                LanguageCode='en'
            )
            logging.info(f"Successfully submitted AWS Comprehend job with input {inputs3uri}.")
            return LWLW.WAIT
        except Exception as e:
            logging.exception(f"Exception while submitting AWS Comprehend job with input {inputs3uri}")
            return LWLW.ERROR
        

    def check(self):
        job = self.exists()
        if job is None:
            logging.error(f"The job {self.job_name} should exist but it doesn't!")
            return LWLW.ERROR
        
        if job['JobStatus'] not in ('COMPLETED', 'FAILED', 'STOP_REQUESTED', 'STOPPED'):
            # if it isn't one of these then it's still busy.
            return LWLW.WAIT
        
        if job['JobStatus'] in ('FAILED', 'STOP_REQUESTED', 'STOPPED'):
            logging.error(f"Comprehend job {self.job_name} has completed with an error: {job['JobStatus']}")
            return LWLW.ERROR

        # if we're here, then the job actually completed and we can gather our content.
        # Grab the content from S3
        outputuri = job['OutputDataConfig']['S3Uri']
        logging.info(f"Result in: {outputuri}")
        with tempfile.TemporaryDirectory() as tmpdir:
            (_, _, bucket, key) = outputuri.split('/', 3)
            self.s3_client.download_file(bucket, key, tmpdir + "/output.tar.gz")
            with tarfile.open(tmpdir + "/output.tar.gz") as tfile:
                outdata = tfile.extractfile(tfile.getmember("output")).read()
        
        # output the aws entities data
        with open(self.aws_entities, "wb") as f:
            f.write(outdata)

        aws_entities_json = json.loads(outdata)         
        if not 'Entities' in aws_entities_json.keys():
            logging.error(f"Error: AWS Comprehend output does not contain entities list")
            exit(1)
        aws_entities_list = aws_entities_json["Entities"]

        # preprocess NER inputs and initialize AMP entities output
        [amp_transcript_obj, amp_entities_obj, ignore_types_list] = amp.nerutils.initialize_amp_entities(self.transcript, self.amp_entities, self.ignore_types)

        # populate AMP Entities list based on input AMP transcript words list and output AWS Entities list  
        amp.nerutils.populate_amp_entities2(amp_transcript_obj, aws_entities_list, amp_entities_obj, ignore_types_list)

        # write the output AMP entities to JSON file
        write_json_file(amp_entities_obj, self.amp_entities)
        logging.info("Finished.")
        return LWLW.OK


    def cleanup(self):
        "Clean up the input, output, and job"
        job = self.exists()
        if job is None:
            logging.error(f"The job {self.job_name} should exist but it doesn't!")
            return LWLW.ERROR
        
        try:
            # delete the input document
            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=self.job_name + ".json")

            # delete the output document
            (_, _, bucket, key) = job['OutputDataConfig']['S3Uri'].split('/', 3)
            self.s3_client.delete_object(Bucket=bucket, Key=key)

            # delete the job
            # TODO: not sure how to do this.
            #self.comprehend_client.delete_job(jobId=job['JobId'])     
            return LWLW.OK
        
        except Exception as e:
            logging.error(f"Error deleting the job and files {self.job_name}: {e}")
            return LWLW.ERROR


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("amp_transcript", help="Input transcription file")
    parser.add_argument("aws_entities", help="Output aws entities file")
    parser.add_argument("amp_entities", help="Output amp entities file")
    parser.add_argument("--ignore_types", type=str, default="QUANTITY,DATE", help="Types of things to ignore")
    parser.add_argument("--force", default=False, action="store_true", help="delete any existing jobs with this name and force a new job")
    parser.add_argument("--lwlw", default=False, action="store_true", help="Use LWLW protocol")

    args = parser.parse_args()
    amp.logging.setup_logging("aws_comprehend", args.debug)
    logging.info(f"Starting with args {args}")

    aws_comprehend = AWS_Comprehend(args.amp_transcript, args.aws_entities, args.amp_entities, ignore_types=args.ignore_types)
    exit(aws_comprehend.run(lwlw=args.lwlw, pre_cleanup=args.force))

    
if __name__ == "__main__":
    main()
