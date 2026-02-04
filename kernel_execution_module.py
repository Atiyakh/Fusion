import asyncio
import hashlib
import hmac
import json
import os
import pickle
import signal
import struct
import sys
import threading
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps, lru_cache, partial
from io import StringIO, BytesIO
from pathlib import Path
from queue import Queue, PriorityQueue, Empty
from typing import (
    Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union,
    TypeVar, Generic, Protocol, runtime_checkable, Coroutine, AsyncGenerator
)
import weakref


T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


class KernelState(Enum):
    IDLE = auto()
    BUSY = auto()
    STARTING = auto()
    RESTARTING = auto()
    DEAD = auto()
    INTERRUPTED = auto()


class ExecutionPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass(frozen=True)
class ExecutionRequest:
    code: str
    execution_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    priority: ExecutionPriority = ExecutionPriority.NORMAL
    timeout: Optional[float] = None
    silent: bool = False
    store_history: bool = True
    user_expressions: Dict[str, str] = field(default_factory=dict)
    allow_stdin: bool = False
    stop_on_error: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other: 'ExecutionRequest') -> bool:
        return self.priority.value < other.priority.value


@dataclass
class ExecutionResult:
    execution_id: str
    status: str
    execution_count: int
    outputs: List[Dict[str, Any]]
    error: Optional[Dict[str, Any]]
    payload: List[Dict[str, Any]]
    user_expressions: Dict[str, Any]
    timing: Dict[str, float]
    metadata: Dict[str, Any]


@runtime_checkable
class ExecutionHandler(Protocol):
    def handle_execute_input(self, msg: Dict[str, Any]) -> None: ...
    def handle_execute_result(self, msg: Dict[str, Any]) -> None: ...
    def handle_stream(self, msg: Dict[str, Any]) -> None: ...
    def handle_display_data(self, msg: Dict[str, Any]) -> None: ...
    def handle_error(self, msg: Dict[str, Any]) -> None: ...
    def handle_status(self, msg: Dict[str, Any]) -> None: ...


class CircularBuffer(Generic[T]):
    __slots__ = ('_buffer', '_capacity', '_head', '_tail', '_size', '_lock')
    
    def __init__(self, capacity: int):
        self._buffer: List[Optional[T]] = [None] * capacity
        self._capacity = capacity
        self._head = 0
        self._tail = 0
        self._size = 0
        self._lock = threading.RLock()
    
    def push(self, item: T) -> Optional[T]:
        with self._lock:
            evicted = None
            if self._size == self._capacity:
                evicted = self._buffer[self._head]
                self._head = (self._head + 1) % self._capacity
            else:
                self._size += 1
            self._buffer[self._tail] = item
            self._tail = (self._tail + 1) % self._capacity
            return evicted
    
    def pop(self) -> Optional[T]:
        with self._lock:
            if self._size == 0:
                return None
            self._tail = (self._tail - 1) % self._capacity
            item = self._buffer[self._tail]
            self._buffer[self._tail] = None
            self._size -= 1
            return item
    
    def __iter__(self):
        with self._lock:
            idx = self._head
            for _ in range(self._size):
                yield self._buffer[idx]
                idx = (idx + 1) % self._capacity


