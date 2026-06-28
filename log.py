import logging
from pathlib import Path


def setup_logger(log_filename=Path("messages.log"), lvl="info", reinitialize=False):
    log = logging.getLogger(__name__)

    if log_filename.exists() and reinitialize:
        log_filename.unlink()

    match lvl.upper():
        case "DEBUG":
            log.setLevel(logging.DEBUG)
        case "INFO":
            log.setLevel(logging.INFO)
        case "WARNING":
            log.setLevel(logging.WARNING)
        case "ERROR":
            log.setLevel(logging.ERROR)
        case "CRITICAL":
            log.setLevel(logging.CRITICAL)

    formatter = logging.Formatter(
        fmt="[%(asctime)s %(levelname)s] %(message)s", datefmt="%d-%m-%Y %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)

    log.propagate = False
    log.debug("Logger initialized!")
    return log
