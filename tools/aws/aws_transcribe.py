#!/usr/bin/env amp_python.sif

# Script to run a aws transcribe job
# Using https://docs.aws.amazon.com/code-samples/latest/catalog/python-transcribe-transcribe_basics.py.html
# and
# https://docs.aws.amazon.com/code-samples/latest/catalog/python-transcribe-getting_started.py.html
# as a basis.
import argparse
from pathlib import Path
import logging
from time import sleep
import amp.logger
import amp.utils
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import platform
import time

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    # job_directory is really a temporary directory, we don't need that.
    parser.add_argument("input_audio", help="Input audio file")
    parser.add_argument("aws_transcript", help="Output AWS Transcript JSON")
    parser.add_argument("--audio_format", default="wav", help="Format for the audio input")
#     parser.add_argument("--bucket", default='', help="S3 Bucket to use (defaults to value in config)")
#     parser.add_argument("--directory", default='', help="S3 Directory to use in bucket") 
    parser.add_argument("--lwlw", default=True, action="store_true", help="Use LWLW protocol")
    parser.add_argument("--force", default=False, action="store_true", help="delete any existing jobs with this name and force a new job")
    
    args = parser.parse_args()
    logging.info(f"Starting args={args}")

    config = amp.utils.get_config()
#     if args.bucket is None or args.bucket == '':        
    s3_bucket = config.get('aws_transcribe', 's3_bucket', fallback=None)
    if s3_bucket is None:
        logging.error("aws_transcribe/s3_bucket is not specified in the config file")
        exit(1)    
#     if args.directory is None or args.directory == '':
    s3_directory = config.get('aws_transcribe', 's3_directory', fallback='')
    if s3_directory is None:
        logging.error('aws_transcribe/s3_directory is not specified in the config file')
        exit(1)
    s3_directory.strip('/')

    # create the s3 path
    args.input_audio = Path(args.input_audio)
    
    # generate a job name, using the output filename as the basis.    
    job_name = "AWST-" + platform.node().split('.')[0] + args.aws_transcript.replace('/', '-')
    logging.debug(f"Generated job name {job_name}")

    if s3_directory != '':
        object_name = f"{s3_directory}/{job_name}"
    else:
        object_name = job_name
    
    if args.force:
        logging.info(f"Force cleanup of existing job")
        cleanup_job(job_name, s3_bucket, object_name)

    if args.lwlw:
        # if the job exists, check it.  Otherwise, submit a new job.
        if get_job(job_name):
            rc = check_job(job_name, s3_bucket, object_name, args.aws_transcript)
        else:
            rc = submit_job(job_name, args.input_audio, args.audio_format, s3_bucket, object_name)
        exit(rc)
    else:
        # synchronous operation (for testing)
        rc = submit_job(job_name, args.input_audio, args.audio_format, s3_bucket, object_name)
        while rc == 255:
            rc = check_job(job_name, s3_bucket, object_name, args.aws_transcript)
            sleep(10)
        exit(rc)
        

def get_job(job_name):
    "Return the transcription job data or None if it doesn't exist"
    transcribe_client = boto3.client('transcribe', **amp.utils.get_aws_credentials())
    try:
        return transcribe_client.get_transcription_job(TranscriptionJobName=job_name)        
    except ClientError as e:
        if "The requested job couldn't be found" in str(e):
            return None
        raise e

def submit_job(job_name, input_audio, audio_format, bucket, object_name):
    # upload the file to S3
    s3_uri = f"s3://{bucket}/{object_name}"
    s3_client = boto3.client('s3', **amp.utils.get_aws_credentials())    
    try:
        logging.info(f"Uploading file {str(input_audio)} to {s3_uri}")
        response = s3_client.upload_file(str(input_audio), bucket, object_name) #, ExtraArgs={'ACL': 'public-read'})        
    except Exception as e:
        logging.exception(f"Failed to upload file {input_audio}!")
        return 1
    
    # transcribe the file
    try:
        logging.info(f"Starting transcription job {job_name}")
        transcribe_client = boto3.client('transcribe', **amp.utils.get_aws_credentials())
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': s3_uri},
            MediaFormat=audio_format,
            LanguageCode="en-US",
            OutputBucketName=bucket,
            Settings={"ShowSpeakerLabels": True, "MaxSpeakerLabels": 10 }
        )
        logging.info(f"Waiting for transcription job {job_name} to complete")
        return 255
    except Exception as e:
        logging.exception(f"Failed to submit transcription job!")
        cleanup_job(job_name, bucket, object_name)
        return 1


def check_job(job_name, bucket, object_name, aws_transcript):
    "Check on the status of the running job"
    transcribe_client = boto3.client('transcribe', **amp.utils.get_aws_credentials())
    s3_client = boto3.client('s3', **amp.utils.get_aws_credentials()) 
    job = get_job(job_name)
    job_status = job['TranscriptionJob']['TranscriptionJobStatus']
    logging.debug(f"Transcoding job status: {job_status}")
    if job_status == 'COMPLETED':
        transcription_uri = job['TranscriptionJob']['Transcript']['TranscriptFileUri']
        logging.info(f"Result URI: {transcription_uri}.  Result bucket: {bucket}, Key: {job_name + '.json'}")
        s3_client.download_file(Bucket=bucket, Key=job_name + ".json", Filename=aws_transcript)
        cleanup_job(job_name, bucket, object_name)
        logging.info(f"Job {job_name} completed in success!")
        return 0
    elif job_status == 'FAILED':
        logging.error(f"Transcription failed: {job['TranscriptionJob']['FailureReason']}")
        cleanup_job(job_name, bucket, object_name)
        return 1
    # Job is still pending.
    return 255


def cleanup_job(job_name, bucket, object_name):
    "Remove the job and generated data (on aws), and the input file (in s3)"    
    # remove the source data from S3
    try:
        s3_client = boto3.client('s3', **amp.utils.get_aws_credentials())        
        s3_client.delete_object(Bucket=bucket, Key=object_name)
        logging.info(f"Removed {object_name} from S3 bucket {bucket}")
    except Exception as e:
        logging.warning(f"Cannot remove source file {bucket}/{object_name} for job {job_name}:\n{e}")
        
    # remove the job (and generated data) from AWS
    job = get_job(job_name)
    if job:
        try:
            transcribe_client = boto3.client('transcribe', **amp.utils.get_aws_credentials())
            transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
            logging.info(f"Removed AWS Transcribe job {job_name}")
        except Exception as e:
            logging.warning(f"Cannot remove AWS Transcribe job {job_name}:\n{e}")
            pass



if __name__ == "__main__":
    main()
