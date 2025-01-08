from Fluxon.Endpoint import AsyncServer, run_server
import router

server = run_server(AsyncServer(
    port=8080, secure=False,
    router=router.router
))
