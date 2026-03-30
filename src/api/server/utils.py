import multiprocessing as mp


def workers_count() -> int:
    return mp.cpu_count() - 1
