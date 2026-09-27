"""归档子进程的完整生命周期：启动、输出、等待、停止和回收。"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from collections.abc import Callable, Sequence
from pathlib import Path

from core.cancellation import Cancellation


def run_command(
    command: Sequence[str],
    *,
    cancellation: Cancellation,
    cwd: Path | None = None,
    output_cb: Callable[[str], None] | None = None,
    capture_output: bool = False,
    hide_console: bool = False,
) -> int:
    """执行命令并返回退出码；异常或取消时回收进程、输出线程和管道。"""
    cancellation.check()
    capture = capture_output or output_cb is not None
    flags = (
        getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if hide_console and sys.platform == "win32" else 0
    )
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT,
        creationflags=flags,
    )
    reader: threading.Thread | None = None
    try:
        if process.stdout is not None:
            stream = process.stdout
            chunks: queue.Queue[bytes | OSError | None] = queue.Queue()

            def read_stdout() -> None:
                try:
                    while chunk := os.read(stream.fileno(), 4096):
                        chunks.put(chunk)
                except OSError as error:
                    chunks.put(error)
                finally:
                    chunks.put(None)

            reader = threading.Thread(target=read_stdout, daemon=True)
            reader.start()
            _pump_output(chunks, cancellation, output_cb)
        while True:
            cancellation.check()
            try:
                return process.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                continue
    finally:
        _terminate_process(process)
        if reader is not None and reader.ident is not None:
            reader.join()
        if process.stdout is not None:
            process.stdout.close()


def _pump_output(
    chunks: queue.Queue[bytes | OSError | None],
    cancellation: Cancellation,
    output_cb: Callable[[str], None] | None,
) -> None:
    """消费读取线程的输出；等待输出期间每 0.1 秒检查停止请求。"""
    pending = bytearray()
    scan_from = 0
    while True:
        cancellation.check()
        try:
            chunk = chunks.get(timeout=0.1)
        except queue.Empty:
            continue
        if isinstance(chunk, OSError):
            raise chunk
        if chunk is None:
            break
        if output_cb is None:
            continue
        pending.extend(chunk)
        while True:
            separator = next(
                (index for index in range(scan_from, len(pending)) if pending[index] in (10, 13)),
                -1,
            )
            if separator < 0:
                scan_from = len(pending)
                break
            line = bytes(pending[:separator]).decode("utf-8", "replace").strip()
            del pending[:separator + 1]
            scan_from = 0
            if line:
                output_cb(line)
    leftover = bytes(pending).decode("utf-8", "replace").strip()
    if leftover and output_cb is not None:
        output_cb(leftover)


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    """终止仍在运行的工具并等待退出，超时后强制结束。"""
    if process.poll() is None:
        try:
            process.terminate()
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
