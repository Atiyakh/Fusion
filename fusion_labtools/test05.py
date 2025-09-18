import asyncio

class AsyncHTTPServer:
    def __init__(self, host='127.0.0.1', port=8080):
        self.host = host
        self.port = port
        self.routes = {}

    def route(self, path):
        def decorator(func):
            print(func.__name__, "registered for path:", path)
            self.routes[path] = func
            return func
        return decorator

    async def handle_client(self, reader, writer):
        try:
            data = await asyncio.wait_for(reader.read(1024), timeout=5.0)
        except asyncio.TimeoutError:
            writer.close()
            await writer.wait_closed()
            return

        request_line = data.decode().splitlines()[0]
        method, path, _ = request_line.split()

        handler = self.routes.get(path, self.default_handler)
        status, body = await handler(method, path)

        response = (
            f"HTTP/1.1 {status}\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Content-Type: text/plain\r\n"
            f"Connection: close\r\n"
            f"\r\n"
            f"{body}"
        )

        writer.write(response.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    async def default_handler(self, method, path):
        return "404 Not Found", f"Path {path} not found."

    async def start(self):
        server = await asyncio.start_server(
            self.handle_client, self.host, self.port)
        addr = server.sockets[0].getsockname()
        print(f"Serving on {addr}")

        async with server:
            await server.serve_forever()

# --- Example Usage ---
if __name__ == "__main__":
    server = AsyncHTTPServer()

    @server.route("/")
    async def index(method, path):
        print(method, path)
        return "200 OK", "Hello, world!"

    @server.route("/ping")
    async def ping(method, path):
        return "200 OK", "pong"

    asyncio.run(server.start())
