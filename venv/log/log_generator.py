import logging
import asyncio
import sys
from typing import Optional

logger = logging.getLogger("school_app_logger")
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = logging.FileHandler("logs.log", encoding="utf-8")
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

async def _async_save_log_to_db(level: str, message: str, ip_address: Optional[str] = None):
    try:
        from database.db import Logs, async_session
        async with async_session() as session:
            new_log = Logs(level=level.lower(), message=str(message)[:990], ip_address=ip_address or "System/Local")
            session.add(new_log)
            await session.commit()
    except Exception:
        pass

class LogResult:
    def __init__(self, task_or_coro=None):
        self._task = task_or_coro
    def __await__(self):
        if self._task:
            if asyncio.iscoroutine(self._task):
                return self._task.__await__()
            elif isinstance(self._task, asyncio.Task):
                return asyncio.shield(self._task).__await__()
        async def _dummy():
            pass
        return _dummy().__await__()

def create_log(level: str, message: str, ip_address: Optional[str] = None) -> LogResult:
    lvl = str(level).lower()
    if lvl == "debug":
        logger.debug(message)
    elif lvl == "info":
        logger.info(message)
    elif lvl == "warning":
        logger.warning(message)
    elif lvl == "error":
        logger.error(message)
    elif lvl == "critical":
        logger.critical(message)
    else:
        logger.info(f"[{lvl.upper()}] {message}")
    task_or_coro = None
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            task_or_coro = loop.create_task(_async_save_log_to_db(lvl, message, ip_address))
    except RuntimeError:
        pass
    return LogResult(task_or_coro)
