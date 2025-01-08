from Fluxon.Endpoint import AsyncServer, CloudStorageServer, run_server
import router

cloud_folder = "C:/Users/skhodari/Desktop/TESTING/SERVER_TEST/cloud_folder"

server = run_server(AsyncServer(
    port=8080, secure=False,
    router=router.router,
    # cloud storage setup
    cloud_storage=CloudStorageServer(
        port=8888, secure=False,
        cloud_folder=cloud_folder
    )
))
