import asyncio
import atexit
import datetime
import hashlib
import hmac
import json
import os
import pickle
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from enum import Enum, IntEnum, auto
from functools import lru_cache, partial, wraps
from pathlib import Path
from queue import Empty, PriorityQueue, Queue
from typing import (
    Any, AsyncGenerator, Awaitable, Callable, Coroutine, Dict, Generator,
    Generic, List, Literal, Optional, Protocol, Set, Tuple, Type, TypeVar, Union
)

import zmq
import zmq.asyncio
from jupyter_client import AsyncKernelClient, AsyncKernelManager, KernelManager
from jupyter_client.session import Session
from jupyter_client.connect import ConnectionFileMixin


T = TypeVar('T')
R = TypeVar('R')


class MessageType(str, Enum):
    EXECUTE_REQUEST = 'execute_request'
    EXECUTE_REPLY = 'execute_reply'
    EXECUTE_INPUT = 'execute_input'
    EXECUTE_RESULT = 'execute_result'
    STREAM = 'stream'
    DISPLAY_DATA = 'display_data'
    UPDATE_DISPLAY_DATA = 'update_display_data'
    ERROR = 'error'
    STATUS = 'status'
    CLEAR_OUTPUT = 'clear_output'
    COMPLETE_REQUEST = 'complete_request'
    COMPLETE_REPLY = 'complete_reply'
    INSPECT_REQUEST = 'inspect_request'
    INSPECT_REPLY = 'inspect_reply'
    HISTORY_REQUEST = 'history_request'
    HISTORY_REPLY = 'history_reply'
    IS_COMPLETE_REQUEST = 'is_complete_request'
    IS_COMPLETE_REPLY = 'is_complete_reply'
    KERNEL_INFO_REQUEST = 'kernel_info_request'
    KERNEL_INFO_REPLY = 'kernel_info_reply'
    SHUTDOWN_REQUEST = 'shutdown_request'
    SHUTDOWN_REPLY = 'shutdown_reply'
    INTERRUPT_REQUEST = 'interrupt_request'
    INTERRUPT_REPLY = 'interrupt_reply'
    DEBUG_REQUEST = 'debug_request'
    DEBUG_REPLY = 'debug_reply'
    INPUT_REQUEST = 'input_request'
    INPUT_REPLY = 'input_reply'
    COMM_OPEN = 'comm_open'
    COMM_MSG = 'comm_msg'
    COMM_CLOSE = 'comm_close'
    COMM_INFO_REQUEST = 'comm_info_request'
    COMM_INFO_REPLY = 'comm_info_reply'


class KernelStatus(Enum):
    STARTING = 'starting'
    IDLE = 'idle'
    BUSY = 'busy'
    RESTARTING = 'restarting'
    AUTORESTARTING = 'autorestarting'
    DEAD = 'dead'
    UNKNOWN = 'unknown'


class CodeCompleteness(Enum):
    COMPLETE = 'complete'
    INCOMPLETE = 'incomplete'
    INVALID = 'invalid'
    UNKNOWN = 'unknown'


@dataclass
class WireMessage:
    header: Dict[str, Any]
    parent_header: Dict[str, Any]
    metadata: Dict[str, Any]
    content: Dict[str, Any]
    buffers: List[bytes] = field(default_factory=list)
    
    @property
    def msg_id(self) -> str:
        return self.header.get('msg_id', '')
    
    @property
    def msg_type(self) -> str:
        return self.header.get('msg_type', '')
    
    @property
    def session(self) -> str:
        return self.header.get('session', '')


@dataclass
class ExecutionContext:
    code: str
    msg_id: str
    silent: bool = False
    store_history: bool = True
    user_expressions: Dict[str, str] = field(default_factory=dict)
    allow_stdin: bool = False
    stop_on_error: bool = True
    timeout: Optional[float] = None
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = 'pending'
    execution_count: Optional[int] = None
    error: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    
    def add_output(self, output: Dict[str, Any]) -> None:
        self.outputs.append(output)


