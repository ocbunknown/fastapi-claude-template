import uuid_utils.compat as uuid

from src.application.common.events import StreamEvent, rebuild_stream_event


@rebuild_stream_event(subject_namespace="user.registered", stream="user_events")
class UserRegistered(StreamEvent):
    user_uuid: uuid.UUID
    login: str
