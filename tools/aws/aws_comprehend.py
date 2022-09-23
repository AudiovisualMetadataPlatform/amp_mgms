#!/usr/bin/env amp_python.sif

import tempfile
import shutil
import tarfile
import socket
import time
from datetime import datetime
import boto3
import argparse
import tempfile
import logging
from amp.config import load_amp_config, get_config_value, get_cloud_credentials
import amp.logging
from amp.fileutils import read_json_file, write_json_file
import amp.nerutils

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("amp_transcript", help="Input transcription file")
    parser.add_argument("aws_entities", help="Output aws entities file")
    parser.add_argument("amp_entities", help="Output amp entities file")
    parser.add_argument("--ignore_types", type=str, default="QUANTITY,DATE", help="Types of things to ignore")
    parser.add_argument("--force", default=False, action="store_true", help="delete any existing jobs with this name and force a new job")

    args = parser.parse_args()
    amp.logging.setup_logging("aws_comprehend", args.debug)
    logging.info(f"Starting with args {args}")

    # fixup the default arguments...
    config = load_amp_config()
    role_arn = get_config_value(config, ['mgms', 'aws_comprehend', 'role_arn'], None)
    if role_arn is None:
        logging.error('mgms.aws_comprehend.role_arn is not specified in the config file')
        exit(1)
    s3_bucket = get_config_value(config, ['mgms', 'aws_comprehend', 's3_bucket'], None)    
    if s3_bucket is None:
        logging.error("mgms.aws_comprehend.s3_bucket is not specified in the config file")
        exit(1)
    s3_directory = get_config_value(config, ['mgms', 'aws_comprehend', 's3_directory'], None)                
    if s3_directory is None:
        logging.error('mgms.aws_comprehend.s3_directory is not specified in the config file')
        exit(1)
    s3_directory.strip('/')        

    # preprocess NER inputs and initialize AMP entities output
    [amp_transcript_obj, amp_entities_obj, ignore_types_list] = amp.nerutils.initialize_amp_entities(args.amp_transcript, args.amp_entities, args.ignore_types)

    # if we reach here, further processing is needed, continue with preparation for AWS Comprehend job 
    # generate a job name, using the output filename as the basis.    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    # hostname + timestamp should ensure unique job name
    jobname = 'AWSC-' + socket.gethostname() + "-" + timestamp      
    s3uri = 's3://' + s3_bucket + '/'

    aws_creds = get_cloud_credentials(config, 'aws')

    with tempfile.TemporaryDirectory() as tmpdir:
        # write AMP Transcript text into the input file in a temp directory and upload it to S3
        upload_input_to_s3(aws_creds, amp_transcript_obj, tmpdir, s3_bucket, jobname)

        # Make call to AWS Comprehend
        outputuri = run_comprehend_job(aws_creds, jobname, s3uri, role_arn)

        # download AWS Comprehend output from s3 to the tmp directory, uncompress and copy it to output aws_entities output file
        download_output_from_s3(aws_creds, outputuri, s3uri, s3_bucket, tmpdir, args.aws_entities)

        # AWS Comprehend output should contain entities
        aws_entities_json = read_json_file(args.aws_entities)
        if not 'Entities' in aws_entities_json.keys():
            logging.error(f"Error: AWS Comprehend output does not contain entities list")
            exit(1)
        aws_entities_list = aws_entities_json["Entities"]

        # populate AMP Entities list based on input AMP transcript words list and output AWS Entities list  
        amp.ner_helper.populate_amp_entities(amp_transcript_obj, aws_entities_list, amp_entities_obj, ignore_types_list)

        # write the output AMP entities to JSON file
        write_json_file(amp_entities_obj, args.amp_entities)
    logging.info("Finished.")
    