class LRUCache(Generic[K, V]):
    def __init__(self, maxsize: int = 128):
        self._cache: Dict[K, V] = {}
        self._order: deque = deque()
        self._maxsize = maxsize
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        with self._lock:
            if key in self._cache:
                self._hits += 1
                self._order.remove(key)
                self._order.append(key)
                return self._cache[key]
            self._misses += 1
            return default
    
    def put(self, key: K, value: V) -> None:
        with self._lock:
            if key in self._cache:
                self._order.remove(key)
            elif len(self._cache) >= self._maxsize:
                oldest = self._order.popleft()
                del self._cache[oldest]
            self._cache[key] = value
            self._order.append(key)
    
    @property
    def hit_ratio(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0


class ExecutionMetrics:
    __slots__ = (
        '_total_executions', '_successful', '_failed', '_total_time',
        '_execution_times', '_lock', '_code_hashes', '_start_time'
    )
    
    def __init__(self, history_size: int = 1000):
        self._total_executions = 0
        self._successful = 0
        self._failed = 0
        self._total_time = 0.0
        self._execution_times = CircularBuffer[float](history_size)
        self._lock = threading.RLock()
        self._code_hashes: Set[str] = set()
        self._start_time = time.monotonic()
    
    def record_execution(self, duration: float, success: bool, code_hash: str) -> None:
        with self._lock:
            self._total_executions += 1
            self._total_time += duration
            self._execution_times.push(duration)
            self._code_hashes.add(code_hash)
            if success:
                self._successful += 1
            else:
                self._failed += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            times = list(self._execution_times)
            return {
                'total_executions': self._total_executions,
                'successful': self._successful,
                'failed': self._failed,
                'success_rate': self._successful / max(1, self._total_executions),
                'total_time': self._total_time,
                'average_time': self._total_time / max(1, self._total_executions),
                'min_time': min(times) if times else 0.0,
                'max_time': max(times) if times else 0.0,
                'unique_code_blocks': len(self._code_hashes),
                'uptime': time.monotonic() - self._start_time
            }


class ExecutionContext:
    __slots__ = (
        '_namespace', '_hidden_namespace', '_execution_count',
        '_history', '_lock', '_parent_context'
    )
    
    def __init__(self, parent: Optional['ExecutionContext'] = None):
        self._namespace: Dict[str, Any] = {}
        self._hidden_namespace: Dict[str, Any] = {}
        self._execution_count = 0
        self._history: List[Tuple[str, Any]] = []
        self._lock = threading.RLock()
        self._parent_context = weakref.ref(parent) if parent else None
    
    def execute(self, code: str, mode: str = 'exec') -> Tuple[Any, Optional[Exception]]:
        with self._lock:
            self._execution_count += 1
            combined_ns = {**self._get_parent_namespace(), **self._namespace}
            try:
                compiled = compile(code, f'<cell_{self._execution_count}>', mode)
                result = eval(compiled, combined_ns, self._namespace)
                self._history.append((code, result))
                return result, None
            except Exception as e:
                return None, e
    
    def _get_parent_namespace(self) -> Dict[str, Any]:
        if self._parent_context:
            parent = self._parent_context()
            if parent:
                return {**parent._get_parent_namespace(), **parent._namespace}
        return {}
    
    def set_variable(self, name: str, value: Any, hidden: bool = False) -> None:
        with self._lock:
            target = self._hidden_namespace if hidden else self._namespace
            target[name] = value
    
    def get_variable(self, name: str) -> Optional[Any]:
        with self._lock:
            if name in self._namespace:
                return self._namespace[name]
            if name in self._hidden_namespace:
                return self._hidden_namespace[name]
            if self._parent_context:
                parent = self._parent_context()
                if parent:
                    return parent.get_variable(name)
            return None


class OutputCapture:
    def __init__(self):
        self._stdout_buffer = StringIO()
        self._stderr_buffer = StringIO()
        self._original_stdout = None
        self._original_stderr = None
        self._outputs: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
    
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = self._create_tee(self._stdout_buffer, self._original_stdout, 'stdout')
        sys.stderr = self._create_tee(self._stderr_buffer, self._original_stderr, 'stderr')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        return False
    
    def _create_tee(self, buffer: StringIO, original, stream_name: str):
        class TeeStream:
            def __init__(inner_self):
                inner_self.buffer = buffer
                inner_self.original = original
                inner_self.name = stream_name
            
            def write(inner_self, data):
                inner_self.buffer.write(data)
                with self._lock:
                    self._outputs.append({
                        'output_type': 'stream',
                        'name': inner_self.name,
                        'text': data
                    })
                return inner_self.original.write(data)
            
            def flush(inner_self):
                inner_self.buffer.flush()
                inner_self.original.flush()
        
        return TeeStream()
    
    def get_outputs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._outputs)


class ExecutionQueue:
    def __init__(self, max_size: int = 1000):
        self._queue: PriorityQueue[Tuple[int, float, ExecutionRequest]] = PriorityQueue(maxsize=max_size)
        self._counter = 0
        self._lock = threading.RLock()
        self._pending: Dict[str, ExecutionRequest] = {}
        self._event = threading.Event()
    
    def enqueue(self, request: ExecutionRequest) -> bool:
        with self._lock:
            if self._queue.full():
                return False
            self._counter += 1
            self._queue.put((request.priority.value, self._counter, request))
            self._pending[request.execution_id] = request
            self._event.set()
            return True
    
    def dequeue(self, timeout: Optional[float] = None) -> Optional[ExecutionRequest]:
        try:
            _, _, request = self._queue.get(timeout=timeout)
            with self._lock:
                self._pending.pop(request.execution_id, None)
            return request
        except Empty:
            return None
    
    def cancel(self, execution_id: str) -> bool:
        with self._lock:
            if execution_id in self._pending:
                del self._pending[execution_id]
                return True
            return False
    
    def pending_count(self) -> int:
        return self._queue.qsize()


