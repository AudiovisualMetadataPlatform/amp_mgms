#!/bin/env mgm_python.sif

# Script to run a aws transcribe job
# Using https://docs.aws.amazon.com/code-samples/latest/catalog/python-transcribe-transcribe_basics.py.html
# and
# https://docs.aws.amazon.com/code-samples/latest/catalog/python-transcribe-getting_started.py.html
# as a basis.
import argparse
from pathlib import Path
import logging
import tempfile
from time import sleep
import amp.logger
import amp.utils
import boto3
import platform
import os
from datetime import datetime

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    # job_directory is really a temporary directory, we don't need that.
    parser.add_argument("input_file")
    parser.add_argument("output_file")
    parser.add_argument("--audio_format", default="wav", help="Format for the audio input")
    parser.add_argument("--bucket", default='', help="S3 Bucket to use (defaults to value in config)")
    parser.add_argument("--directory", default='', help="S3 Directory to use in bucket")
    args = parser.parse_args()
    logging.info(f"Starting args={args}")

    config = amp.utils.get_config()
    if args.bucket is None or args.bucket == '':        
        args.bucket = config.get('aws_transcribe', 'default_bucket', fallback=None)
        if args.bucket is None:
            logging.error("--bucket not specified and aws_transcribe/default_bucket not set in config")
            exit(1)
    
    if args.directory is None or args.directory == '':
        args.directory = config.get('aws_transcribe', 'default_directory', fallback='')
        if args.directory is None:
            logging.error('--directory not specified and aws_transcribe/default_directory not set in config')
            exit(1)
        if args.directory.startswith("/") or args.directory.endswith("/"):
            logging.error("Directory must not begin or end with '/'")
            exit(1)

    # create the s3 path
    args.input_file = Path(args.input_file)
    
    # create a unique job/object name ("<directory>/AWS-Transcribe-<hostname>-<date>-<time>-<pid>")
    job_name = f"AWS-Transcribe-{platform.node().split('.')[0]}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    if args.directory != '':
        object_name = f"{args.directory}/{job_name}"
    else:
        object_name = job_name
    s3_uri = f"s3://{args.bucket}/{object_name}"

    # upload the file to S3
    s3_client = boto3.client('s3', **amp.utils.get_aws_credentials())    
    try:
        logging.debug(f"Uploading file {str(args.input_file)} to {s3_uri}")
        response = s3_client.upload_file(str(args.input_file), args.bucket, object_name) #, ExtraArgs={'ACL': 'public-read'})        
    except Exception as e:
        logging.error(f"Uploading file {args.input_file} failed: {e}")
        exit(1)
    
    # transcribe the file
    transcribe_client = boto3.client('transcribe', **amp.utils.get_aws_credentials())
    transcribe_exception = False
    try:
        logging.debug(f"Starting transcription job {job_name}")
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': s3_uri},
            MediaFormat=args.audio_format,
            LanguageCode="en-US",
            OutputBucketName=args.bucket,
            Settings={"ShowSpeakerLabels": True, "MaxSpeakerLabels": 10 }
        )
        logging.debug(f"Waiting for transcription job {job_name} to complete")
        while True:
            job = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            job_status = job['TranscriptionJob']['TranscriptionJobStatus']
            logging.debug(f"Transcoding job status: {job_status}")
            if job_status == 'COMPLETED':
                transcription_uri = job['TranscriptionJob']['Transcript']['TranscriptFileUri']
                logging.info(f"Result URI: {transcription_uri}")
                s3_client.download_file(Bucket=args.bucket, Key=object_name + ".json", Filename=args.output_file)
                s3_client.delete_object(Bucket=args.bucket, Key=object_name + ".json")
                break
            elif job_status == 'FAILED':
                logging.error(f"Transcription failed: {job['TranscriptionJob']['FailureReason']}")
                transcribe_exception = True
                break
            sleep(10)
    except Exception as e:
        logging.error(f"Exception during transcription: {e}")
        transcribe_exception = True

    # delete the input file from S3
    try:
        logging.debug(f"Deleting file {object_name} from s3 bucket {args.bucket}")
        s3_client.delete_object(Bucket=args.bucket, Key=object_name)        
    except Exception as e:
        logging.error(f"Failed to delete file {object_name} from s3 bucket {args.bucket}: {e}")
        transcribe_exception = True





    if transcribe_exception:
        logging.error("Transcription failed")
        exit(1)

    logging.info("Finished")

