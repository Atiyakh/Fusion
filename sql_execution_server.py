import asyncio
import hashlib
import hmac
import json
import logging
import os
import pickle
import queue
import re
import secrets
import socket
import sqlite3
import ssl
import struct
import sys
import threading
import time
import traceback
import uuid
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum, IntEnum, auto
from functools import lru_cache, partial, wraps
from io import BytesIO, StringIO
from pathlib import Path
from queue import Empty, PriorityQueue, Queue
from typing import (
    Any, AsyncGenerator, AsyncIterator, Awaitable, Callable, Coroutine, Dict, 
    Generator, Generic, Iterable, Iterator, List, Literal, Mapping, NamedTuple,
    Optional, Protocol, Sequence, Set, Tuple, Type, TypeVar, Union, overload
)
from urllib.parse import parse_qs, urlparse
from weakref import WeakValueDictionary
import aiosqlite
from aiohttp import web
import aiohttp_cors


T = TypeVar('T')
R = TypeVar('R')


class QueryType(Enum):
    SELECT = auto()
    INSERT = auto()
    UPDATE = auto()
    DELETE = auto()
    CREATE = auto()
    DROP = auto()
    ALTER = auto()
    TRUNCATE = auto()
    BEGIN = auto()
    COMMIT = auto()
    ROLLBACK = auto()
    PRAGMA = auto()
    EXPLAIN = auto()
    ATTACH = auto()
    DETACH = auto()
    VACUUM = auto()
    UNKNOWN = auto()


class IsolationLevel(Enum):
    NONE = None
    DEFERRED = 'DEFERRED'
    IMMEDIATE = 'IMMEDIATE'
    EXCLUSIVE = 'EXCLUSIVE'


class ExecutionStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    ERROR = 'error'
    CANCELLED = 'cancelled'
    TIMEOUT = 'timeout'


@dataclass(frozen=True)
class QueryRequest:
    sql: str
    params: Tuple[Any, ...] = field(default_factory=tuple)
    query_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    timeout: Optional[float] = None
    isolation_level: IsolationLevel = IsolationLevel.DEFERRED
    read_only: bool = False
    row_limit: Optional[int] = None
    fetch_size: int = 1000
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResult:
    query_id: str
    status: ExecutionStatus
    rows: List[Tuple[Any, ...]]
    columns: List[str]
    row_count: int
    affected_rows: int
    last_row_id: Optional[int]
    execution_time: float
    query_type: QueryType
    error: Optional[str]
    warnings: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'query_id': self.query_id,
            'status': self.status.value,
            'rows': self.rows,
            'columns': self.columns,
            'row_count': self.row_count,
            'affected_rows': self.affected_rows,
            'last_row_id': self.last_row_id,
            'execution_time': self.execution_time,
            'query_type': self.query_type.name,
            'error': self.error,
            'warnings': self.warnings,
            'metadata': self.metadata
        }


class SQLParseError(Exception):
    def __init__(self, message: str, position: int = -1, token: str = ''):
        super().__init__(message)
        self.position = position
        self.token = token


class SQLSecurityError(Exception):
    pass


class QueryCancelledException(Exception):
    pass


class ConnectionPoolExhausted(Exception):
    pass


