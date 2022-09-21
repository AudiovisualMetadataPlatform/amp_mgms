#!/usr/bin/env amp_python.sif
import argparse
import requests
import logging
import time
import json
import uuid
import boto3
from distutils.util import strtobool
import logging
import http.client as http_client

import amp.logging
from amp.config import load_amp_config, get_config_value, get_cloud_credentials
from amp.fileutils import write_json_file

def main():
    apiUrl = "https://api.videoindexer.ai"
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("input_video", help="Input video file")
    parser.add_argument("--include_ocr", type=strtobool, default=True, help="Include OCR")
    parser.add_argument("azure_video_index", help="Azure Video Index JSON")
    parser.add_argument("azure_artifact_ocr", help="Azure Artifact OCR JSON")
    args = parser.parse_args()
    amp.logging.setup_logging("azure_video_indexer", args.debug)
    logging.info(f"Starting with args {args}")
    
    config = load_amp_config()
    azure = get_cloud_credentials(config, 'azure')
    account_id = azure['account_id']
    api_key = azure['api_key']
    region_name = azure['region_name']
    s3_bucket = get_config_value(config, ['mgms', 'azure_video_indexer', 's3_bucket'])
    
    # Turn on HTTP debugging here
    http_client.HTTPConnection.debuglevel = 1

    aws_creds = get_cloud_credentials(config, 'aws')
    if args.debug:
        http_client.HTTPConnection.debuglevel = 1

    aws_creds = get_cloud_credentials(config, 'aws')

    # upload video to S3
    s3_path = upload_to_s3(aws_creds, args.input_video, s3_bucket)
    
    # Get an authorization token for subsequent requests
    auth_token = get_auth_token(apiUrl, region_name, account_id, api_key)
    
    # Upload the video and get the ID to reference for indexing status and results
    video_url = "https://" + s3_bucket + ".s3.us-east-2.amazonaws.com/" + s3_path
    videoId = index_video(apiUrl, region_name, account_id, auth_token, args.input_video, video_url)

    # Check on the indexing status
    while True:
        # The token expires after an hour.  Let's just refresh every iteration
        video_auth_token = get_video_auth_token(apiUrl, region_name, account_id, api_key, videoId)
        state = get_processing_status(apiUrl, region_name, account_id, videoId, video_auth_token)
        
        # We have a status other than uploaded or processing, it is complete
        if state != "Uploaded" and state != "Processing":
            break
        
        # Wait a bit before checking again
        time.sleep(60)

    # Turn on HTTP debugging here
    http_client.HTTPConnection.debuglevel = 1

    # Get the simple video index json
    auth_token = get_auth_token(apiUrl, region_name, account_id, api_key)
    index_json = get_video_index_json(apiUrl, region_name, account_id, videoId, auth_token, api_key)
    write_json_file(index_json, args.azure_video_index)

    # Get the advanced OCR json via the artifact URL if requested
    if args.include_ocr:
        try:
            artifacts_url = get_artifacts_url(apiUrl, region_name, account_id, videoId, auth_token, 'ocr')
            download_artifacts(artifacts_url, args.azure_artifact_ocr)
            logging.info(f"Downloaded OCR artifact to {args.azure_artifact_ocr}")
        # When the video doesn't contain OCR, no OCR artifact will be generated, and the above download will result in exception.
        # Since we may not know before hand if a video contains OCR or not, this should be a normal case and not cause job failure;
        # instead, we can generate an empty OCR output, and the next job should handle such case and generate empty AMP VOCR.
        # However, the exception could also be caused by system errors, in which case job should fail.
        # TODO should we fail the job or generate an empty OCR file ?
        except:
            logging.exception(f"Failed to download OCR artifact to {args.azure_artifact_ocr}!")    
    
    delete_from_s3(aws_creds, s3_path, s3_bucket)
    logging.info("Finished.")


# Retrieve the "artifacts" (ocr json) from the specified url
def download_artifacts(artifacts_url, output_name):
    r = requests.get(url = artifacts_url)
    with open(output_name, 'wb') as f:
        f.write(r.content)
    return output_name

