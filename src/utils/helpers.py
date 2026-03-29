import sys
from pathlib import Path
import json
import keyring


def get_documents_from_folder(folder_path, extensions):
    path = Path(folder_path)
    document_list = []

    if not path.exists() or not path.is_dir():
        return []

    for file in path.rglob("*"):
        if file.is_file() and file.suffix.lower() in extensions:
            document_list.append(str(file.resolve()))

    return document_list


def get_base_path():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent.parent
    else:
        return Path(__file__).resolve().parent.parent


def save_password(service_name, username, password):
    saved = load_password(service_name, username)
    if (not saved) or (saved != password):
        keyring.set_password(service_name, username, password)


def load_password(service_name, username):
    return keyring.get_password(service_name, username)


def load_config(path="config.json"):

    base_path = get_base_path()

    with open(base_path / path, "r") as f:
        config = json.load(f)

    cert_path: Path = base_path / config["security"]["tss_cert_file"]
    cert_path = cert_path.resolve()
    config["security"]["tss_cert_file"] = str(cert_path)

    _validate_config(config)

    return config


def _validate_config(config):
    assert "api" in config
    assert "base_url" in config["api"]
    assert "tsa_url" in config["api"]
    assert Path(config["security"]["tss_cert_file"]).exists()
