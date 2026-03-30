from src.api.common.dto.base import DTO


class Fingerprint(DTO):
    fingerprint: str


class Login(Fingerprint):
    login: str
    password: str


class Register(Fingerprint):
    login: str
    password: str


class VerificationCode(DTO):
    code: str
