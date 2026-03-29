import sys
import os
import json
import traceback
import asyncio
from core.converter import convert_doc_to_pdf, is_doc_file
from core.signer import Signer
from utils.helpers import load_config


def main():
    try:
        cleanup = False

        if len(sys.argv) != 2:
            raise Exception("Missing JSON input file")

        request_file = sys.argv[1]

        config = load_config()

        api_base_url = config["api"]["base_url"]
        tsa_url = config["api"]["tsa_url"]
        tss_cert_file = config["security"]["tss_cert_file"]

        with open(request_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        username = data["username"]
        password = data["password"]
        otp = data["otp"]
        file_list = data["files"]
        stamp_position = int(data["stamp_position"]) if "stamp_position" in data else 3

        number_of_files = len(file_list)
        cleanup = False

        signer = Signer(api_base_url, tsa_url, tss_cert_file, username, password)

        if number_of_files == 1:
            filename = file_list[0]
            if is_doc_file(filename):
                filename = convert_doc_to_pdf(filename)
                cleanup = True
            results = signer.sign_pdf(filename, stamp_position, otp)
            signed_file = results[0]

            if signed_file is not None:
                result = {"success": True, "signed_files": [signed_file]}
            else:
                result = {
                    "success": False,
                    "error": "Η Υπογραφή του εγγραφου απέτυχε λόγω ύπαρξης ενεργού περιεχομένου.",
                }
        else:
            results = asyncio.run(signer.sign_all_pdfs(file_list, stamp_position, otp))
            succes = [d[0] for d in results if d[0] is not None]

            if succes:
                result = {"success": True, "signed_files": succes}
            else:
                result = {
                    "success": False,
                    "error": "Η Υπογραφή όλων των εγγραφων απέτυχε λόγω ύπαρξης ενεργού περιεχομένου.",
                }

    except Exception as e:
        result = {"success": False, "error": str(e), "trace": traceback.format_exc()}

    if cleanup and os.path.exists(filename):
        os.remove(filename)

    result_file = request_file.replace(".json", "_result.json")

    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result, f)

    sys.exit(0)


if __name__ == "__main__":
    main()
