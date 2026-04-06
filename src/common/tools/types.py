def is_typevar[T](t: T) -> bool:
    return hasattr(t, "__bound__") or hasattr(t, "__constraints__")
