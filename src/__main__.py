from contextlib import suppress

from src.entrypoints.http import run, settings

if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        run(settings)
