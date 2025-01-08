#!/usr/bin/env amp_python.sif
import argparse
import requests
import logging
import time
import json
import boto3
from distutils.util import strtobool
import logging
import http.client as http_client
from pathlib import Path

import amp.logging
from amp.config import load_amp_config, get_config_value, get_cloud_credentials
from amp.fileutils import write_json_file
from amp.lwlw import LWLW
from amp.cloudutils import generate_persistent_name

# chunks shamelessly stolen from 
# https://github.com/Azure-Samples/azure-video-indexer-samples/blob/master/API-Samples/Python/





def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("input_video", help="Input video file")
    parser.add_argument("--include_ocr", type=strtobool, default=True, help="Include OCR")
    parser.add_argument("azure_video_index", help="Azure Video Index JSON")
    parser.add_argument("azure_artifact_ocr", help="Azure Artifact OCR JSON")
    parser.add_argument("--force", default=False, action="store_true", help="delete any existing jobs with this name and force a new job")
    parser.add_argument("--lwlw", default=False, action="store_true", help="Use LWLW protocol")    
    args = parser.parse_args()
    amp.logging.setup_logging("azure_video_indexer", args.debug)
    logging.info(f"Starting with args {args}")

    # turn on debugging for http_client
    if args.debug:
        http_client.HTTPConnection.debuglevel = 1

    avi = AzureVideoIndexer(args.input_video, args.azure_video_index, args.azure_artifact_ocr if args.include_ocr else None)
    exit(avi.run(lwlw=args.lwlw, pre_cleanup=args.force, pause=90))


class AzureVideoIndexer(LWLW):
    def __init__(self, input_video, azure_video_index, azure_artifact_ocr=None):
        "Initialize the AVI"
        self.input_video = input_video
        self.azure_video_index = azure_video_index
        self.azure_artifact_ocr = azure_artifact_ocr

        self.config = load_amp_config()
        # AWS Stuff
        self.s3_bucket = get_config_value(self.config, ['mgms', 'azure_video_indexer', 's3_bucket'])
        self.aws_creds = get_cloud_credentials(self.config, 'aws')
        self.s3_client = boto3.client("s3", **self.aws_creds)

        # Azure Stuff
        self.azure_creds = get_cloud_credentials(self.config, 'azure')
        self.api_url_base = f"https://api.videoindexer.ai/{self.azure_creds['region_name']}/Accounts/{self.azure_creds['account_id']}"
        self.auth_token = None
        self.auth_token_expire = 0

        self.job_name = generate_persistent_name("AzureVideoIndexer-", self.input_video, self.azure_video_index)


    def exists(self):
        "Get information about the job or None if it doesn't exist"
        check_url = f"{self.api_url_base}/Videos"
        r = requests.get(check_url,
                            params={'accessToken': self._get_request_token()})
        data = json.loads(r.text)
        for r in data['results']:
            logging.debug(f"{r['id']}: {r['name']} ({r['externalId']}) {r['state']}")
            if r['externalId'] == self.job_name:
                return r

        return None        


    def submit(self):
        "Submit the job to AVI"
        # upload the source video
        try:
            self.s3_client.upload_file(self.input_video, self.s3_bucket, self.job_name,
                                       ExtraArgs={'ACL': 'public-read'})
            logging.info(f"Uploaded source file {self.input_video} to s3://{self.s3_bucket}/{self.job_name}")
        except Exception as e:
            logging.error(f"Failed to upload source file {self.input_video} to s3://{self.s3_bucket}/{self.job_name}: {e}")
            return LWLW.ERROR
        
        # submit the job.
        try:
            # construct an AWS S3 video URL for AVI
            video_url = f"https://{self.s3_bucket}.s3.{self.aws_creds['region_name']}.amazonaws.com/{self.job_name}"
            upload_url = self.api_url_base + "/Videos"
            r = requests.post(upload_url,
                            params={
                                'accessToken': self._get_request_token(),
                                'name': Path(self.input_video).name,
                                'description': 'AMP File Upload',
                                'privacy': 'private',
                                'partition': 'No Partition',
                                'videoUrl': video_url,
                                'externalId': self.job_name
                            })
            if r.status_code != 200:
                logging.error(f"Failed to submit job: {r.text}")
                return LWLW.ERROR
            
            # log the ID of the job.
            data = json.loads(r.text)
            logging.info(f"Azure Video Indexer job id: {data['id']}")
            return LWLW.WAIT
        
        except Exception as e:
            logging.error(f"Exception submitting job: {e}")
            return LWLW.ERROR
        

    def check(self):
        "Check on the status and handle results if ready"
        job = self.exists()
        if job is None:
            logging.error(f"The job {self.job_name} should exist but it doesn't!")
            return LWLW.ERROR
        
        if job['state'] in ('Uploaded', 'Processing'):
            # it's still in flight.  just wait.
            return LWLW.WAIT
        
        # write the Azure Video Index data to a file
        r = requests.get(url=f"{self.api_url_base}/Videos/{job['id']}/Index",
                         params={
                            'accessToken': self._get_request_token(),
                            'language': 'English',
                            'includeSummarizedInsights': 'true',
                        })       
        if r.status_code != 200:
            logging.error(f"Cannot retrieve insights for {job['id']}: {r.text}")
            return LWLW.ERROR
        with open(self.azure_video_index, "wb") as f:
            f.write(r.content)

        # if OCR was requested, handle it.
        if self.azure_artifact_ocr:
            get_artifact_url = f"{self.api_url_base}/Videos/{job['id']}/ArtifactUrl"
            r = requests.get(url=get_artifact_url, 
                             params={'type': 'ocr',
                                     'accessToken': self._get_request_token()})
            if r.status_code != 200:
                logging.error(f"Cannot get URL for OCR Download: {r.text}")
                return LWLW.ERROR
            ocr_url = json.loads(r.text)
            logging.info(f"OCR URL: {ocr_url}")
            r = requests.get(url=ocr_url)
            with open(self.azure_artifact_ocr, "wb") as f:
                f.write(r.content)
            logging.info(f"OCR output written to {self.azure_artifact_ocr}")

        return LWLW.OK
        

    def cleanup(self):
        "Clean up the job artifacts"
        try:
            # delete the AWS S3 file        
            logging.info("Removing S3 Video source")
            self.s3_client.delete_object(Bucket=self.s3_bucket, Key=self.job_name)
            
            # delete the Azure stuff
            logging.info("Removing Video Indexer Job")
            job = self.exists()
            if job:
                video_url = f"{self.api_url_base}/Videos/{job['id']}"
                requests.delete(url=video_url,
                                params={'accessToken': self._get_request_token()})
            return LWLW.OK    
        except Exception as e:
            logging.error(f"Failed to clean up job artifacts: {e}")
            return LWLW.ERROR


    def _get_request_token(self):
        "Request an auth token"
        if time.time() > self.auth_token_expire or self.auth_token is None:
            logging.info("Requesting new auth token")
            auth_url = f"https://api.videoindexer.ai/Auth/{self.azure_creds['region_name']}/Accounts/{self.azure_creds['account_id']}/AccessToken"
            r = requests.get(url=auth_url, params={'allowEdit': True},
                            headers={'Ocp-Apim-Subscription-Key': self.azure_creds['api_key']} )
            if r.status_code != 200:
                raise Exception(f"Auth failure on {self.api_url_base}: {r}")

            self.auth_token = r.text.replace('"', '')
            self.auth_token_expire = time.time() + 1800  # 30 minutes
            
        return self.auth_token


if __name__ == "__main__":
    main()
