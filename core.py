import argparse
import json
from pathlib import Path

import pandas as pd
import requests
from requests import Response
from requests.auth import HTTPBasicAuth


def main(args):
    sender = SMSSender(args.device)

    db = pd.read_csv(args.messages)
    for _, s in db.iterrows():
        phone = s.phone.strip("'")
        msg = s.message
        _ = sender.send_sms(phone=phone, msg=msg)


class SMSSender:
    def __init__(self, device: Path, timeout=10) -> None:
        """ """
        if not device.exists():
            raise FileNotFoundError(device)

        d: dict = json.loads(device.read_text())
        self.local_adress = self.__get_record(d, "local_adress")
        self.username = self.__get_record(d, "username")
        self.password = self.__get_record(d, "password")
        self.header = {"Content-Type": "application/json"}
        self.timeout = timeout
        self.auth = HTTPBasicAuth(username=self.username, password=self.password)

    def send_sms(self, phone: str, msg: str) -> Response:
        url = f"http://{self.local_adress}/message"
        payload = {
            "textMessage": {
                "text": msg,
            },
            "phoneNumbers": [phone],
        }
        r = requests.post(
            url, json=payload, headers=self.header, auth=self.auth, timeout=self.timeout
        )
        return r

    @staticmethod
    def __get_record(d: dict, key: str) -> str:
        val = d.get(key)
        if val is not None and val != "":
            return val

        raise ValueError(f"The '{key}' record is missing from device file")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--messages",
        type=Path,
        help="Fichier CSV qui contient à la fois les messages et les numéros visés.",
    )
    parser.add_argument("--device", type=Path, default=Path("device.json"))
    args = parser.parse_args()
    main(args)