# Upload the transcript file created from amp_transcript_obj in tmpdir to the S3 bucket for the given job. 
def upload_input_to_s3(creds, amp_transcript_obj, tmpdir, bucket, jobname):
    # write the transcript text into a tmp input file
    try:
        # use jobname as input filename
        input = tmpdir + "/" + jobname
        with open(input, 'w') as infile:
            infile.write(amp_transcript_obj.results.transcript)
            logging.info(f"Successfully created input file {input} containing transcript for AWS Comprehend job.")
    except Exception as e:
        logging.exception(f"Exception while creating input file {input} containing transcript for AWS Comprehend job.")
        raise
    
    # upload the tmp file to s3
    try:
        s3_client = boto3.client('s3', **creds)
        response = s3_client.upload_file(input, bucket, jobname)
        logging.info(f"Successfully uploaded input file {input} to S3 bucket {bucket} for AWS Comprehend job.")
    except Exception as e:
        logging.exception(f"Exception while uploading input file {input} to S3 bucket {bucket} for AWS Comprehend job.")
        raise

# Download AWS Comprehend output from the given URL in the given S3 bucket to the tmpdir and extract it to aws_entities.
def download_output_from_s3(creds, outputuri, s3uri, bucket, tmpdir, aws_entities):
    # get the output file from s3
    try:
        outkey = outputuri.replace(s3uri, '')
        outname = outkey.rsplit("/", 1)[1]
        output = tmpdir + outname
        s3_client = boto3.client('s3', **creds)    
        s3_client.download_file(bucket, outkey, output)
        logging.info(f"Successfully downloaded AWS Comprehend output {outputuri} to compressed output file {output}.")
    except Exception as e:
        logging.exception(f"Exception while downloading AWS Comprehend output {outputuri} to compressed output file {output}.")
        raise
    
    # extract the contents of the output.tar.gz file and move the uncompressed file to galaxy output
    try:
        tar = tarfile.open(output)
        outputs = tar.getmembers()
        tar.extractall()
        tar.close()
                
        if len(outputs) > 0:
            source = outputs[0].name
            shutil.move(source, aws_entities) 
            logging.info(f"Successfully uncompressed {output} to {source} and moved it to {aws_entities}.")
        else:
            raise Exception(f"Error: Compressed output file {output} does not contain any member.")
    except Exception as e:
        logging.exception(f"Exception while uncompressing/moving {output} to {aws_entities}.")
        raise     

# Run AWS Comprehend job with the given jobname, using the input at the given S3 URL with the given dataAccessRoleArn.
def run_comprehend_job(creds, jobname, s3uri, dataAccessRoleArn):
    # submit AWS Comprehend job
    try:
        # TODO region name should be in MGM config
        comprehend = boto3.client(service_name='comprehend', **creds)
        # jobname was used as the object_name uploaded to s3
        inputs3uri = s3uri + jobname
        response = comprehend.start_entities_detection_job(
            InputDataConfig={
                'S3Uri': inputs3uri,
                "InputFormat": "ONE_DOC_PER_FILE"
            },
            OutputDataConfig={
                'S3Uri': s3uri
            },
            DataAccessRoleArn=dataAccessRoleArn,
            JobName=jobname,
            LanguageCode='en'
        )
        logging.info(f"Successfully submitted AWS Comprehend job with input {inputs3uri}.")
    except Exception as e:
        logging.exception(f"Exception while submitting AWS Comprehend job with input {inputs3uri}")
        raise

    # wait for AWS Comprehend job to end
    status = ''
    outputuri = ''
    try:
        # keep checking every 60 seconds while job still in progress
        while status not in ('COMPLETED','FAILED', 'STOP_REQUESTED','STOPPED'):
            jobStatusResponse = comprehend.describe_entities_detection_job(JobId=response['JobId'])
            status = jobStatusResponse['EntitiesDetectionJobProperties']['JobStatus']
            outputuri = jobStatusResponse['EntitiesDetectionJobProperties']['OutputDataConfig']['S3Uri']
            logging.debug(f"Waiting for AWS Comprehend job {jobname} to complete: status = {status}.")              
            time.sleep(60)        
    except Exception as e:
        logging.exception(f"Exception while running AWS Comprehend job {jobname}")
        raise
    
    # check status of job upon ending
    logging.debug(jobStatusResponse)     
    if status == 'COMPLETED':
        logging.info(f"AWS Comprehend job {jobname} completed in success with output {outputuri}.")  
        return outputuri
    else:
        raise Exception(f"Error: AWS Comprehend job {jobname} ended with status {status}.")
    

if __name__ == "__main__":
    main()
