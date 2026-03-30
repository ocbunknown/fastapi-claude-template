import random
import string
from typing import Final

DEFAULT_LENGTH: Final[int] = 12


def generate_password(length: int = DEFAULT_LENGTH) -> str:
    characters = string.ascii_letters + string.digits + string.punctuation
    password = "".join(random.choice(characters) for _ in range(length))

    return password
