__all__ = ["LoggerNode"]

import dataclasses
import functools
import logging
import re
import traceback
from typing import Any, final

from magicnet.util.messenger import MessengerNode, StandardEvents


@dataclasses.dataclass
@final
class LoggerNode(MessengerNode[Any, Any]):
    """
    LoggerNode can be attached to a messenger tree to automatically log
    INFO, WARNING, ERROR and EXCEPTION through builtin logging module.
    It is not automatically enabled for compatibility with setups that
    are using different logging solutions, such as directNotify (in Panda3D).

    If multiple LoggerNodes are attached to the tree, the same event
    will be logged multiple times, so it is usually recommended to only attach one.
    """

    prefix: str = "magicnet.logging"
    initlogger: bool = True

    # This regex converts CamelCase to snake_case
    snake_case_regex = re.compile("((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))")

    def __camel_case(self, s: str) -> str:
        return self.snake_case_regex.sub(r"_\1", s).lower()

    def __post_init__(self):
        self.listen(StandardEvents.ERROR, functools.partial(self.log, logging.ERROR))
        self.listen(StandardEvents.WARNING, functools.partial(self.log, logging.WARNING))
        self.listen(StandardEvents.INFO, functools.partial(self.log, logging.INFO))
        self.listen(StandardEvents.DEBUG, functools.partial(self.log, logging.DEBUG))
        self.listen(StandardEvents.EXCEPTION, self.log_exc)

        if self.initlogger:
            console = logging.StreamHandler()
            console.setLevel(logging.INFO)
            formatter = logging.Formatter("%(name)-12s: %(levelname)-8s %(message)s")
            console.setFormatter(formatter)
            logger = logging.getLogger(self.prefix)
            logger.setLevel(logging.INFO)
            logger.addHandler(console)

    def log(self, level: int, data: str):
        if not self.listener.current_event:
            logger = logging.getLogger(self.prefix)
        else:
            sender = self.__camel_case(self.listener.current_event.sender.__class__.__name__)
            logger = logging.getLogger(f"{self.prefix}.{sender}")
        logger.log(level, data)

    def log_exc(self, name: str, exc: BaseException):
        self.log(logging.ERROR, f"Exception raised: {name}")
        traceback.print_exception(exc)
