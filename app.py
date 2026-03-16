import os
import json
import socket
import sys
from datetime import datetime

AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-1")

HSM_HOST = os.getenv("HSM_HOST")
HSM_PORT = int(os.getenv("HSM_PORT", "2223"))
CONNECT_TIMEOUT = int(os.getenv("CONNECT_TIMEOUT", "5"))

# Pipe から渡したい値があればここで受ける
PAYLOAD_JSON = os.getenv("PAYLOAD_JSON", "")


def load_payload():
    if not PAYLOAD_JSON:
        return {}
    try:
        return json.loads(PAYLOAD_JSON)
    except Exception as e:
        raise RuntimeError(f"PAYLOAD_JSON parse error: {e}")


def check_hsm_connectivity(host: str, port: int, timeout_sec: int):
    with socket.create_connection((host, port), timeout=timeout_sec):
        return True


def main():
    if not HSM_HOST:
        raise RuntimeError("Missing env: HSM_HOST")

    payload = load_payload()

    request_id = payload.get("request_id", "no-request-id")
    action = payload.get("action", "no-action")
    source = payload.get("source", "unknown")

    print("=== ECS HSM Worker Start ===")
    print(json.dumps({
        "ts": datetime.utcnow().isoformat() + "Z",
        "aws_region": AWS_REGION,
        "request_id": request_id,
        "action": action,
        "source": source,
        "hsm_host": HSM_HOST,
        "hsm_port": HSM_PORT
    }, ensure_ascii=False))

    check_hsm_connectivity(HSM_HOST, HSM_PORT, CONNECT_TIMEOUT)

    print(json.dumps({
        "status": "ok",
        "message": "HSM connection succeeded",
        "request_id": request_id,
        "hsm_host": HSM_HOST,
        "hsm_port": HSM_PORT
    }, ensure_ascii=False))

    print("=== ECS HSM Worker End ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({
            "status": "ng",
            "error": str(e)
        }, ensure_ascii=False))
        sys.exit(1)