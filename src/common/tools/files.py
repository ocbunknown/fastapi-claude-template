from typing import Any, Literal

ModeType = Literal[
    "r",
    "w",
    "a",
    "rb",
    "wb",
    "ab",
    "r+",
    "w+",
    "a+",
    "rb+",
    "wb+",
    "ab+",
]


def open_file_sync(path: str, mode: ModeType) -> Any:
    if mode not in {
        "r",
        "w",
        "a",
        "rb",
        "wb",
        "ab",
        "r+",
        "w+",
        "a+",
        "rb+",
        "wb+",
        "ab+",
    }:
        raise ValueError(f"Invalid mode '{mode}'. Must be a valid file access mode.")

    try:
        with open(path, mode) as file:
            if "r" in mode:
                return file.read()
            return
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: {path}") from e
    except OSError as e:
        raise OSError(f"Error accessing file {path}: {e}") from e
