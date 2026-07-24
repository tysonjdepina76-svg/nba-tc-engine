import logging

def setup_logging(name="tc_pipeline"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
    return logger

def get_logger(name="tc_pipeline"):
    return logging.getLogger(name)
