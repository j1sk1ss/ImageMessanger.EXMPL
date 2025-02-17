import hmac
import hashlib
import base64
import os

from common.configuration import conf


temp_keys_list: list = []


def _load_keys() -> set:
    try:
        with open(conf.PASSWORDS_FILE, "r") as f:
            return set(line.strip() for line in f.readlines())
    except FileNotFoundError:
        return set()
    

def add_key(username: str, password: str) -> bool:
    keys = set()
    if os.path.exists(conf.PASSWORDS_FILE):
        with open(conf.PASSWORDS_FILE, "r") as f:
            keys = set(line.strip() for line in f if line.strip())

    new_entry = f"{username}:{password}"
    if new_entry in keys:
        return False

    keys.add(new_entry)
    with open(conf.PASSWORDS_FILE, "w") as f:
        f.write("\n".join(keys) + "\n")

    return True


def verify_pass(username: str, password: str) -> tuple:
    passwords: set[str] = _load_keys()
    for pswd in passwords:
        if password == pswd.split(":")[0] and username == pswd.split(":")[1]:
            return pswd.split(":", 2)
    
    return None, None


def generate_access_key(username: str, userpass: str) -> str:
    data = f"{username}:{userpass}".encode()
    key = hmac.new("сщквуддЫфде".encode(), data, hashlib.sha256).digest()
    access_key = base64.urlsafe_b64encode(key).decode()
    temp_keys_list.append(access_key)
    return access_key


def verify_access_key(key: str) -> bool:
    return key in temp_keys_list
