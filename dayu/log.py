"""``dayu.log`` 兼容层 —— 仅供从 dayu-agent 移植过来的 pypdf 降级链路使用。

背景
----
dayu-agent 有一个 ``dayu/log.py``，对外暴露 ``Log`` 门面
（``Log.info(msg, module=...)`` / ``Log.warning(msg, module=...)``）。
dayu-agent-r **没有**这个模块：它用的是 ``dayu/runtime/log.py``，
API 完全不同（``configure`` / ``log_verbose`` / ``LogLevel`` / 诊断流），
其中并不存在 ``Log`` 类。

为了让两个移植文件（``dayu/docling_fallback.py`` 与
``dayu/fins/pipelines/pypdf_converter.py``）保持与 dayu-agent 原版**逐字一致**
（便于日后跟上上游改动、减少冲突），这里补一个最小兼容面，
而不是去改那两份文件里的 import。

它们实际只用到：

* ``Log.info(message, module=...)``
* ``Log.warning(message, module=...)``

映射到标准库 ``logging``，logger 名形如 ``dayu.<module>``，
与 ``dayu/runtime/log.py`` 的命名习惯保持一致。
"""

from __future__ import annotations

import logging
from typing import Any

_ROOT_LOGGER_NAME = "dayu"


def _logger_for(module: str | None) -> logging.Logger:
    """把调用方传入的模块标签（如 ``FINS.DOCLING_FALLBACK``）转成 logger。"""
    if not module:
        return logging.getLogger(_ROOT_LOGGER_NAME)
    slug = str(module).strip().lower().replace(".", "_").replace("-", "_")
    if not slug:
        return logging.getLogger(_ROOT_LOGGER_NAME)
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{slug}")


def _emit(level: int, message: Any, module: str | None) -> None:
    logger = _logger_for(module)
    if not logger.isEnabledFor(level):
        return
    logger.log(level, "%s", message)


class Log:
    """``dayu-agent`` 的 ``Log`` 门面的最小兼容实现（仅 info/warning 等）。"""

    @staticmethod
    def debug(message: Any, *, module: str | None = None, **_: Any) -> None:
        _emit(logging.DEBUG, message, module)

    @staticmethod
    def info(message: Any, *, module: str | None = None, **_: Any) -> None:
        _emit(logging.INFO, message, module)

    @staticmethod
    def warning(message: Any, *, module: str | None = None, **_: Any) -> None:
        _emit(logging.WARNING, message, module)

    @staticmethod
    def error(message: Any, *, module: str | None = None, **_: Any) -> None:
        _emit(logging.ERROR, message, module)

    @staticmethod
    def exception(message: Any, *, module: str | None = None, **_: Any) -> None:
        _emit(logging.ERROR, message, module)


__all__ = ["Log"]
