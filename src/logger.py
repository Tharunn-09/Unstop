import logging
import sys
import io

def setup_logger(name: str = "UnstopPOTD") -> logging.Logger:
    """Configures and returns a structured, clear console logger with UTF-8 support."""
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)
    
    # Wrap stdout with utf-8 error handler if needed for Windows console compatibility
    stream = sys.stdout
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            pass

    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

log = setup_logger()
