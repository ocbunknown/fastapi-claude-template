import base64
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class AESCipher:
    def __init__(self, key: str) -> None:
        self._key = self._decode_key(key)

    def encrypt(self, plaintext: str) -> bytes:
        iv = os.urandom(16)

        cipher = Cipher(
            algorithms.AES(self._key), modes.CBC(iv), backend=default_backend()
        )
        encryptor = cipher.encryptor()

        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(plaintext.encode()) + padder.finalize()

        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        return iv + ciphertext

    def decrypt(self, ciphertext: bytes) -> str:
        iv = ciphertext[:16]
        actual_ciphertext = ciphertext[16:]

        cipher = Cipher(
            algorithms.AES(self._key), modes.CBC(iv), backend=default_backend()
        )
        decryptor = cipher.decryptor()

        padded_plaintext = decryptor.update(actual_ciphertext) + decryptor.finalize()

        unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()

        return plaintext.decode()

    def _decode_key(self, encoded_key: str) -> bytes:
        return base64.b64decode(encoded_key)