class LRUCache(Generic[T]):
    __slots__ = ('_capacity', '_cache', '_lock')
    
    def __init__(self, capacity: int):
        self._capacity = capacity
        self._cache: OrderedDict[str, T] = OrderedDict()
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[T]:
        with self._lock:
            if key not in self._cache:
                return None
            self._cache.move_to_end(key)
            return self._cache[key]
    
    def put(self, key: str, value: T) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self._capacity:
                self._cache.popitem(last=False)
    
    def invalidate(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


class QueryPlanCache:
    def __init__(self, max_size: int = 1000):
        self._cache = LRUCache[Tuple[str, QueryType]](max_size)
        self._hit_count = 0
        self._miss_count = 0
        self._lock = threading.RLock()
    
    def _normalize_query(self, sql: str) -> str:
        normalized = re.sub(r'\s+', ' ', sql.strip().upper())
        normalized = re.sub(r'\d+', '?', normalized)
        normalized = re.sub(r"'[^']*'", '?', normalized)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def get(self, sql: str) -> Optional[Tuple[str, QueryType]]:
        with self._lock:
            key = self._normalize_query(sql)
            result = self._cache.get(key)
            if result:
                self._hit_count += 1
            else:
                self._miss_count += 1
            return result
    
    def put(self, sql: str, parsed: str, query_type: QueryType) -> None:
        with self._lock:
            key = self._normalize_query(sql)
            self._cache.put(key, (parsed, query_type))
    
    @property
    def hit_ratio(self) -> float:
        total = self._hit_count + self._miss_count
        return self._hit_count / total if total > 0 else 0.0


class QueryAnalyzer:
    _QUERY_PATTERNS = [
        (re.compile(r'^\s*SELECT\b', re.I), QueryType.SELECT),
        (re.compile(r'^\s*INSERT\b', re.I), QueryType.INSERT),
        (re.compile(r'^\s*UPDATE\b', re.I), QueryType.UPDATE),
        (re.compile(r'^\s*DELETE\b', re.I), QueryType.DELETE),
        (re.compile(r'^\s*CREATE\b', re.I), QueryType.CREATE),
        (re.compile(r'^\s*DROP\b', re.I), QueryType.DROP),
        (re.compile(r'^\s*ALTER\b', re.I), QueryType.ALTER),
        (re.compile(r'^\s*TRUNCATE\b', re.I), QueryType.TRUNCATE),
        (re.compile(r'^\s*BEGIN\b', re.I), QueryType.BEGIN),
        (re.compile(r'^\s*COMMIT\b', re.I), QueryType.COMMIT),
        (re.compile(r'^\s*ROLLBACK\b', re.I), QueryType.ROLLBACK),
        (re.compile(r'^\s*PRAGMA\b', re.I), QueryType.PRAGMA),
        (re.compile(r'^\s*EXPLAIN\b', re.I), QueryType.EXPLAIN),
        (re.compile(r'^\s*ATTACH\b', re.I), QueryType.ATTACH),
        (re.compile(r'^\s*DETACH\b', re.I), QueryType.DETACH),
        (re.compile(r'^\s*VACUUM\b', re.I), QueryType.VACUUM),
    ]
    
    _DANGEROUS_PATTERNS = [
        re.compile(r';\s*DROP\b', re.I),
        re.compile(r';\s*DELETE\b', re.I),
        re.compile(r';\s*UPDATE\b', re.I),
        re.compile(r';\s*INSERT\b', re.I),
        re.compile(r';\s*CREATE\b', re.I),
        re.compile(r';\s*ALTER\b', re.I),
        re.compile(r'--', re.I),
        re.compile(r'/\*', re.I),
        re.compile(r'UNION\s+SELECT', re.I),
        re.compile(r'INTO\s+OUTFILE', re.I),
        re.compile(r'LOAD_FILE', re.I),
    ]
    
    @classmethod
    def determine_type(cls, sql: str) -> QueryType:
        sql_stripped = sql.strip()
        for pattern, query_type in cls._QUERY_PATTERNS:
            if pattern.match(sql_stripped):
                return query_type
        return QueryType.UNKNOWN
    
    @classmethod
    def validate_security(cls, sql: str, allow_dangerous: bool = False) -> List[str]:
        warnings = []
        if not allow_dangerous:
            for pattern in cls._DANGEROUS_PATTERNS:
                if pattern.search(sql):
                    warnings.append(f"Potentially dangerous pattern detected: {pattern.pattern}")
        if len(sql) > 100000:
            warnings.append("Query exceeds recommended length")
        return warnings
    
    @classmethod
    def is_read_only(cls, query_type: QueryType) -> bool:
        return query_type in {QueryType.SELECT, QueryType.PRAGMA, QueryType.EXPLAIN}


class ConnectionWrapper:
    __slots__ = ('_conn', '_in_use', '_created_at', '_last_used', '_query_count', '_id')
    
    def __init__(self, conn: aiosqlite.Connection):
        self._conn = conn
        self._in_use = False
        self._created_at = time.monotonic()
        self._last_used = time.monotonic()
        self._query_count = 0
        self._id = uuid.uuid4().hex[:8]
    
    @property
    def connection(self) -> aiosqlite.Connection:
        return self._conn
    
    def mark_in_use(self) -> None:
        self._in_use = True
        self._last_used = time.monotonic()
        self._query_count += 1
    
    def mark_available(self) -> None:
        self._in_use = False
        self._last_used = time.monotonic()
    
    @property
    def is_in_use(self) -> bool:
        return self._in_use
    
    @property
    def age(self) -> float:
        return time.monotonic() - self._created_at
    
    @property
    def idle_time(self) -> float:
        return time.monotonic() - self._last_used


class ConnectionPool:
    def __init__(
        self,
        database: str,
        min_connections: int = 2,
        max_connections: int = 10,
        max_idle_time: float = 300.0,
        max_connection_age: float = 3600.0
    ):
        self._database = database
        self._min_connections = min_connections
        self._max_connections = max_connections
        self._max_idle_time = max_idle_time
        self._max_connection_age = max_connection_age
        self._pool: deque[ConnectionWrapper] = deque()
        self._in_use: Set[ConnectionWrapper] = set()
        self._lock = asyncio.Lock()
        self._condition = asyncio.Condition(self._lock)
        self._closed = False
        self._maintenance_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        async with self._lock:
            for _ in range(self._min_connections):
                conn = await self._create_connection()
                self._pool.append(conn)
        self._maintenance_task = asyncio.create_task(self._maintenance_loop())
    
    async def _create_connection(self) -> ConnectionWrapper:
        conn = await aiosqlite.connect(self._database)
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA cache_size=10000")
        await conn.execute("PRAGMA temp_store=MEMORY")
        return ConnectionWrapper(conn)
    
    async def _maintenance_loop(self) -> None:
        while not self._closed:
            await asyncio.sleep(30)
            await self._cleanup_idle_connections()
    
    async def _cleanup_idle_connections(self) -> None:
        async with self._lock:
            to_remove = []
            for wrapper in list(self._pool):
                if wrapper.idle_time > self._max_idle_time or wrapper.age > self._max_connection_age:
                    if len(self._pool) > self._min_connections:
                        to_remove.append(wrapper)
            for wrapper in to_remove:
                self._pool.remove(wrapper)
                await wrapper.connection.close()
    
    @asynccontextmanager
    async def acquire(self, timeout: Optional[float] = 30.0) -> AsyncGenerator[aiosqlite.Connection, None]:
        wrapper = await self._acquire_wrapper(timeout)
        try:
            yield wrapper.connection
        finally:
            await self._release_wrapper(wrapper)
    
    async def _acquire_wrapper(self, timeout: Optional[float]) -> ConnectionWrapper:
        deadline = time.monotonic() + timeout if timeout else None
        
        async with self._condition:
            while True:
                if self._closed:
                    raise ConnectionPoolExhausted("Pool is closed")
                
                if self._pool:
                    wrapper = self._pool.popleft()
                    wrapper.mark_in_use()
                    self._in_use.add(wrapper)
                    return wrapper
                
                if len(self._in_use) < self._max_connections:
                    wrapper = await self._create_connection()
                    wrapper.mark_in_use()
                    self._in_use.add(wrapper)
                    return wrapper
                
                if deadline:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ConnectionPoolExhausted("Timeout waiting for connection")
                    await asyncio.wait_for(self._condition.wait(), timeout=remaining)
                else:
                    await self._condition.wait()
    
    async def _release_wrapper(self, wrapper: ConnectionWrapper) -> None:
        async with self._condition:
            wrapper.mark_available()
            self._in_use.discard(wrapper)
            
            if wrapper.age < self._max_connection_age:
                self._pool.append(wrapper)
            else:
                await wrapper.connection.close()
                if len(self._pool) + len(self._in_use) < self._min_connections:
                    new_wrapper = await self._create_connection()
                    self._pool.append(new_wrapper)
            
            self._condition.notify()
    
    async def close(self) -> None:
        self._closed = True
        if self._maintenance_task:
            self._maintenance_task.cancel()
        
        async with self._lock:
            for wrapper in list(self._pool):
                await wrapper.connection.close()
            for wrapper in list(self._in_use):
                await wrapper.connection.close()
            self._pool.clear()
            self._in_use.clear()
    
    @property
    def stats(self) -> Dict[str, Any]:
        return {
            'available': len(self._pool),
            'in_use': len(self._in_use),
            'total': len(self._pool) + len(self._in_use),
            'max_connections': self._max_connections
        }


class QueryExecutor:
    def __init__(self, pool: ConnectionPool, plan_cache: Optional[QueryPlanCache] = None):
        self._pool = pool
        self._plan_cache = plan_cache or QueryPlanCache()
        self._active_queries: Dict[str, asyncio.Event] = {}
        self._query_metrics: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def execute(self, request: QueryRequest) -> QueryResult:
        start_time = time.perf_counter()
        cancel_event = asyncio.Event()
        
        async with self._lock:
            self._active_queries[request.query_id] = cancel_event
        
        try:
            query_type = QueryAnalyzer.determine_type(request.sql)
            warnings = QueryAnalyzer.validate_security(request.sql)
            
            if request.read_only and not QueryAnalyzer.is_read_only(query_type):
                return QueryResult(
                    query_id=request.query_id,
                    status=ExecutionStatus.ERROR,
                    rows=[],
                    columns=[],
                    row_count=0,
                    affected_rows=0,
                    last_row_id=None,
                    execution_time=time.perf_counter() - start_time,
                    query_type=query_type,
                    error="Write operations not allowed in read-only mode",
                    warnings=warnings,
                    metadata=request.metadata
                )
            
            async with self._pool.acquire(timeout=request.timeout) as conn:
                if cancel_event.is_set():
                    raise QueryCancelledException()
                
                if request.isolation_level.value:
                    await conn.execute(f"BEGIN {request.isolation_level.value}")
                
                cursor = await conn.execute(request.sql, request.params)
                
                if query_type == QueryType.SELECT:
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    rows = []
                    row_count = 0
                    
                    while True:
                        if cancel_event.is_set():
                            raise QueryCancelledException()
                        
                        batch = await cursor.fetchmany(request.fetch_size)
                        if not batch:
                            break
                        
                        for row in batch:
                            if request.row_limit and row_count >= request.row_limit:
                                break
                            rows.append(tuple(row))
                            row_count += 1
                        
                        if request.row_limit and row_count >= request.row_limit:
                            break
                    
                    result = QueryResult(
                        query_id=request.query_id,
                        status=ExecutionStatus.SUCCESS,
                        rows=rows,
                        columns=columns,
                        row_count=row_count,
                        affected_rows=0,
                        last_row_id=None,
                        execution_time=time.perf_counter() - start_time,
                        query_type=query_type,
                        error=None,
                        warnings=warnings,
                        metadata=request.metadata
                    )
                else:
                    await conn.commit()
                    result = QueryResult(
                        query_id=request.query_id,
                        status=ExecutionStatus.SUCCESS,
                        rows=[],
                        columns=[],
                        row_count=0,
                        affected_rows=cursor.rowcount,
                        last_row_id=cursor.lastrowid,
                        execution_time=time.perf_counter() - start_time,
                        query_type=query_type,
                        error=None,
                        warnings=warnings,
                        metadata=request.metadata
                    )
                
                execution_time = time.perf_counter() - start_time
                async with self._lock:
                    self._query_metrics[query_type.name].append(execution_time)
                
                return result
        
        except QueryCancelledException:
            return QueryResult(
                query_id=request.query_id,
                status=ExecutionStatus.CANCELLED,
                rows=[],
                columns=[],
                row_count=0,
                affected_rows=0,
                last_row_id=None,
                execution_time=time.perf_counter() - start_time,
                query_type=QueryAnalyzer.determine_type(request.sql),
                error="Query was cancelled",
                warnings=[],
                metadata=request.metadata
            )
        
        except asyncio.TimeoutError:
            return QueryResult(
                query_id=request.query_id,
                status=ExecutionStatus.TIMEOUT,
                rows=[],
                columns=[],
                row_count=0,
                affected_rows=0,
                last_row_id=None,
                execution_time=time.perf_counter() - start_time,
                query_type=QueryAnalyzer.determine_type(request.sql),
                error="Query timed out",
                warnings=[],
                metadata=request.metadata
            )
        
        except Exception as e:
            return QueryResult(
                query_id=request.query_id,
                status=ExecutionStatus.ERROR,
                rows=[],
                columns=[],
                row_count=0,
                affected_rows=0,
                last_row_id=None,
                execution_time=time.perf_counter() - start_time,
                query_type=QueryAnalyzer.determine_type(request.sql),
                error=str(e),
                warnings=[],
                metadata=request.metadata
            )
        
        finally:
            async with self._lock:
                self._active_queries.pop(request.query_id, None)
    
    async def cancel(self, query_id: str) -> bool:
        async with self._lock:
            if query_id in self._active_queries:
                self._active_queries[query_id].set()
                return True
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        metrics = {}
        for query_type, times in self._query_metrics.items():
            if times:
                metrics[query_type] = {
                    'count': len(times),
                    'total_time': sum(times),
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times)
                }
        return metrics


