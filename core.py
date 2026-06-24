import json
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

PHONE = ""
MSG = "Coucou depuis mon script Python !"


def main():
    # Load device
    device = Path("device.json")
    device = json.loads(device.read_text())

    # Create request in expected format:
    header = {"Content-Type": "application/json"}
    payload = {
        "textMessage": {
            "text": MSG,
        },
        "phoneNumbers": [PHONE],
    }

    # Actually send the request!
    r = requests.post(
        f"http://{device.get('local_adress')}/message",
        json=payload,
        headers=header,
        auth=HTTPBasicAuth(
            username=device.get("username"), password=device.get("password")
        ),
        timeout=10,
    )

    # Display the status:
    print(r.status_code)
    print(r.text)


if __name__ == "__main__":
    main()
