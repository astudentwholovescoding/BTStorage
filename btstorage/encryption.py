import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def encode_data(data, password):
    password = password.encode()
    key = hashlib.sha256(password).digest()

    aesgcm = AESGCM(key)
    nonce = b"\x00"*12  

    encoded = aesgcm.encrypt(nonce, data, None)
    return encoded


def decode_data(data, password):
    password = password.encode()
    key = hashlib.sha256(password).digest()

    aesgcm = AESGCM(key)
    nonce = b"\x00"*12  

    decoded = aesgcm.decrypt(nonce, data, None)
    return decoded