class ChannelSocket(ABC):
    def __init__(self, context: zmq.asyncio.Context, address: str, socket_type: int):
        self._context = context
        self._address = address
        self._socket: Optional[zmq.asyncio.Socket] = None
        self._socket_type = socket_type
        self._lock = asyncio.Lock()
        self._connected = False
    
    async def connect(self) -> None:
        async with self._lock:
            if self._connected:
                return
            self._socket = self._context.socket(self._socket_type)
            self._socket.connect(self._address)
            self._connected = True
    
    async def disconnect(self) -> None:
        async with self._lock:
            if self._socket:
                self._socket.close()
                self._socket = None
            self._connected = False
    
    @abstractmethod
    async def send(self, msg: WireMessage) -> None: ...
    
    @abstractmethod
    async def recv(self) -> WireMessage: ...


class DealerChannel(ChannelSocket):
    def __init__(self, context: zmq.asyncio.Context, address: str, session: 'JupyterSession'):
        super().__init__(context, address, zmq.DEALER)
        self._session = session
    
    async def send(self, msg: WireMessage) -> None:
        frames = self._session.serialize(msg)
        await self._socket.send_multipart(frames)
    
    async def recv(self) -> WireMessage:
        frames = await self._socket.recv_multipart()
        return self._session.deserialize(frames)


class SubChannel(ChannelSocket):
    def __init__(self, context: zmq.asyncio.Context, address: str, session: 'JupyterSession'):
        super().__init__(context, address, zmq.SUB)
        self._session = session
    
    async def connect(self) -> None:
        await super().connect()
        self._socket.setsockopt(zmq.SUBSCRIBE, b'')
    
    async def send(self, msg: WireMessage) -> None:
        raise NotImplementedError("SUB sockets cannot send")
    
    async def recv(self) -> WireMessage:
        frames = await self._socket.recv_multipart()
        return self._session.deserialize(frames)


