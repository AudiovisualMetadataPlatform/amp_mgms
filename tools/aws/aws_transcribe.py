#!/usr/bin/env amp_python.sif

# Script to run a aws transcribe job
# Using https://docs.aws.amazon.com/code-samples/latest/catalog/python-transcribe-transcribe_basics.py.html
# and
# https://docs.aws.amazon.com/code-samples/latest/catalog/python-transcribe-getting_started.py.html
# as a basis.
import argparse
from pathlib import Path
import logging
import amp.logging
from amp.config import load_amp_config, get_cloud_credentials, get_config_value
import boto3
from botocore.exceptions import ClientError
from amp.lwlw import LWLW
from amp.cloudutils import generate_persistent_name




class AWS_Transcribe(LWLW):
    def __init__(self, audio, transcript, format="wav"):
        self.audio = Path(audio)
        self.transcript = transcript
        self.format = format
        self.config = load_amp_config()
        
        # get/generate bucket, object/job name.
        self.s3_bucket = get_config_value(self.config, ['mgms', 'aws_transcribe', 's3_bucket'], None)    
        if self.s3_bucket is None:
            logging.error("mgms.aws_transcribe.s3_bucket is not specified in the config file")
            exit(1)    
        self.job_name = generate_persistent_name('AWST', self.audio)
         
        # get our cloud clients
        aws_creds = get_cloud_credentials(self.config, 'aws')
        self.transcribe_client = boto3.client('transcribe', **aws_creds)
        self.s3_client = boto3.client('s3', **aws_creds)


    def exists(self):
        "Return the transcription job data or None if it doesn't exist"        
        try:
            return self.transcribe_client.get_transcription_job(TranscriptionJobName=self.job_name)        
        except ClientError as e:
            if "The requested job couldn't be found" in str(e):
                return None
            raise e        


    def submit(self):        
        "Upload the audio file to S3 and submit the transcription job"
        # upload the file to S3
        input_uri = f"s3://{self.s3_bucket}/{self.job_name}"
 
        try:
            logging.info(f"Uploading file {str(self.audio)} to {input_uri}")
            self.s3_client.upload_file(str(self.audio), self.s3_bucket, self.job_name)
        except Exception as e:
            logging.exception(f"Failed to upload file {self.audio}: {e}!")
            return 1
        
        # transcribe the file
        try:
            logging.info(f"Starting transcription job {self.job_name}")            
            self.transcribe_client.start_transcription_job(
                TranscriptionJobName=self.job_name,
                Media={'MediaFileUri': input_uri},
                MediaFormat=self.format,
                LanguageCode="en-US",
                OutputBucketName=self.s3_bucket,
                Settings={"ShowSpeakerLabels": True, "MaxSpeakerLabels": 10 }
            )
            logging.info(f"Waiting for transcription job {self.job_name} to complete")
            return LWLW.WAIT
        except Exception as e:
            logging.exception(f"Failed to submit transcription job!")
            return LWLW.ERROR


    def check(self):
        "Check on the status of the running job"
        job = self.exists()
        if job is None:
            logging.error(f"The job {self.job_name} should exist but it doesn't!")
            return LWLW.ERROR
        
        job_status = job['TranscriptionJob']['TranscriptionJobStatus']
        logging.debug(f"Transcoding job status: {job_status}")
        if job_status == 'COMPLETED':
            transcription_uri = job['TranscriptionJob']['Transcript']['TranscriptFileUri']
            logging.info(f"Result URI: {transcription_uri}.  Result bucket: {self.s3_bucket}, Key: {self.job_name + '.json'}")
            try:
                self.s3_client.download_file(Bucket=self.s3_bucket, Key=self.job_name + ".json", Filename=self.transcript)
                logging.info(f"Job {self.job_name} completed in success!")
                return LWLW.OK
            except Exception as e:
                logging.error(f"Failed to download result: {e}")
                return LWLW.ERROR
        elif job_status == 'FAILED':
            logging.error(f"Transcription failed: {job['TranscriptionJob']['FailureReason']}")
            return LWLW.ERROR
        # Job is still pending.
        return LWLW.WAIT


    def cleanup(self):
        "Remove the job and generated data (on aws), and the input file (in s3)"    
        # remove the source data from S3
        try:
            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=self.job_name)
            logging.info(f"Removed {self.job_name} from S3 bucket {self.s3_bucket}")
        except Exception as e:
            logging.warning(f"Cannot remove source file {self.s3_bucket}/{self.job_name} for job {self.job_name}:\n{e}")
            
        # remove the job (and generated data) from AWS
        job = self.exists()
        if job:
            try:
                self.s3_client.delete_object(Bucket=self.s3_bucket, Key=self.job_name + ".json")
                logging.info(f"Removed result file {self.job_name}.json from S3 Bucket {self.s3_bucket}")
                self.transcribe_client.delete_transcription_job(TranscriptionJobName=self.job_name)
                logging.info(f"Removed AWS Transcribe job {self.job_name}")
            except Exception as e:
                logging.warning(f"Cannot remove AWS Transcribe job {self.job_name}:\n{e}")
                pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    # job_directory is really a temporary directory, we don't need that.
    parser.add_argument("input_audio", help="Input audio file")
    parser.add_argument("aws_transcript", help="Output AWS Transcript JSON")
    parser.add_argument("--audio_format", default="wav", help="Format for the audio input")
    parser.add_argument("--lwlw", default=False, action="store_true", help="Use LWLW protocol")
    parser.add_argument("--force", default=False, action="store_true", help="delete any existing jobs with this name and force a new job")
    
    args = parser.parse_args()
    amp.logging.setup_logging("aws_transcribe", args.debug)
    logging.info(f"Starting args={args}")

    transcribe = AWS_Transcribe(args.input_audio, args.aws_transcript, format=args.audio_format)
    exit(transcribe.run(lwlw=args.lwlw, pre_cleanup=args.force))


if __name__ == "__main__":
    main()