class KernelExecutionEngine:
    def __init__(
        self,
        max_workers: int = 4,
        queue_size: int = 1000,
        history_size: int = 10000
    ):
        self._state = KernelState.STARTING
        self._context = ExecutionContext()
        self._queue = ExecutionQueue(queue_size)
        self._metrics = ExecutionMetrics(history_size)
        self._cache = LRUCache[str, ExecutionResult](maxsize=256)
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()
        self._worker_threads: List[threading.Thread] = []
        self._execution_futures: Dict[str, asyncio.Future] = {}
        self._interrupt_flags: Dict[str, threading.Event] = {}
        self._initialize()
    
    def _initialize(self) -> None:
        for i in range(2):
            t = threading.Thread(target=self._worker_loop, daemon=True, name=f'ExecutionWorker-{i}')
            self._worker_threads.append(t)
            t.start()
        self._state = KernelState.IDLE
    
    def _worker_loop(self) -> None:
        while not self._shutdown_event.is_set():
            request = self._queue.dequeue(timeout=0.1)
            if request:
                self._process_request(request)
    
    def _process_request(self, request: ExecutionRequest) -> None:
        start_time = time.perf_counter()
        code_hash = hashlib.sha256(request.code.encode()).hexdigest()
        
        if not request.silent:
            cached = self._cache.get(code_hash)
            if cached and request.store_history:
                self._emit('execution_cached', request.execution_id, cached)
                return
        
        interrupt_event = threading.Event()
        self._interrupt_flags[request.execution_id] = interrupt_event
        
        with self._lock:
            self._state = KernelState.BUSY
        
        try:
            with OutputCapture() as capture:
                result_value, error = self._context.execute(request.code)
            
            duration = time.perf_counter() - start_time
            
            result = ExecutionResult(
                execution_id=request.execution_id,
                status='ok' if error is None else 'error',
                execution_count=self._context._execution_count,
                outputs=capture.get_outputs(),
                error=self._format_error(error) if error else None,
                payload=[],
                user_expressions=self._eval_user_expressions(request.user_expressions),
                timing={'duration': duration, 'start': start_time},
                metadata=request.metadata
            )
            
            self._metrics.record_execution(duration, error is None, code_hash)
            
            if not request.silent:
                self._cache.put(code_hash, result)
            
            self._emit('execution_complete', request.execution_id, result)
            
        except Exception as e:
            self._emit('execution_error', request.execution_id, str(e))
        finally:
            self._interrupt_flags.pop(request.execution_id, None)
            with self._lock:
                self._state = KernelState.IDLE
    
    def _format_error(self, error: Exception) -> Dict[str, Any]:
        return {
            'ename': type(error).__name__,
            'evalue': str(error),
            'traceback': traceback.format_exception(type(error), error, error.__traceback__)
        }
    
    def _eval_user_expressions(self, expressions: Dict[str, str]) -> Dict[str, Any]:
        results = {}
        for name, expr in expressions.items():
            try:
                value, _ = self._context.execute(expr, mode='eval')
                results[name] = {'status': 'ok', 'data': {'text/plain': repr(value)}}
            except Exception as e:
                results[name] = {'status': 'error', 'ename': type(e).__name__, 'evalue': str(e)}
        return results
    
    def _emit(self, event: str, *args, **kwargs) -> None:
        for handler in self._handlers.get(event, []):
            try:
                handler(*args, **kwargs)
            except Exception:
                pass
    
    def on(self, event: str, handler: Callable) -> Callable[[], None]:
        self._handlers[event].append(handler)
        return lambda: self._handlers[event].remove(handler)
    
    def execute(self, code: str, **kwargs) -> str:
        request = ExecutionRequest(code=code, **kwargs)
        self._queue.enqueue(request)
        return request.execution_id
    
    async def execute_async(self, code: str, **kwargs) -> ExecutionResult:
        execution_id = self.execute(code, **kwargs)
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._execution_futures[execution_id] = future
        
        def on_complete(eid: str, result: ExecutionResult):
            if eid == execution_id and execution_id in self._execution_futures:
                loop = future.get_loop()
                loop.call_soon_threadsafe(future.set_result, result)
                del self._execution_futures[execution_id]
        
        self.on('execution_complete', on_complete)
        return await future
    
    def interrupt(self, execution_id: str) -> bool:
        if execution_id in self._interrupt_flags:
            self._interrupt_flags[execution_id].set()
            return True
        return self._queue.cancel(execution_id)
    
    def restart(self) -> None:
        with self._lock:
            self._state = KernelState.RESTARTING
            self._context = ExecutionContext()
            self._cache = LRUCache[str, ExecutionResult](maxsize=256)
            self._state = KernelState.IDLE
    
    def shutdown(self) -> None:
        self._shutdown_event.set()
        self._executor.shutdown(wait=True)
        with self._lock:
            self._state = KernelState.DEAD
    
    @property
    def state(self) -> KernelState:
        return self._state
    
    def get_statistics(self) -> Dict[str, Any]:
        return {
            'state': self._state.name,
            'pending_executions': self._queue.pending_count(),
            'cache_hit_ratio': self._cache.hit_ratio,
            **self._metrics.get_statistics()
        }


