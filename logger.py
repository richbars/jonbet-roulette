import logging


class AppLogger:
    _formatter = logging.Formatter(
        "%(levelname)-5s [%(threadName)s] %(name)s - %(message)s"
    )

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        logger = logging.getLogger(name)

        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(cls._formatter)
            logger.setLevel(logging.DEBUG)
            logger.addHandler(handler)
            logger.propagate = False

        return logger