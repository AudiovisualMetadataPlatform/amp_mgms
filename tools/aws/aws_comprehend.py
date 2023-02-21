#!/usr/bin/env mgm_python.sif


import sys
import tempfile
import shutil
import tarfile
import socket
import time
from datetime import datetime
import boto3
import argparse
import platform
import tempfile
import logging

import amp.logger
import amp.utils
import amp.ner_helper

def main():
    #(amp_transcript, aws_entities, amp_entities, ignore_types, bucket, dataAccessRoleArn) = sys.argv[1:7]
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("amp_transcript", help="Input transcription file")
    parser.add_argument("aws_entities", help="Output aws entities file")
    parser.add_argument("amp_entities", help="Output amp entities file")
    parser.add_argument("--ignore_types", default="QUANTITY, DATE", help="Types of things to ignore")
    parser.add_argument("--force", default=False, action="store_true", help="delete any existing jobs with this name and force a new job")
    parser.add_argument("--lwlw", default=False, action="store_true", help="Run as an LWLW job")

    args = parser.parse_args()
    logging.info(f"Starting with args {args}")
    (amp_transcript, aws_entities, amp_entities, ignore_types) = (args.amp_transcript, args.aws_entities, args.amp_entities, args.ignore_types)

    # fixup the default arguments...
    config = amp.utils.get_config()
    role_arn = config.get('aws_comprehend', 'role_arn', fallback=None)
    if role_arn is None:
        logging.error('aws_comprehend/role_arn is not specified in the config file')
        exit(1)
    s3_bucket = config.get('aws_comprehend', 's3_bucket', fallback=None)
    if s3_bucket is None:
        logging.error("aws_comprehend/s3_bucket is not specified in the config file")
        exit(1)
    s3_directory = config.get('aws_comprehend', 's3_directory', fallback='')
    if s3_directory is None:
        logging.error('aws_comprehend/s3_directory is not specified in the config file')
        exit(1)
    s3_directory.strip('/')        

    # preprocess NER inputs and initialize AMP entities output
    [amp_transcript_obj, amp_entities_obj, ignore_types_list] = amp.ner_helper.initialize_amp_entities(amp_transcript, amp_entities, ignore_types)

    # if we reach here, further processing is needed, continue with preparation for AWS Comprehend job 
    # generate a job name, using the output filename as the basis.    
    job_name = "AWSC-" + platform.node().split('.')[0] + args.output_file.replace('/', '-')
    logging.debug(f"Generated job name {job_name}")

    if args.force:
        cleanup_job(job_name)

    if args.lwlw:
        # if the job exists, check it.  Otherwise, submit a new job.
        if get_job(job_name):
            rc = check_job(job_name, s3_bucket, job_name, args.aws_transcript)
        else:
            rc = submit_job(job_name, s3_bucket, amp_transcript_obj)
        exit(rc)
    else:
        # synchronous operation (for testing)
        rc = submit_job(job_name, s3_bucket, amp_transcript_obj)
        while rc == 255:
            rc = check_job(job_name, s3_bucket, job_name, args.aws_transcript)
            time.sleep(10)
        exit(rc)



def get_job(job_name):
    "Return the comprehension job data or None if it doesn't exist"
    comprehend = boto3.client(service_name='comprehend', **amp.utils.get_aws_credentials())    
    response = comprehend.list_document_classification_jobs(Filter={'JobName': job_name})
    if len(response.get('DocumentClassificationJobPropertiesList', [])):
        return response['DocumentClassificationJobPropertiesList'][0]
    else:
        return None
    
  
def submit_job(job_name, s3_bucket, amp_transcript):
    "Submit the comprehend job"
    # write the transcript data to a file and then upload it to S3
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            ifile = f"{tmpdir}/{job_name}"
            with open(ifile, "w") as f:
                f.write(amp_transcript.results.transcript)
                logging.info(f"Successfully created transcript input file")

            s3_client = boto3.client('s3', **amp.utils.get_aws_credentials())
            response = s3_client.upload_file(ifile, s3_bucket, job_name)
            logging.info(f"Successfully uploaded input file {ifile} to S3 bucket {s3_bucket} for AWS Comprehend job.")
    except Exception as e:
        logging.error("Failed to upload transcript: {e}")
        return 1


    try:
        # TODO region name should be in MGM config
        comprehend = boto3.client(service_name='comprehend', **amp.utils.get_aws_credentials())
        # jobname was used as the object_name uploaded to s3
        inputs3uri = f"s3://{s3_bucket}/{job_name}"
        response = comprehend.start_entities_detection_job(
            InputDataConfig={
                'S3Uri': inputs3uri,
                "InputFormat": "ONE_DOC_PER_FILE"
            },
            OutputDataConfig={
                'S3Uri': f"s3://{s3_bucket}"
            },
            DataAccessRoleArn=dataAccessRoleArn,
            JobName=job_name,
            LanguageCode='en'
        )
        logging.info(f"Successfully submitted AWS Comprehend job with input {inputs3uri}.")
    except Exception as e:
        logging.exception(f"Exception while submitting AWS Comprehend job with input {inputs3uri}")
        cleanup_job(job_name)
        return 1




def check_job():
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
        
        
        # get the output file from s3
        try:
            outkey = outputuri.replace(s3uri, '')
            outname = outkey.rsplit("/", 1)[1]
            output = tmpdir + outname
            s3_client = boto3.client('s3', **amp.utils.get_aws_credentials())    
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

                # Make call to AWS Comprehend
        outputuri = run_comprehend_job(jobname, s3uri, role_arn)

        # download AWS Comprehend output from s3 to the tmp directory, uncompress and copy it to output aws_entities output file
        download_output_from_s3(outputuri, s3uri, s3_bucket, tmpdir, aws_entities)

        # AWS Comprehend output should contain entities
        aws_entities_json = amp.utils.read_json_file(aws_entities)
        if not 'Entities' in aws_entities_json.keys():
            logging.error(f"Error: AWS Comprehend output does not contain entities list")
            exit(1)
        aws_entities_list = aws_entities_json["Entities"]

        # populate AMP Entities list based on input AMP transcript words list and output AWS Entities list  
        amp.ner_helper.populate_amp_entities(amp_transcript_obj, aws_entities_list, amp_entities_obj, ignore_types_list)

        # write the output AMP entities to JSON file
        amp.utils.write_json_file(amp_entities_obj, amp_entities)
        
        logging.info("Finished.")
        return outputuri  # should be return code
    else:
        raise Exception(f"Error: AWS Comprehend job {jobname} ended with status {status}.")
    




def cleanup_job(job_name):
    pass



if __name__ == "__main__":
    main()