class TransactionManager:
    def __init__(self, executor: QueryExecutor):
        self._executor = executor
        self._active_transactions: Dict[str, List[QueryRequest]] = {}
        self._lock = asyncio.Lock()
    
    async def begin(self, transaction_id: Optional[str] = None) -> str:
        tx_id = transaction_id or uuid.uuid4().hex
        async with self._lock:
            self._active_transactions[tx_id] = []
        return tx_id
    
    async def execute_in_transaction(self, transaction_id: str, request: QueryRequest) -> QueryResult:
        async with self._lock:
            if transaction_id not in self._active_transactions:
                raise ValueError(f"Transaction {transaction_id} not found")
            self._active_transactions[transaction_id].append(request)
        return await self._executor.execute(request)
    
    async def commit(self, transaction_id: str) -> None:
        async with self._lock:
            if transaction_id not in self._active_transactions:
                raise ValueError(f"Transaction {transaction_id} not found")
            del self._active_transactions[transaction_id]
    
    async def rollback(self, transaction_id: str) -> None:
        async with self._lock:
            if transaction_id not in self._active_transactions:
                raise ValueError(f"Transaction {transaction_id} not found")
            del self._active_transactions[transaction_id]


class SQLExecutionServer:
    def __init__(
        self,
        database: str,
        host: str = '127.0.0.1',
        port: int = 8765,
        max_connections: int = 10
    ):
        self._database = database
        self._host = host
        self._port = port
        self._pool: Optional[ConnectionPool] = None
        self._executor: Optional[QueryExecutor] = None
        self._transaction_manager: Optional[TransactionManager] = None
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._max_connections = max_connections
        self._request_count = 0
        self._start_time: Optional[float] = None
    
    async def initialize(self) -> None:
        self._pool = ConnectionPool(
            self._database,
            max_connections=self._max_connections
        )
        await self._pool.initialize()
        self._executor = QueryExecutor(self._pool)
        self._transaction_manager = TransactionManager(self._executor)
        self._app = web.Application()
        self._setup_routes()
        self._setup_cors()
    
    def _setup_routes(self) -> None:
        self._app.router.add_post('/execute', self._handle_execute)
        self._app.router.add_post('/execute/batch', self._handle_batch_execute)
        self._app.router.add_post('/cancel/{query_id}', self._handle_cancel)
        self._app.router.add_post('/transaction/begin', self._handle_begin_transaction)
        self._app.router.add_post('/transaction/{tx_id}/execute', self._handle_transaction_execute)
        self._app.router.add_post('/transaction/{tx_id}/commit', self._handle_commit)
        self._app.router.add_post('/transaction/{tx_id}/rollback', self._handle_rollback)
        self._app.router.add_get('/health', self._handle_health)
        self._app.router.add_get('/metrics', self._handle_metrics)
        self._app.router.add_get('/schema', self._handle_schema)
        self._app.router.add_get('/tables', self._handle_tables)
    
    def _setup_cors(self) -> None:
        cors = aiohttp_cors.setup(self._app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods=["GET", "POST", "OPTIONS"]
            )
        })
        for route in list(self._app.router.routes()):
            cors.add(route)
    
    async def _handle_execute(self, request: web.Request) -> web.Response:
        self._request_count += 1
        try:
            data = await request.json()
            query_request = QueryRequest(
                sql=data['sql'],
                params=tuple(data.get('params', [])),
                timeout=data.get('timeout'),
                read_only=data.get('read_only', False),
                row_limit=data.get('row_limit'),
                fetch_size=data.get('fetch_size', 1000),
                metadata=data.get('metadata', {})
            )
            result = await self._executor.execute(query_request)
            return web.json_response(result.to_dict())
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def _handle_batch_execute(self, request: web.Request) -> web.Response:
        self._request_count += 1
        try:
            data = await request.json()
            queries = data.get('queries', [])
            results = []
            for q in queries:
                query_request = QueryRequest(
                    sql=q['sql'],
                    params=tuple(q.get('params', [])),
                    timeout=q.get('timeout'),
                    read_only=q.get('read_only', False)
                )
                result = await self._executor.execute(query_request)
                results.append(result.to_dict())
            return web.json_response({'results': results})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def _handle_cancel(self, request: web.Request) -> web.Response:
        query_id = request.match_info['query_id']
        cancelled = await self._executor.cancel(query_id)
        return web.json_response({'cancelled': cancelled})
    
    async def _handle_begin_transaction(self, request: web.Request) -> web.Response:
        tx_id = await self._transaction_manager.begin()
        return web.json_response({'transaction_id': tx_id})
    
    async def _handle_transaction_execute(self, request: web.Request) -> web.Response:
        tx_id = request.match_info['tx_id']
        try:
            data = await request.json()
            query_request = QueryRequest(
                sql=data['sql'],
                params=tuple(data.get('params', []))
            )
            result = await self._transaction_manager.execute_in_transaction(tx_id, query_request)
            return web.json_response(result.to_dict())
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def _handle_commit(self, request: web.Request) -> web.Response:
        tx_id = request.match_info['tx_id']
        try:
            await self._transaction_manager.commit(tx_id)
            return web.json_response({'committed': True})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def _handle_rollback(self, request: web.Request) -> web.Response:
        tx_id = request.match_info['tx_id']
        try:
            await self._transaction_manager.rollback(tx_id)
            return web.json_response({'rolled_back': True})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def _handle_health(self, request: web.Request) -> web.Response:
        pool_stats = self._pool.stats if self._pool else {}
        uptime = time.monotonic() - self._start_time if self._start_time else 0
        return web.json_response({
            'status': 'healthy',
            'uptime': uptime,
            'pool': pool_stats
        })
    
    async def _handle_metrics(self, request: web.Request) -> web.Response:
        executor_metrics = self._executor.get_metrics() if self._executor else {}
        pool_stats = self._pool.stats if self._pool else {}
        return web.json_response({
            'request_count': self._request_count,
            'query_metrics': executor_metrics,
            'pool_stats': pool_stats
        })
    
    async def _handle_schema(self, request: web.Request) -> web.Response:
        try:
            result = await self._executor.execute(QueryRequest(
                sql="SELECT name, sql FROM sqlite_master WHERE type='table'"
            ))
            schema = {}
            for row in result.rows:
                table_name, create_sql = row
                schema[table_name] = create_sql
            return web.json_response({'schema': schema})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def _handle_tables(self, request: web.Request) -> web.Response:
        try:
            result = await self._executor.execute(QueryRequest(
                sql="SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ))
            tables = [row[0] for row in result.rows]
            return web.json_response({'tables': tables})
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)
    
    async def start(self) -> None:
        self._start_time = time.monotonic()
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()
    
    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
        if self._pool:
            await self._pool.close()


class SQLClientSession:
    def __init__(self, base_url: str):
        self._base_url = base_url.rstrip('/')
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self) -> 'SQLClientSession':
        self._session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session:
            await self._session.close()
    
    async def execute(
        self,
        sql: str,
        params: Optional[List[Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        async with self._session.post(
            f'{self._base_url}/execute',
            json={'sql': sql, 'params': params or [], **kwargs}
        ) as response:
            return await response.json()
    
    async def execute_batch(self, queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        async with self._session.post(
            f'{self._base_url}/execute/batch',
            json={'queries': queries}
        ) as response:
            return await response.json()
    
    async def cancel(self, query_id: str) -> Dict[str, Any]:
        async with self._session.post(f'{self._base_url}/cancel/{query_id}') as response:
            return await response.json()
    
    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator['TransactionContext', None]:
        async with self._session.post(f'{self._base_url}/transaction/begin') as response:
            data = await response.json()
            tx_id = data['transaction_id']
        
        ctx = TransactionContext(self._session, self._base_url, tx_id)
        try:
            yield ctx
            await ctx.commit()
        except Exception:
            await ctx.rollback()
            raise


class TransactionContext:
    def __init__(self, session: aiohttp.ClientSession, base_url: str, tx_id: str):
        self._session = session
        self._base_url = base_url
        self._tx_id = tx_id
    
    async def execute(self, sql: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        async with self._session.post(
            f'{self._base_url}/transaction/{self._tx_id}/execute',
            json={'sql': sql, 'params': params or []}
        ) as response:
            return await response.json()
    
    async def commit(self) -> None:
        async with self._session.post(f'{self._base_url}/transaction/{self._tx_id}/commit'):
            pass
    
    async def rollback(self) -> None:
        async with self._session.post(f'{self._base_url}/transaction/{self._tx_id}/rollback'):
            pass


async def create_sql_server(
    database: str,
    host: str = '127.0.0.1',
    port: int = 8765,
    **kwargs
) -> SQLExecutionServer:
    server = SQLExecutionServer(database, host, port, **kwargs)
    await server.initialize()
    return server


if __name__ == '__main__':
    async def main():
        server = await create_sql_server(':memory:', port=8765)
        await server.start()
        
        async with SQLClientSession('http://127.0.0.1:8765') as client:
            await client.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
            await client.execute("INSERT INTO users (name) VALUES (?)", ["Alice"])
            await client.execute("INSERT INTO users (name) VALUES (?)", ["Bob"])
            
            result = await client.execute("SELECT * FROM users")
            print(json.dumps(result, indent=2))
            
            async with client.transaction() as tx:
                await tx.execute("INSERT INTO users (name) VALUES (?)", ["Charlie"])
                await tx.execute("UPDATE users SET name = ? WHERE id = ?", ["Alicia", 1])
            
            result = await client.execute("SELECT * FROM users")
            print(json.dumps(result, indent=2))
        
        await server.stop()
    
    asyncio.run(main())