# Get the url where the artifacts json is stored
def get_artifacts_url(apiUrl, region_name, account_id, videoId, auth_token, type):
    url = apiUrl + "/" + region_name + "/Accounts/" + account_id + "/Videos/" + videoId + "/ArtifactUrl"
    params = {'accessToken':auth_token, 'type':type}
    r = requests.get(url = url, params = params)
    return r.text.replace("\"", "")

# Get the video index json, which contains OCR data
def get_video_index_json(apiUrl, region_name, account_id, videoId, auth_token, api_key):
    url = apiUrl + "/" + region_name + "/Accounts/" + account_id + "/Videos/" + videoId + "/Index"
    params = {'accessToken':auth_token }
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    r = requests.get(url = url, params=params, headers = headers) 
    return json.loads(r.text)

# Get the processing status of the video
def get_processing_status(apiUrl, region_name, account_id, videoId, video_auth_token):
    video_url = apiUrl + "/" + region_name + "/Accounts/" + account_id + "/Videos/" + videoId + "/Index"
    params = {'accessToken':video_auth_token,
                'language':'English'}
    r = requests.get(url = video_url, params = params)
    data = json.loads(r.text)
    if 'videos' in data.keys():
        videos = data['videos']
        if 'state' in videos[0].keys():
            return videos[0]['state']
    return "Error"

# Create the auth token request
def request_auth_token(url, api_key):
    params = {'allowEdit':True} 
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    # sending get request and saving the response as response object 
    r = requests.get(url = url, params = params, headers=headers) 
    if r.status_code == 200:
        return r.text.replace("\"", "")
    else:
        logging.error(f"Auth failure: {r}")
        exit(1)

# Get general auth token
def get_auth_token(apiUrl, region_name, account_id, api_key):
    token_url = apiUrl + "/auth/" + region_name + "/Accounts/" + account_id + "/AccessToken"
    return request_auth_token(token_url, api_key)

# Get video auth token
def get_video_auth_token(apiUrl, region_name, account_id, api_key, videoId):
    token_url = apiUrl + "/auth/" + region_name + "/Accounts/" + account_id + "/Videos/" + videoId + "/AccessToken"
    return request_auth_token(token_url, api_key)

# Index the video using multipart form upload.
def index_video(apiUrl, region_name, account_id, auth_token, input_video, video_url):
    # Create a unique file name 
    millis = int(round(time.time() * 1000))
    upload_url = apiUrl + "/" + region_name +  "/Accounts/" + account_id + "/Videos"    
    data = {}
    
    with open(input_video, 'rb') as f:
        params = {'accessToken':auth_token,
                'name':'amp_video_' + str(millis),
                'description':'AMP File Upload',
                'privacy':'private',
                'partition':'No Partition',
                'videoUrl':video_url}
        r = requests.post(upload_url, params = params)
        
        if r.status_code != 200:
            logging.error("Upload failure:" + r)            
            exit(1)
        else:
            data = json.loads(r.text)
            if 'id' in data.keys():
                return data['id']
            else:
                logging.error("No id in data")
                exit(1)

def upload_to_s3(creds, input_video, bucket):
    s3_client = boto3.client('s3', **creds)
    jobname = str(uuid.uuid1())
    try:
        response = s3_client.upload_file(input_video, bucket, jobname, ExtraArgs={'ACL': 'public-read'})
        logging.info(f"Uploaded file {input_video} to S3 bucket {bucket}")
        return jobname
    except Exception as e:
        logging.exception(f"Failed to upload file {input_video} to S3 bucket {bucket}!")
        exit(1)

def delete_from_s3(creds, s3_path, bucket):
    s3_client = boto3.resource('s3', **creds)
    try:
        obj = s3_client.Object(bucket, s3_path)
        obj.delete()
        logging.info(f"Deleted file {s3_path} from S3 bucket {bucket}")
    except Exception as e:
        logging.warning(f"Failed to delete file {s3_path} from S3 bucket {bucket}:\n{e}")


if __name__ == "__main__":
    main()
