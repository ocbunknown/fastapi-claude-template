from typing import Any

from src.settings.core import Settings

from .granian import run_api_granian


def serve(settings: Settings, suffix: str = "app", **kwargs: Any) -> None:
    match settings.server.type:
        case "granian":
            run_api_granian(f"src.__main__:{suffix}", settings.server, **kwargs)
        case _:
            raise ValueError(
                f"Unsupported server type: '{settings.server.type}'. "
                "Currently only 'granian' server type is supported. "
                "Please update your server configuration to use 'granian'."
            )
