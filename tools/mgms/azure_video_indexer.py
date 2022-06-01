#!/usr/bin/env mgm_python.sif
import argparse
import sys
import traceback
import requests
import logging
import time
import json
import uuid
import boto3
from distutils.util import strtobool
import logging

import amp.logger
import amp.utils

def main():
    apiUrl = "https://api.videoindexer.ai"

    #(root_dir, input_video, include_ocr, region_name, azure_video_index, azure_artifact_ocr) = sys.argv[1:7]
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", default=False, action="store_true", help="Turn on debugging")
    parser.add_argument("input_video", help="Input video file")
    parser.add_argument("include_ocr", type=strtobool, default=True, help="Include OCR")
#     parser.add_argument("region_name", help="Azure account region")
    parser.add_argument("azure_video_index", help="Azure Video Index JSON")
    parser.add_argument("azure_artifact_ocr", help="Azure Artifact OCR JSON")
    args = parser.parse_args()
    logging.info(f"Starting with args {args}")
    (input_video, include_ocr, azure_video_index, azure_artifact_ocr) = (args.input_video, args.include_ocr, args.azure_video_index, args.azure_artifact_ocr)
#     (input_video, include_ocr, region_name, azure_video_index, azure_artifact_ocr) = (args.input_video, args.include_ocr, args.region_name, args.azure_video_index, args.azure_artifact_ocr)

    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client

    azure = amp.utils.get_azure_credentials()
    account_id = azure['account_id']
    api_key = azure['api_key']
    region_name = azure['region_name']
    s3_bucket = azure['s3_bucket']

    # Turn on HTTP debugging here
    http_client.HTTPConnection.debuglevel = 1

    # upload video to S3
    s3_path = upload_to_s3(input_video, s3_bucket)
    if not s3_path:
#         logging.error(f"Failed to upload {input_video} to AWS bucket {s3_bucket}")
        exit(1)
#     logging.info(f"Uploaded {input_video} to AWS S3 bucket {s3_path}")
    
    # Get an authorization token for subsequent requests
    auth_token = get_auth_token(apiUrl, region_name, account_id, api_key)
    
    # Upload the video and get the ID to reference for indexing status and results
    video_url = "https://" + s3_bucket + ".s3.us-east-2.amazonaws.com/" + s3_path
    videoId = index_video(apiUrl, region_name, account_id, auth_token, input_video, video_url)

    # Get the auth token associated with this video    
    # video_auth_token = get_video_auth_token(apiUrl, region_name, account_id, api_key, videoId)

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
    amp.utils.write_json_file(index_json, azure_video_index)

    # Get the advanced OCR json via the artifact URL if requested
    if include_ocr:
        try:
            artifacts_url = get_artifacts_url(apiUrl, region_name, account_id, videoId, auth_token, 'ocr')
            download_artifacts(artifacts_url, azure_artifact_ocr)
            log.info(f"Downloaded OCR artifact to {azure_artifact_ocr}")
        # When the video doesn't contain OCR, no OCR artifact will be generated, and the above download will result in exception.
        # Since we may not know before hand if a video contains OCR or not, this should be a normal case and not cause job failure;
        # instead, we can generate an empty OCR output, and the next job should handle such case and generate empty AMP VOCR.
        # However, the exception could also be caused by system errors, in which case job should fail.
        # TODO should we fail the job or generate an empty OCR file ?
        except:
            logging.exception(f"Failed to download OCR artifact to {azure_artifact_ocr}", e)    
    
    delete_from_s3(s3_path, s3_bucket)
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
        logging.error("Auth failure")
        logging.error(r)
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
                logging.error("no id in data")
                exit(1)

def upload_to_s3(input_video, bucket):
    s3_client = boto3.client('s3', **amp.utils.get_aws_credentials())
    jobname = str(uuid.uuid1())
    try:
        response = s3_client.upload_file(input_video, bucket, jobname, ExtraArgs={'ACL': 'public-read'})
        logging.info("Uploaded file " + input_video + " to s3 bucket " + bucket)
    except Exception as e:
        logging.error("Failed to upload file " + input_video + " to s3 bucket " + bucket, e)
        traceback.print_exc()
        return None
    return jobname

def delete_from_s3(s3_path, bucket):
    s3_client = boto3.resource('s3', **amp.utils.get_aws_credentials())
    try:
        obj = s3_client.Object(bucket, s3_path)
        obj.delete()
        logging.info("Deleted file " + s3_path + " from s3 bucket " + bucket)
    except Exception as e:
        logging.error("Failed to delete file " + s3_path + " from s3 bucket " + bucket, e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
