class ProxyError(Exception):
    pass


class ProxyPoolEmptyError(ProxyError):
    def __init__(self, message: str = "Proxy pool is empty") -> None:
        super().__init__(message)


class ProxyPoolFullError(ProxyError):
    def __init__(self, message: str = "Proxy pool is full") -> None:
        super().__init__(message)
