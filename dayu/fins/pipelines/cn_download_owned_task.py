"""下载流程拥有资源的异步任务收口；重复取消也等待实际工作结束。"""

import asyncio
from threading import Event
from typing import TypeVar

_Result = TypeVar("_Result")


async def await_owned_task(task: asyncio.Task[_Result], stopped: Event | None = None) -> _Result:
    """等待资源所有者任务结束，再传播调用方取消和清理错误。

    参数：task 为拥有线程或进程资源的任务；stopped 为取消时通知工作线程的事件。
    返回：任务的真实结果。异常：调用方取消在资源结束后传播，工作错误作为其原因；未取消时原错透传。
    """
    cancellation: asyncio.CancelledError | None = None
    while True:
        try:
            result = await asyncio.shield(task)
            if cancellation is not None:
                raise cancellation
            return result
        except asyncio.CancelledError as exc:
            if cancellation is None:
                cancellation = exc
            if stopped is not None:
                stopped.set()
            if task.done():
                try:
                    task.result()
                except Exception as cleanup_error:
                    raise cancellation from cleanup_error
                raise cancellation
        except Exception as exc:
            if cancellation is not None:
                raise cancellation from exc
            raise
