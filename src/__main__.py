from contextlib import suppress

from src.api.server import serve
from src.api.v1.setup import init_app_v1
from src.settings.core import load_settings

settings = load_settings()
app = init_app_v1(settings)


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        serve(settings=settings)
