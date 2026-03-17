import os
import json
import time
import sys
from datetime import datetime

import boto3

AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-1")
QUEUE_URL = os.getenv("SQS_QUEUE_URL")

WAIT_TIME_SECONDS = int(os.getenv("WAIT_TIME_SECONDS", "10"))   # long polling
MAX_NUMBER_OF_MESSAGES = int(os.getenv("MAX_NUMBER_OF_MESSAGES", "1"))
VISIBILITY_TIMEOUT = int(os.getenv("VISIBILITY_TIMEOUT", "30"))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "2"))


if not QUEUE_URL:
    raise RuntimeError("Missing env: SQS_QUEUE_URL")

sqs = boto3.client("sqs", region_name=AWS_REGION)


def now():
    return datetime.utcnow().isoformat() + "Z"


def receive_messages():
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=MAX_NUMBER_OF_MESSAGES,
        WaitTimeSeconds=WAIT_TIME_SECONDS,
        VisibilityTimeout=VISIBILITY_TIMEOUT,
        MessageAttributeNames=["All"],
        AttributeNames=["All"],
    )
    return response.get("Messages", [])


def delete_message(receipt_handle: str):
    sqs.delete_message(
        QueueUrl=QUEUE_URL,
        ReceiptHandle=receipt_handle
    )


def process_message(message: dict):
    message_id = message.get("MessageId")
    receipt_handle = message.get("ReceiptHandle")
    body_raw = message.get("Body", "{}")

    print("=== SQS MESSAGE RECEIVED ===")
    print(json.dumps({
        "ts": now(),
        "message_id": message_id,
        "body_raw": body_raw
    }, ensure_ascii=False))

    try:
        body = json.loads(body_raw)
    except Exception:
        body = {"raw_body": body_raw}

    request_id = body.get("request_id", "no-request-id")
    action = body.get("action", "no-action")
    source = body.get("source", "unknown")

    print(json.dumps({
        "status": "ok",
        "message": "SQS message received by ECS worker",
        "request_id": request_id,
        "action": action,
        "source": source,
        "message_id": message_id
    }, ensure_ascii=False))

    delete_message(receipt_handle)

    print(json.dumps({
        "status": "ok",
        "message": "SQS message deleted",
        "message_id": message_id
    }, ensure_ascii=False))


def main():
    print("=== ECS SQS Worker Start ===")
    print(json.dumps({
        "ts": now(),
        "aws_region": AWS_REGION,
        "queue_url": QUEUE_URL,
        "wait_time_seconds": WAIT_TIME_SECONDS,
        "max_number_of_messages": MAX_NUMBER_OF_MESSAGES,
        "visibility_timeout": VISIBILITY_TIMEOUT
    }, ensure_ascii=False))

    while True:
        try:
            messages = receive_messages()

            if not messages:
                print(json.dumps({
                    "ts": now(),
                    "status": "ok",
                    "message": "No messages"
                }, ensure_ascii=False))
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            for message in messages:
                process_message(message)

        except Exception as e:
            print(json.dumps({
                "ts": now(),
                "status": "ng",
                "error": str(e)
            }, ensure_ascii=False))
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({
            "status": "ng",
            "fatal_error": str(e)
        }, ensure_ascii=False))
        sys.exit(1)