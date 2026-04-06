from typing import Any

import orjson as orjson

from src.presentation.http.common.serializers.default import _default, _predict_bytes


def orjson_dumps(value: Any) -> bytes:
    return _predict_bytes(value) or orjson.dumps(
        value,
        default=_default,
        option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY,
    )
