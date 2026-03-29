import requests
from asn1crypto import x509
import base64
import hashlib

class ApiClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password

    def get_status(self):
        url = f"{self.base_url}/status"
        response = requests.get(url)
        return response.json()

    def request_otp(self):
        url = f"{self.base_url}/RequestOTP"
        payload = {"Username": self.username, "Password": self.password}

        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()

        outcome = result.get("Outcome")

        if outcome == 0:
            return "Το OTP στάλθηκε επιτυχώς."
        elif outcome == 1:
            raise Exception(
                "Ο λογαριασμός αυτός δεν χρησιμοποιεί το email ως μέθοδο αποστολής OTP: "
                + result.get("Description")
            )
        elif outcome == 9:
            raise Exception("An error occurred: " + result.get("Description"))

        raise Exception("An error occurred: " + result.get("Description"))

    def get_certificates(self):
        url = f"{self.base_url}/Certificates"

        payload = {"Username": self.username, "Password": self.password}

        response = requests.post(url, json=payload)
        response.raise_for_status()

        result = response.json()

        if result.get("Success") == False:
            raise Exception("Certificate retrieval failed")

        certs = []

        for cert_b64 in result["Certificates"]:
            cert_der = base64.b64decode(cert_b64)
            cert = x509.Certificate.load(cert_der)
            certs.append(cert)

        return certs

    def sign(self, buffer, otp):
        url = f"{self.base_url}/SignBuffer"

        hash_base64 = []

        for data in buffer:
            digest = hashlib.sha256(data).digest()

            if len(digest) != 32:
                raise ValueError("Invalid SHA256 length")

            hash_base64.append(base64.b64encode(digest).decode())

        payload = {
            "Username": self.username,
            "Password": self.password,
            "SignPassword": otp,
            "BufferToSign": hash_base64,
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        result = response.json()

        if not result.get("Success"):
            raise Exception("Αποτυχία δημιουργίας ψηφιακής υπογραφής!")

        signatures = result["Data"]["Signature"]

        if type(signatures) is not list:
            signatures = [signatures]

        signatures_b64 = [base64.b64decode(signature) for signature in signatures]

        return signatures_b64