class JupyterSession:
    DELIM = b'<IDS|MSG>'
    
    def __init__(self, key: bytes = b'', session_id: Optional[str] = None):
        self._key = key
        self._session_id = session_id or uuid.uuid4().hex
        self._msg_count = 0
        self._lock = threading.Lock()
    
    def _make_header(self, msg_type: str) -> Dict[str, Any]:
        with self._lock:
            self._msg_count += 1
            msg_id = f'{self._session_id}_{self._msg_count}'
        return {
            'msg_id': msg_id,
            'msg_type': msg_type,
            'username': os.environ.get('USER', 'anonymous'),
            'session': self._session_id,
            'date': datetime.datetime.utcnow().isoformat() + 'Z',
            'version': '5.3'
        }
    
    def create_message(
        self,
        msg_type: str,
        content: Dict[str, Any],
        parent: Optional[WireMessage] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WireMessage:
        return WireMessage(
            header=self._make_header(msg_type),
            parent_header=parent.header if parent else {},
            metadata=metadata or {},
            content=content
        )
    
    def _sign(self, frames: List[bytes]) -> bytes:
        if not self._key:
            return b''
        h = hmac.new(self._key, digestmod=hashlib.sha256)
        for frame in frames:
            h.update(frame)
        return h.hexdigest().encode('ascii')
    
    def serialize(self, msg: WireMessage) -> List[bytes]:
        frames = [
            json.dumps(msg.header).encode('utf-8'),
            json.dumps(msg.parent_header).encode('utf-8'),
            json.dumps(msg.metadata).encode('utf-8'),
            json.dumps(msg.content).encode('utf-8')
        ]
        signature = self._sign(frames)
        return [b'', self.DELIM, signature] + frames + msg.buffers
    
    def deserialize(self, frames: List[bytes]) -> WireMessage:
        idx = frames.index(self.DELIM)
        idents = frames[:idx]
        signature = frames[idx + 1]
        msg_frames = frames[idx + 2:idx + 6]
        buffers = frames[idx + 6:] if len(frames) > idx + 6 else []
        
        if self._key:
            expected = self._sign(msg_frames)
            if not hmac.compare_digest(signature, expected):
                raise ValueError("Invalid message signature")
        
        return WireMessage(
            header=json.loads(msg_frames[0]),
            parent_header=json.loads(msg_frames[1]),
            metadata=json.loads(msg_frames[2]),
            content=json.loads(msg_frames[3]),
            buffers=buffers
        )


class MessageRouter:
    def __init__(self):
        self._handlers: Dict[str, List[Callable[[WireMessage], Awaitable[None]]]] = {}
        self._pending: Dict[str, asyncio.Future[WireMessage]] = {}
        self._lock = asyncio.Lock()
    
    def register(self, msg_type: str, handler: Callable[[WireMessage], Awaitable[None]]) -> Callable[[], None]:
        if msg_type not in self._handlers:
            self._handlers[msg_type] = []
        self._handlers[msg_type].append(handler)
        return lambda: self._handlers[msg_type].remove(handler)
    
    async def route(self, msg: WireMessage) -> None:
        msg_type = msg.msg_type
        parent_id = msg.parent_header.get('msg_id', '')
        
        async with self._lock:
            if parent_id in self._pending:
                self._pending[parent_id].set_result(msg)
        
        for handler in self._handlers.get(msg_type, []):
            try:
                await handler(msg)
            except Exception:
                pass
        
        for handler in self._handlers.get('*', []):
            try:
                await handler(msg)
            except Exception:
                pass
    
    async def wait_for_reply(self, msg_id: str, timeout: Optional[float] = None) -> WireMessage:
        future: asyncio.Future[WireMessage] = asyncio.get_event_loop().create_future()
        async with self._lock:
            self._pending[msg_id] = future
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            async with self._lock:
                self._pending.pop(msg_id, None)


class OutputCollector:
    def __init__(self):
        self._outputs: Dict[str, List[Dict[str, Any]]] = {}
        self._execution_results: Dict[str, Dict[str, Any]] = {}
        self._errors: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def add_stream(self, parent_id: str, name: str, text: str) -> None:
        async with self._lock:
            if parent_id not in self._outputs:
                self._outputs[parent_id] = []
            outputs = self._outputs[parent_id]
            if outputs and outputs[-1].get('output_type') == 'stream' and outputs[-1].get('name') == name:
                outputs[-1]['text'] += text
            else:
                outputs.append({'output_type': 'stream', 'name': name, 'text': text})
    
    async def add_display_data(self, parent_id: str, data: Dict[str, Any], metadata: Dict[str, Any]) -> None:
        async with self._lock:
            if parent_id not in self._outputs:
                self._outputs[parent_id] = []
            self._outputs[parent_id].append({
                'output_type': 'display_data',
                'data': data,
                'metadata': metadata
            })
    
    async def add_execute_result(
        self, parent_id: str, execution_count: int, data: Dict[str, Any], metadata: Dict[str, Any]
    ) -> None:
        async with self._lock:
            if parent_id not in self._outputs:
                self._outputs[parent_id] = []
            self._outputs[parent_id].append({
                'output_type': 'execute_result',
                'execution_count': execution_count,
                'data': data,
                'metadata': metadata
            })
            self._execution_results[parent_id] = {
                'execution_count': execution_count,
                'data': data,
                'metadata': metadata
            }
    
    async def add_error(self, parent_id: str, ename: str, evalue: str, traceback: List[str]) -> None:
        async with self._lock:
            if parent_id not in self._outputs:
                self._outputs[parent_id] = []
            error = {'output_type': 'error', 'ename': ename, 'evalue': evalue, 'traceback': traceback}
            self._outputs[parent_id].append(error)
            self._errors[parent_id] = error
    
    async def get_outputs(self, parent_id: str) -> List[Dict[str, Any]]:
        async with self._lock:
            return list(self._outputs.get(parent_id, []))
    
    async def clear(self, parent_id: str) -> None:
        async with self._lock:
            self._outputs.pop(parent_id, None)
            self._execution_results.pop(parent_id, None)
            self._errors.pop(parent_id, None)


class KernelConnection:
    def __init__(self, connection_info: Dict[str, Any]):
        self._info = connection_info
        self._session = JupyterSession(key=connection_info.get('key', '').encode())
        self._context = zmq.asyncio.Context()
        self._shell: Optional[DealerChannel] = None
        self._iopub: Optional[SubChannel] = None
        self._stdin: Optional[DealerChannel] = None
        self._control: Optional[DealerChannel] = None
        self._hb_socket: Optional[zmq.asyncio.Socket] = None
        self._router = MessageRouter()
        self._collector = OutputCollector()
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._status = KernelStatus.UNKNOWN
        self._status_callbacks: List[Callable[[KernelStatus], None]] = []
    
    def _make_url(self, channel: str) -> str:
        transport = self._info.get('transport', 'tcp')
        ip = self._info.get('ip', '127.0.0.1')
        port = self._info.get(f'{channel}_port')
        return f"{transport}://{ip}:{port}"
    
    async def connect(self) -> None:
        self._shell = DealerChannel(self._context, self._make_url('shell'), self._session)
        self._iopub = SubChannel(self._context, self._make_url('iopub'), self._session)
        self._stdin = DealerChannel(self._context, self._make_url('stdin'), self._session)
        self._control = DealerChannel(self._context, self._make_url('control'), self._session)
        
        await asyncio.gather(
            self._shell.connect(),
            self._iopub.connect(),
            self._stdin.connect(),
            self._control.connect()
        )
        
        self._setup_handlers()
        self._running = True
        self._tasks.append(asyncio.create_task(self._iopub_loop()))
        self._tasks.append(asyncio.create_task(self._shell_reply_loop()))
        self._tasks.append(asyncio.create_task(self._heartbeat_loop()))
    
    def _setup_handlers(self) -> None:
        self._router.register(MessageType.STATUS.value, self._handle_status)
        self._router.register(MessageType.STREAM.value, self._handle_stream)
        self._router.register(MessageType.DISPLAY_DATA.value, self._handle_display_data)
        self._router.register(MessageType.EXECUTE_RESULT.value, self._handle_execute_result)
        self._router.register(MessageType.ERROR.value, self._handle_error)
        self._router.register(MessageType.CLEAR_OUTPUT.value, self._handle_clear_output)
    
    async def _handle_status(self, msg: WireMessage) -> None:
        state = msg.content.get('execution_state', 'unknown')
        self._status = KernelStatus(state)
        for callback in self._status_callbacks:
            callback(self._status)
    
    async def _handle_stream(self, msg: WireMessage) -> None:
        parent_id = msg.parent_header.get('msg_id', '')
        await self._collector.add_stream(parent_id, msg.content['name'], msg.content['text'])
    
    async def _handle_display_data(self, msg: WireMessage) -> None:
        parent_id = msg.parent_header.get('msg_id', '')
        await self._collector.add_display_data(parent_id, msg.content['data'], msg.content.get('metadata', {}))
    
    async def _handle_execute_result(self, msg: WireMessage) -> None:
        parent_id = msg.parent_header.get('msg_id', '')
        await self._collector.add_execute_result(
            parent_id,
            msg.content['execution_count'],
            msg.content['data'],
            msg.content.get('metadata', {})
        )
    
    async def _handle_error(self, msg: WireMessage) -> None:
        parent_id = msg.parent_header.get('msg_id', '')
        await self._collector.add_error(
            parent_id,
            msg.content['ename'],
            msg.content['evalue'],
            msg.content['traceback']
        )
    
    async def _handle_clear_output(self, msg: WireMessage) -> None:
        parent_id = msg.parent_header.get('msg_id', '')
        if msg.content.get('wait', False):
            pass
        else:
            await self._collector.clear(parent_id)
    
    async def _iopub_loop(self) -> None:
        while self._running:
            try:
                msg = await asyncio.wait_for(self._iopub.recv(), timeout=0.5)
                await self._router.route(msg)
            except asyncio.TimeoutError:
                continue
            except Exception:
                if self._running:
                    await asyncio.sleep(0.1)
    
    async def _shell_reply_loop(self) -> None:
        while self._running:
            try:
                msg = await asyncio.wait_for(self._shell.recv(), timeout=0.5)
                await self._router.route(msg)
            except asyncio.TimeoutError:
                continue
            except Exception:
                if self._running:
                    await asyncio.sleep(0.1)
    
    async def _heartbeat_loop(self) -> None:
        self._hb_socket = self._context.socket(zmq.REQ)
        self._hb_socket.connect(self._make_url('hb'))
        
        while self._running:
            try:
                await self._hb_socket.send(b'ping')
                await asyncio.wait_for(self._hb_socket.recv(), timeout=5.0)
                await asyncio.sleep(1.0)
            except asyncio.TimeoutError:
                self._status = KernelStatus.DEAD
                for callback in self._status_callbacks:
                    callback(self._status)
            except Exception:
                if self._running:
                    await asyncio.sleep(1.0)
    
    async def disconnect(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await asyncio.gather(
            self._shell.disconnect() if self._shell else asyncio.sleep(0),
            self._iopub.disconnect() if self._iopub else asyncio.sleep(0),
            self._stdin.disconnect() if self._stdin else asyncio.sleep(0),
            self._control.disconnect() if self._control else asyncio.sleep(0)
        )
        if self._hb_socket:
            self._hb_socket.close()
        self._context.term()
    
    async def execute(
        self,
        code: str,
        silent: bool = False,
        store_history: bool = True,
        user_expressions: Optional[Dict[str, str]] = None,
        allow_stdin: bool = False,
        stop_on_error: bool = True,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        msg = self._session.create_message(
            MessageType.EXECUTE_REQUEST.value,
            {
                'code': code,
                'silent': silent,
                'store_history': store_history,
                'user_expressions': user_expressions or {},
                'allow_stdin': allow_stdin,
                'stop_on_error': stop_on_error
            }
        )
        
        await self._shell.send(msg)
        reply = await self._router.wait_for_reply(msg.msg_id, timeout=timeout)
        
        while self._status == KernelStatus.BUSY:
            await asyncio.sleep(0.01)
        
        outputs = await self._collector.get_outputs(msg.msg_id)
        
        return {
            'status': reply.content.get('status'),
            'execution_count': reply.content.get('execution_count'),
            'outputs': outputs,
            'user_expressions': reply.content.get('user_expressions', {}),
            'payload': reply.content.get('payload', [])
        }
    
    async def complete(self, code: str, cursor_pos: int, timeout: Optional[float] = None) -> Dict[str, Any]:
        msg = self._session.create_message(
            MessageType.COMPLETE_REQUEST.value,
            {'code': code, 'cursor_pos': cursor_pos}
        )
        await self._shell.send(msg)
        reply = await self._router.wait_for_reply(msg.msg_id, timeout=timeout)
        return reply.content
    
    async def inspect(
        self, code: str, cursor_pos: int, detail_level: int = 0, timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        msg = self._session.create_message(
            MessageType.INSPECT_REQUEST.value,
            {'code': code, 'cursor_pos': cursor_pos, 'detail_level': detail_level}
        )
        await self._shell.send(msg)
        reply = await self._router.wait_for_reply(msg.msg_id, timeout=timeout)
        return reply.content
    
    async def is_complete(self, code: str, timeout: Optional[float] = None) -> CodeCompleteness:
        msg = self._session.create_message(
            MessageType.IS_COMPLETE_REQUEST.value,
            {'code': code}
        )
        await self._shell.send(msg)
        reply = await self._router.wait_for_reply(msg.msg_id, timeout=timeout)
        return CodeCompleteness(reply.content.get('status', 'unknown'))
    
    async def kernel_info(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        msg = self._session.create_message(MessageType.KERNEL_INFO_REQUEST.value, {})
        await self._shell.send(msg)
        reply = await self._router.wait_for_reply(msg.msg_id, timeout=timeout)
        return reply.content
    
    async def interrupt(self) -> None:
        msg = self._session.create_message(MessageType.INTERRUPT_REQUEST.value, {})
        await self._control.send(msg)
    
    async def shutdown(self, restart: bool = False) -> None:
        msg = self._session.create_message(MessageType.SHUTDOWN_REQUEST.value, {'restart': restart})
        await self._control.send(msg)
    
    def on_status_change(self, callback: Callable[[KernelStatus], None]) -> Callable[[], None]:
        self._status_callbacks.append(callback)
        return lambda: self._status_callbacks.remove(callback)
    
    @property
    def status(self) -> KernelStatus:
        return self._status


class KernelProcess:
    def __init__(self, kernel_name: str = 'python3'):
        self._kernel_name = kernel_name
        self._manager: Optional[AsyncKernelManager] = None
        self._connection: Optional[KernelConnection] = None
        self._process: Optional[subprocess.Popen] = None
        self._connection_file: Optional[str] = None
    
    async def start(self) -> KernelConnection:
        self._manager = AsyncKernelManager(kernel_name=self._kernel_name)
        await self._manager.start_kernel()
        
        connection_info = self._manager.get_connection_info()
        self._connection = KernelConnection(connection_info)
        await self._connection.connect()
        
        return self._connection
    
    async def restart(self) -> None:
        if self._manager:
            await self._manager.restart_kernel()
    
    async def interrupt(self) -> None:
        if self._manager:
            await self._manager.interrupt_kernel()
    
    async def shutdown(self, now: bool = False) -> None:
        if self._connection:
            await self._connection.disconnect()
        if self._manager:
            await self._manager.shutdown_kernel(now=now)
    
    @property
    def is_alive(self) -> bool:
        return self._manager.is_alive() if self._manager else False


class JupyterKernelPool:
    def __init__(self, kernel_name: str = 'python3', pool_size: int = 4):
        self._kernel_name = kernel_name
        self._pool_size = pool_size
        self._available: asyncio.Queue[KernelProcess] = asyncio.Queue()
        self._in_use: Set[KernelProcess] = set()
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        async with self._lock:
            if self._initialized:
                return
            tasks = [self._create_kernel() for _ in range(self._pool_size)]
            kernels = await asyncio.gather(*tasks)
            for kernel in kernels:
                await self._available.put(kernel)
            self._initialized = True
    
    async def _create_kernel(self) -> KernelProcess:
        kernel = KernelProcess(self._kernel_name)
        await kernel.start()
        return kernel
    
    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[KernelConnection, None]:
        kernel = await self._available.get()
        self._in_use.add(kernel)
        try:
            yield kernel._connection
        finally:
            self._in_use.discard(kernel)
            if kernel.is_alive:
                await self._available.put(kernel)
            else:
                new_kernel = await self._create_kernel()
                await self._available.put(new_kernel)
    
    async def shutdown(self) -> None:
        async with self._lock:
            while not self._available.empty():
                kernel = await self._available.get()
                await kernel.shutdown(now=True)
            for kernel in list(self._in_use):
                await kernel.shutdown(now=True)
            self._in_use.clear()


class CodeExecutionManager:
    def __init__(self, pool: JupyterKernelPool):
        self._pool = pool
        self._execution_history: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def execute(self, code: str, **kwargs) -> Dict[str, Any]:
        execution_id = uuid.uuid4().hex
        async with self._pool.acquire() as connection:
            result = await connection.execute(code, **kwargs)
            async with self._lock:
                self._execution_history[execution_id] = {
                    'code': code,
                    'result': result,
                    'timestamp': time.time()
                }
            return {'execution_id': execution_id, **result}
    
    async def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        async with self._lock:
            items = sorted(self._execution_history.items(), key=lambda x: x[1]['timestamp'], reverse=True)
            return [{'id': k, **v} for k, v in items[:limit]]


async def create_jupyter_client(kernel_name: str = 'python3') -> KernelConnection:
    kernel = KernelProcess(kernel_name)
    return await kernel.start()


async def create_kernel_pool(kernel_name: str = 'python3', pool_size: int = 4) -> JupyterKernelPool:
    pool = JupyterKernelPool(kernel_name, pool_size)
    await pool.initialize()
    return pool


if __name__ == '__main__':
    async def main():
        pool = await create_kernel_pool(pool_size=2)
        manager = CodeExecutionManager(pool)
        
        result = await manager.execute("print('Hello from Jupyter!')\n2 + 2")
        print(json.dumps(result, indent=2, default=str))
        
        result = await manager.execute("import numpy as np\nnp.array([1, 2, 3])")
        print(json.dumps(result, indent=2, default=str))
        
        await pool.shutdown()
    
    asyncio.run(main())
