import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests
from requests import HTTPError
from requests.auth import HTTPBasicAuth


def main(args):
    sender = SMSSender(args.device)

    db = pd.read_csv(args.messages)
    for _, s in db.iterrows():
        phone = s.phone.strip("'")
        msg = s.message
        is_sucess, state = sender.send_and_wait(phone=phone, msg=msg)


class SMSSender:
    FINAL_STATES = {"Delivered", "Failed"}

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

    def send_sms(self, phone: str, msg: str, with_delivery_report=True) -> dict:
        url = f"http://{self.local_adress}/message"
        payload = {
            "textMessage": {
                "text": msg,
            },
            "phoneNumbers": [phone],
            "withDeliveryReport": with_delivery_report,
        }
        r = requests.post(
            url, json=payload, headers=self.header, auth=self.auth, timeout=self.timeout
        )
        r.raise_for_status()  # Raises HTTPError, if one occurred.
        return r.json()

    def send_and_wait(
        self, phone: str, msg: str, **kwargs
    ) -> tuple[bool, str] | list[tuple[bool, str]]:
        """
        Envoie un SMS et attend le statut final.
        Retourne (succès: bool, état: str).
        """
        response = self.send_sms(phone, msg, with_delivery_report=True)

        # La réponse contient une liste de messages (un par numéro)
        messages = response if isinstance(response, list) else [response]

        results = []
        for message in messages:
            msg_id = message.get("id")
            if not msg_id:
                results.append((False, "NoId"))
                continue
            final_state = self.wait_for_status(msg_id, **kwargs)
            results.append((final_state == "Delivered", final_state))

        # Si un seul destinataire, retourne directement le résultat
        if len(results) == 1:
            return results[0]
        return results

    def get_status(self, message_id: str) -> dict:
        """Récupère le statut d'un message par son id."""
        url = f"http://{self.local_adress}/message/{message_id}"
        r = requests.get(url, headers=self.header, auth=self.auth, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def wait_for_status(
        self, message_id: str, poll_interval: float = 2.0, max_wait: float = 20.0
    ) -> str:
        """
        Poll jusqu'à obtenir un état final (Delivered ou Failed).
        Retourne l'état final sous forme de string.
        """
        elapsed = 0.0
        while elapsed < max_wait:
            data = self.get_status(message_id)
            state = data.get("state", "Unknown")
            if state in self.FINAL_STATES:
                return state
            time.sleep(poll_interval)
            elapsed += poll_interval
        return "Timeout"

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