"""
# Usage:
# transcribe $input_file $job_directory $output_file $audio_format $s3_bucket $s3_directory

# TODO: shall we use ENV var for <S3_bucket> <s3_directory>, <job_directory>? 
# The reason for it is to avoid passing parameter to script each time (although since the script is only called by Galaxy not a human, it probably doesn't matter);
# the reason against it is that it makes the tool less flexible and more dependent.

# record transcirbe command parameters
job_directory=$1
input_file=$2
output_file=$3
audio_format=$4
s3_bucket=$5
s3_directory=$6

# TODO 
# Galaxy change binary input file extension to .dat for all media files, which means we can't infer audio format from file extension.
# We could use file utility to extract MIME type to obtain audio format; for now We let user specify audio format as a parameter.

# AWS Transcribe service requires a unique job name when submitting a job under the same account.
# Suffixing to the job name with hostname and timestamp shall make the name unique enough in real case.
# In addition, all AWS job related files should go to a designated directory $job_directory, and file names can be prefixed by the job_name. 
job_name_prefix="AwsTranscribe"
job_name_suffix=$(printf "%s-%s-%s" $(hostname -s) $(date +%Y%m%d%H%M%S) $$)
job_name=${job_name_prefix}-${job_name_suffix}
log_file=${job_directory}/${job_name}.log
# create job_directory if not existing yet
#if [ ! -d ${job_directory} ] 
#then
#    mkdir ${job_directory}
#fi
echo "echo ${input_file} ${output_file} ${audio_format} ${s3_bucket} ${s3_directory} ${job_directory} ${job_name} >> $log_file 2>&1" # debug

# if s3_directory is empty or ends with "/" return it as is; otherwise append "/" at the end
s3_path=`echo $s3_directory| sed -E 's|([^/])$|\1/|'`
# upload media file from local Galaxy source file to S3 directory
echo "Uploading ${input_file} to s3://${s3_bucket}/${s3_path}" >> $log_file 2>&1 
aws s3 cp ${input_file} s3://${s3_bucket}/${s3_path} >> $log_file 2>&1

# create json file in the aws directory, i.e. <job_directory>/<job_name>_request.json
request_file=${job_directory}/${job_name}-request.json
input_file_name=$(basename ${input_file})
media_file_url="http://${s3_bucket}.s3.amazonaws.com/${s3_path}${input_file_name}"

# use user-specified bucket for output for easier access control
jq -n "{ \"TranscriptionJobName\": \"${job_name}\", \"LanguageCode\": \"en-US\", \"MediaFormat\": \"${audio_format}\", \"Media\": { \"MediaFileUri\": \"${media_file_url}\" }, \"OutputBucketName\": \"${s3_bucket}\", \"Settings\":{ \"ShowSpeakerLabels\": true, \"MaxSpeakerLabels\": 10 } }" > ${request_file}
 
# submit transcribe job
echo "Starting transcription job ${job_name} using request file ${request_file}" >> $log_file 2>&1
aws transcribe start-transcription-job --cli-input-json file://${request_file} >> $log_file 2>&1

# wait while job is running
echo "Waiting for ${job_name} to finish ..." >> $log_file 2>&1
# note: both AWS query and jq parsing returns field value with double quotes, which needs to be striped off when comparing to string literal
while [[ `aws transcribe get-transcription-job --transcription-job-name "${job_name}" --query "TranscriptionJob"."TranscriptionJobStatus" | sed -e 's/"//g'` = "IN_PROGRESS" ]] 
do
    sleep 60s
done

# retrieve job response
response_file=${job_directory}/${job_name}-response.json
aws transcribe get-transcription-job --transcription-job-name "${job_name}" > ${response_file}
cat $response_file >> $log_file 2>&1
job_status=`jq '.TranscriptionJob.TranscriptionJobStatus' < $response_file | sed -e 's/"//g'`

# if job succeeded, retrieve output file URL and download output file from the URL to galaxy output file location
if [[ ${job_status} = "COMPLETED" ]]; then
# since we use user defined bucket for transcribe output, its S3 location can be inferred following the naming pattern as below
# and we don't need to use the provided URL in the response, as that would require using curl and would encounter permission issue for private files
	transcript_file_uri=s3://${s3_bucket}/${job_name}.json
	aws s3 cp $transcript_file_uri $output_file >> $log_file 2>&1
    echo "Job ${job_name} completed in success!" >> $log_file 2>&1
    exit 0
# otherwise print error message to the log and exit with error code
elif [[ ${job_status} = "FAILED" ]]; then
    echo "Job ${job_name} failed!" >> $log_file 2>&1
    exit 1
else
    echo "Job ${job_name} ended in unexpected status: ${job_status}" >> $log_file 2>&1
    exit 2
fi

"""

if __name__ == "__main__":
    main()
