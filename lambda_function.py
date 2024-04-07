import os
import boto3
import urllib3
import http
import json
import re
import logging
import traceback
import random
import datetime
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ids = int(os.environ.get('POST_ID'))

dynamodb = boto3.client('dynamodb')


def lambda_handler(event, context):

    text = ""
    url = ""
    id = str(random.randint(0, ids))

    try:
        response = dynamodb.query(
            ExpressionAttributeValues={
                ':v1': {
                    'S': id,
                },
            },
            KeyConditionExpression='id = :v1',
            TableName='BlueskyBotOldBlogPost',
        )

        logger.info("response is %s", response)

        if ('Items' in response):
            text = text + response['Items'][0]['description']['S']
            url = url + response['Items'][0]['url']['S']

        logger.info("description is %s", text)
        logger.info("url is %s", url)

        app_password = get_app_password()
        did = get_did()
        key = get_api_key(did, app_password)

        response = post_skeet(did, key, text, url)

        return response

    except Exception as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return {
            "statusCode": 500,
            "message": 'An error occured at skeet old Blog post.'
        }


def get_app_password():
    ssm = boto3.client("ssm")

    app_password = ssm.get_parameter(Name="bluesky_password", WithDecryption=False)
    app_password = app_password["Parameter"]["Value"]

    return app_password


def get_did():
    http = urllib3.PoolManager()

    HANDLE = "vlayusuke.net"
    DID_URL = "https://bsky.social/xrpc/com.atproto.identity.resolveHandle"

    did_resolve = http.request("GET", DID_URL, fields={"handle": HANDLE})
    did_resolve = json.loads(did_resolve.data)
    did = did_resolve["did"]

    return did


def get_api_key(did, app_password):
    http = urllib3.PoolManager()

    API_KEY_URL = "https://bsky.social/xrpc/com.atproto.server.createSession"

    post_data = {"identifier": did, "password": app_password}
    headers = {"Content-Type": "application/json"}
    api_key = http.request(
        "POST",
        API_KEY_URL,
        headers = headers,
        body = bytes(json.dumps(post_data), encoding="utf-8"),
    )
    api_key = json.loads(api_key.data)

    return api_key["accessJwt"]


def post_skeet(did, key, text, url):
    http = urllib3.PoolManager()

    text = text + "\n\n" + url

    found_uri = find_uri_position(text)

    if found_uri:
        uri, start_position, end_position = found_uri

    post_feed_url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"

    post_record = {
        "collection": "app.bsky.feed.post",
        "repo": did,
        "record": {
            "text": f"{text}",
            "facets": [{
                "index": {
                    "byteStart": start_position,
                    "byteEnd": end_position + 1
                },
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        "uri": uri
                    }
                ]
            }],
            "createdAt": datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None).isoformat(timespec="milliseconds") + "Z",
        }
    }

    post_request = http.request(
        "POST",
        post_feed_url,
        body = json.dumps(post_record),
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )

    post_request = json.loads(post_request.data)

    return post_request


def find_uri_position(text):
    pattern = r'(https?://\S+)'
    match = re.search(pattern, text)

    if match:
        uri = match.group(0)
        start_position = len(text[:text.index(uri)].encode('utf-8'))
        end_position = start_position + len(uri.encode('utf-8')) - 1
        return (uri, start_position, end_position)
    else:
        return None