class CodeTransformer:
    _transforms: List[Callable[[str], str]] = []
    
    @classmethod
    def register(cls, transform: Callable[[str], str]) -> None:
        cls._transforms.append(transform)
    
    @classmethod
    def apply(cls, code: str) -> str:
        result = code
        for transform in cls._transforms:
            result = transform(result)
        return result


class MagicCommandRegistry:
    _commands: Dict[str, Callable] = {}
    _line_magics: Dict[str, Callable] = {}
    _cell_magics: Dict[str, Callable] = {}
    
    @classmethod
    def register_line_magic(cls, name: str):
        def decorator(func: Callable):
            cls._line_magics[name] = func
            return func
        return decorator
    
    @classmethod
    def register_cell_magic(cls, name: str):
        def decorator(func: Callable):
            cls._cell_magics[name] = func
            return func
        return decorator
    
    @classmethod
    def execute_magic(cls, line: str, cell: Optional[str] = None) -> Any:
        if line.startswith('%%'):
            magic_name = line[2:].split()[0]
            if magic_name in cls._cell_magics:
                return cls._cell_magics[magic_name](line[len(magic_name)+3:], cell)
        elif line.startswith('%'):
            magic_name = line[1:].split()[0]
            if magic_name in cls._line_magics:
                return cls._line_magics[magic_name](line[len(magic_name)+2:])
        raise ValueError(f"Unknown magic command: {line}")


@MagicCommandRegistry.register_line_magic('time')
def time_magic(line: str) -> Dict[str, Any]:
    start = time.perf_counter()
    exec(line)
    return {'wall_time': time.perf_counter() - start}


@MagicCommandRegistry.register_cell_magic('capture')
def capture_magic(line: str, cell: str) -> Dict[str, Any]:
    with OutputCapture() as capture:
        exec(cell)
    return {'outputs': capture.get_outputs()}


class ExecutionHook:
    _pre_hooks: List[Callable[[str], str]] = []
    _post_hooks: List[Callable[[ExecutionResult], ExecutionResult]] = []
    
    @classmethod
    def register_pre_hook(cls, hook: Callable[[str], str]) -> None:
        cls._pre_hooks.append(hook)
    
    @classmethod
    def register_post_hook(cls, hook: Callable[[ExecutionResult], ExecutionResult]) -> None:
        cls._post_hooks.append(hook)
    
    @classmethod
    def run_pre_hooks(cls, code: str) -> str:
        for hook in cls._pre_hooks:
            code = hook(code)
        return code
    
    @classmethod
    def run_post_hooks(cls, result: ExecutionResult) -> ExecutionResult:
        for hook in cls._post_hooks:
            result = hook(result)
        return result


def create_kernel_engine(**kwargs) -> KernelExecutionEngine:
    return KernelExecutionEngine(**kwargs)


if __name__ == '__main__':
    engine = create_kernel_engine()
    engine.on('execution_complete', lambda eid, result: print(f"[{eid}] {result.status}"))
    
    async def main():
        result = await engine.execute_async("x = 42\nprint(x)")
        print(engine.get_statistics())
        engine.shutdown()
    
    asyncio.run(main())
