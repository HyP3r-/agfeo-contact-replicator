import random
from typing import Tuple

import requests
import urllib3
import vobject.vcard

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Agfeo:
    """
    Wrapper for Agfeo PBX
    """

    def __init__(self, config):
        self.config = config
        self.cookies = None

    def login(self) -> bool:
        """
        Login into PBX
        """

        response = requests.post(f"https://{self.config['hostname']}/tkset/login",
                                 json={"data": {"login": self.config["username"], "password": self.config["password"],
                                                "client": "web"}},
                                 verify=False)
        if response.status_code != 200 or response.json()["data"]["status"] != "Login Ok":
            return False

        self.cookies = response.cookies

        return True

    def contact_get_size(self) -> Tuple[bool, int]:
        """
        Get size of the contact store
        """

        response = requests.post(f"https://{self.config['hostname']}/tkset/pim",
                                 json={"id": self.agfeo_random(), "type": 8, "offset": 0, "size": 0, "data": ""},
                                 cookies=self.cookies, verify=False)
        if response.status_code != 200:
            return False, 0
        return True, int(response.json()["size"])

    def contacts_get(self, offset=0, size=100) -> Tuple[bool, list]:
        """
        Get list of contacts
        """

        response = requests.post(f"https://{self.config['hostname']}/tkset/pim",
                                 json={"id": self.agfeo_random(), "type": 8, "offset": offset, "size": size,
                                       "data": ""},
                                 cookies=self.cookies, verify=False)
        if response.status_code != 200:
            return False, []
        return True, list(response.json()["contacts"])

    def contact_set(self, contact: dict) -> Tuple[bool, dict]:
        """
        Update or Insert a contact into the pbx
        """

        response = requests.post(f"https://{self.config['hostname']}/tkset/pim",
                                 json={"id": self.agfeo_random(), "type": 5, "offset": 0, "size": 1, "data": contact},
                                 cookies=self.cookies, verify=False)
        if response.status_code != 200:
            return False, {}
        return True, response.json()["contact"]

    def contact_delete(self, contact_uid: str) -> bool:
        """
        Delete contact
        """

        response = requests.post(f"https://{self.config['hostname']}/tkset/pim",
                                 json={"id": self.agfeo_random(), "type": 6, "data": contact_uid},
                                 cookies=self.cookies, verify=False)
        return response.status_code == 200 and response.json()["ok"]

    @staticmethod
    def agfeo_random() -> int:
        """
        Generate Random Number for Requests
        """

        return int(1 + random.random() * 0x10000)

    @staticmethod
    def vcard_to_data(contact_input: vobject.base.Component, contact_current: dict = None) -> dict:
        """
        Convert vcard to agfeo contact (and merge it into current contact)
        """

        def _safe_access(fn):
            try:
                return fn()
            except:
                return None

        contact_output = contact_current if contact_current else {}

        # write default fields like company, firstname and lastname
        contact_output["company"] = _safe_access(lambda: contact_input.org.value[0]) or ""
        contact_output["firstname"] = _safe_access(lambda: contact_input.n.value.given) or ""
        contact_output["lastname"] = _safe_access(lambda: contact_input.n.value.family) or ""
        contact_output["numbers"] = []

        lookup_type = {"WORK": 1, "CELL": 2, "HOME": 1, "PREF": 1, "VOICE": 1}
        lookup_kind = {"WORK": 1, "CELL": 1, "HOME": 2, "PREF": 1, "VOICE": 2}

        for contact_input_tel in contact_input.contents.get("tel", []):
            # ignore if tel has no number
            if not contact_input_tel.value:
                continue

            if (not _safe_access(lambda: lookup_type.get(contact_input_tel.params["TYPE"][0])) or
                    not _safe_access(lambda: lookup_kind.get(contact_input_tel.params["TYPE"][0]))):
                continue

            contact_output_number = {
                "type": _safe_access(lambda: lookup_type.get(contact_input_tel.params["TYPE"][0], 1)),
                "kind": _safe_access(lambda: lookup_kind.get(contact_input_tel.params["TYPE"][0], 1)),
                "number": contact_input_tel.value, "pbindex": -1
            }

            contact_output["numbers"].append(contact_output_number)

        return contact_output
