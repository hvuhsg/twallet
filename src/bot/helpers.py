from hashlib import sha256
from secrets import token_urlsafe


def create_password_hash(password: str):
    salt = token_urlsafe(16)
    hs = sha256((password+salt).encode()).hexdigest()
    return hs, salt


def is_password_valid(password: str, hs: str, salt: str) -> bool:
    return sha256((password+salt).encode()).hexdigest() == hs
