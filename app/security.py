from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time


def hash_password(password:str,iterations:int=310_000)->str:
    salt=secrets.token_hex(16)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),iterations)
    return f"pbkdf2_sha256:{iterations}:{salt}:{digest.hex()}"


def verify_password(password:str,encoded:str)->bool:
    try:
        algorithm,iterations,salt,expected=encoded.split(":",3)
        if algorithm!="pbkdf2_sha256": return False
        actual=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt),int(iterations)).hex()
        return hmac.compare_digest(actual,expected)
    except (ValueError,TypeError): return False


def _b64(value:bytes)->str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _unb64(value:str)->bytes:
    return base64.urlsafe_b64decode(value+"="*(-len(value)%4))


def create_session(username:str,secret:str,hours:int,session_version:int=1)->tuple[str,str]:
    csrf=secrets.token_urlsafe(24)
    payload=_b64(json.dumps({"sub":username,"exp":int(time.time()+hours*3600),"csrf":csrf,"sv":session_version},separators=(",",":"),sort_keys=True).encode())
    signature=_b64(hmac.new(secret.encode(),payload.encode(),hashlib.sha256).digest())
    return f"{payload}.{signature}",csrf


def read_session(token:str|None,secret:str)->dict|None:
    if not token or not secret:return None
    try:
        payload,signature=token.split(".",1)
        expected=_b64(hmac.new(secret.encode(),payload.encode(),hashlib.sha256).digest())
        if not hmac.compare_digest(signature,expected):return None
        data=json.loads(_unb64(payload))
        return data if int(data["exp"])>=time.time() else None
    except (ValueError,KeyError,json.JSONDecodeError):return None
