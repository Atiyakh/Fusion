import asyncio
import aiofiles
import traceback
import logging
import json
import pathlib
import os
import shutil
import ssl
from Fluxon.Database.APIs import DatabaseAPI
from Fluxon.Endpoint.server_utils import padded_content_length, folder_structure, content_length, ServerExternalShutdown
from Fluxon.Endpoint.abstract_server import Server

class CloudOpsServer:
    from Fluxon.Filesystem.AuthorizationModels import RoleBasedAccessControl
    main_server: Server
    filesystem_folder: pathlib.Path
    filesystem_auth_model: RoleBasedAccessControl
    filesystem_database: DatabaseAPI

    async def stream_file(self, file_path, chunk_size):
        async with aiofiles.open(file_path, 'rb') as file:
            while chunk := file.read(chunk_size):
                yield chunk

    async def get_file_metadata(path):
        # offloading to a separate thread
        return await asyncio.get_event_loop().run_in_executor(None, os.stat, path)

    async def get_directory_id(self, dir_path, owner_id=False):
        current_folder_id = None
        owner_id_ = None
        columns = ['id', 'owner'] if owner_id else ['id']
        for parent in dir_path.__str__().replace("\\", '/').split("/"):
            query = await self.filesystem_database.Directory.Check(self.filesystem_database.where[
                (self.filesystem_database.Directory.name == parent) & (self.filesystem_database.Directory.directory == current_folder_id)
            ], fetch=1, columns=columns)
            if query:
                current_folder_id = query[0][0]
                if owner_id:
                    owner_id_ = query[0][1]
            else:
                logging.error(f"[CloudStorage] Failed to get directory id ({dir_path})")
        return (current_folder_id, owner_id_) if owner_id else current_folder_id

    async def create_directory(
        self,
        operation_path:pathlib.Path,
        cloud_relative_path:pathlib.Path,
        cloud_database:DatabaseAPI,
        writer:asyncio.StreamWriter
    ):
        try:
            os.mkdir(operation_path)
            # record operation in database
            directory_path = pathlib.Path(cloud_relative_path)
            parent_directory_id, owner_id = await self.get_directory_id(directory_path.parent, owner_id=True)
            await cloud_database.Directory.Insert({
                "name": directory_path.name,
                "owner": owner_id,
                "directory": parent_directory_id
            })
            # report success to client
            writer.write(b"success")
            await writer.drain()
        except:
            traceback.print_exc()
            if writer:
                writer.write(b"[CloudStorage] Unable to create directory")
                await writer.drain()
    
    async def write_file(self, reader, writer, operation_path, file_data, content_length_count, far_host_peername):
        try:
            async with aiofiles.open(operation_path, 'wb') as file:
                if file_data:
                    await file.write(file_data)
                while content_length_count < content_length:
                    try:
                        chunk = await asyncio.wait_for(
                            reader.read(min(content_length - content_length_count, self.buffer_size_limit)),
                            timeout=self.timeout
                        )
                    except asyncio.TimeoutError:
                        self.logger.error(f"Timeout while reading data from {far_host_peername}")
                        return None
                    if not chunk:
                        self.logger.warning(f"Connection closed unexpectedly by {far_host_peername}")
                        return None
                    content_length_count += len(chunk)
                    await file.write(chunk)
        except:
            traceback.print_exc()
            writer.write(b"[CloudStorage] Unable to write file")
            await writer.drain()
            return None
    
    async def delete_item(
        self,
        operation_path:pathlib.Path,
        cloud_relative_path:pathlib.Path,
        cloud_database:DatabaseAPI,
        writer:asyncio.StreamWriter
    ):
        try:
            item = pathlib.Path(operation_path)
            if item.exists():
                if item.is_dir(): # If item is a folder
                    shutil.rmtree(item)
                    # Remove folder from cloud records
                    directory_id = await self.get_directory_id(dir_path=cloud_relative_path)
                    if directory_id:
                        # delete records
                        await cloud_database.Directory.Delete(cloud_database.where[cloud_database.Directory.id == directory_id])
                        # report success to client
                        writer.write(b"success")
                        await writer.drain()
                        return None
                    else:
                        logging.error(f"DirectoryNotFound: Failed to get directory id ({cloud_relative_path})")
                        return None
                elif item.is_file(): # If item is a file
                    os.remove(item)
                    # Remove file from cloud records
                    parent_directory_id = await self.get_directory_id(dir_path=pathlib.Path(cloud_relative_path).parent)
                    if parent_directory_id:
                        # delete records
                        await cloud_database.File.Delete(cloud_database.where[
                            (cloud_database.File.name == pathlib.Path(cloud_relative_path).name) & (cloud_database.File.directory == parent_directory_id)
                        ])
                        # report success to client
                        writer.write(b"success")
                        await writer.drain()
                        return None
                    else:
                        logging.error(f"DirectoryNotFound: Failed to get parent directory id ({cloud_relative_path})")
                        return None
            else:
                writer.write(b"[CloudStorage] Item not found.")
                await writer.drain()
                return None
        except FileNotFoundError:
            writer.write(b"[CloudStorage] Item not found.")
            await writer.drain()
            return None
        except:
            writer.write(f"[CloudStorage] Unable to delete item ({item.absolute()})".encode())
            await writer.drain()
            return None
    
    async def read_file(
        self,
        operation_path:pathlib.Path,
        writer:asyncio.StreamWriter,
        cloud_database:DatabaseAPI,
        cloud_relative_path:pathlib.Path,
        far_host_peername:tuple[str, int]
    ):
        file_path = pathlib.Path(operation_path)
        if file_path.is_file():
            # get file size
            parent_directory_id = await self.get_directory_id(pathlib.Path(cloud_relative_path).parent)
            query = await cloud_database.File.Check(cloud_database.where[
                (cloud_database.File.name == file_path.name) & (cloud_database.File.directory == parent_directory_id)
            ], fetch=1, columns=['size'])
            if query:
                file_size = int(query[0][0])
                # send content length
                writer.write(padded_content_length(file_size, 10))
                await writer.drain()
                # send file stream
                writer_drain_count = 0  # drain every 15 MB
                async with aiofiles.open(file_path, 'rb') as file:
                    file_chunk = await file.read(1024 * 1024) # 1 MB at a time
                    while file_chunk:
                        try:
                            writer.write(file_chunk)
                            writer_drain_count += 1
                            if writer_drain_count == 15:
                                await writer.drain()
                                writer_drain_count = 0
                            file_chunk = await file.read(self.buffer_size_limit)
                        except:
                            traceback.print_exc()
                            self.logger.error(f"Unexpected error while sending data to {far_host_peername}")
                            return None
            else:
                writer.write(("0"*10+f"InvalidOperation: path provided ({file_path.absolute()}) is not a file").encode())
                await writer.drain()
                return None
        else:
            writer.write(("0"*10+f"InvalidOperation: path provided ({file_path.absolute()}) is not a file").encode())
            await writer.drain()
            return None
    
    async def read_tree(
        self, operation_path:pathlib.Path, writer:asyncio.StreamWriter
    ):
        if pathlib.Path(operation_path).is_dir():
            try:
                tree = folder_structure(pathlib.Path(operation_path))
                serialized_tree = json.dumps(tree).encode('utf-8')
                writer.write(padded_content_length(len(serialized_tree), 10))
                writer.write(serialized_tree)
                await writer.drain()
                return None
            except:
                traceback.print_exc()
                self.logger.error("[CloudServer] UnexpectedError: Error while preparing read tree operation")
        else:
            writer.write(("0"*10+f"InvalidOperation: path provided ({str(operation_path)}"))
            await writer.drain()
            return None
    
    async def manage_operation(
        self,
        # -> connection/socket
        reader:asyncio.StreamReader,
        writer:asyncio.StreamWriter,
        far_host_peername:tuple[str, int],
        # -> location
        cloud_relative_path:pathlib.Path,
        cloud_database:DatabaseAPI,
        operation_id:int,
        # -> operation data
        file_data:bytes,  # file data for write operation
        content_length_count:int,  # used to track how much data has been read so far
        operation_path:pathlib.Path  # path to the operation directory or file
    ):
        
        if operation_id == 1:
            await self.create_directory(
                operation_path=operation_path,
                cloud_relative_path=cloud_relative_path,
                cloud_database=cloud_database,
                write=writer,
            )

        elif operation_id == 2:
            await self.write_file(
                reader=reader, writer=writer,
                operation_path=operation_path,
                file_data=file_data,
                content_length_count=content_length_count,
                far_host_peername=far_host_peername,
            )

        elif operation_id == 3:
            await self.delete_item(
                operation_path=operation_path,
                cloud_relative_path=cloud_relative_path,
                cloud_database=cloud_database,
                writer=writer
            )

        elif operation_id == 4:
            await self.read_file(
                operation_path=operation_path,
                writer=writer,
                cloud_database=cloud_database,
                cloud_relative_path=cloud_relative_path,
                far_host_peername=far_host_peername
            )
            
        elif operation_id == 5:
            await self.read_tree(
                operation_path=operation_path,
                writer=writer
            )

    async def handle_cloud_request(self, reader:asyncio.StreamReader, writer:asyncio.StreamWriter):
        try:
            # connection details
            far_host_peername = writer.get_extra_info('peername')
            content_length_count = 0
            headers_length = 0
            content_length = await asyncio.wait_for(reader.read(10), timeout=self.timeout)
            if len(content_length) != 10:
                self.logger.warning(f"Failed to read content length from {far_host_peername}")
                return None
            if not content_length.decode('utf-8').strip().isdigit():
                self.logger.warning(f"Invalid request format from {far_host_peername}")
                return None
            content_length = int(content_length)
            # read the header chunk
            header_chunk = await asyncio.wait_for(
                reader.read(min(content_length - content_length_count, self.buffer_size_limit)),
                timeout=self.timeout
            )
            if not header_chunk:
                self.logger.warning(f"Connection closed unexpectedly by {far_host_peername}")
                return None
            # process header chunk
            content_length_count += len(header_chunk)
            encoded_cloud_relative_path, encoded_operation_name, encoded_session_id, file_data = header_chunk.split(b"|",3)
            headers_length += len(encoded_cloud_relative_path) + len(encoded_session_id) + len(encoded_operation_name) + 3
            cloud_relative_path = encoded_cloud_relative_path.decode()
            operation = encoded_operation_name.decode()
            print("Operation...", operation)
            if operation in self.operation_flags:
                operation = int(operation)
            else:
                return None # invalid cloud request structure
            session_id = encoded_session_id.decode()
            # TODO correct validator
            print("validation point...")
            # validation & operation id retrieval
            if operation_id := self.filesystem_auth_model._validate_operation(
                user_id=self.main_server.setup.SESSION_USER_LOOKUP[session_id], operation=operation
            ):
                print("authenticated...")
                operation_path = pathlib.Path(self.filesystem_folder) / cloud_relative_path
                self.manage_operation(
                    reader=reader, writer=writer,
                    far_host_peername=far_host_peername,
                    cloud_relative_path=cloud_relative_path,
                    cloud_database=self.filesystem_database,
                    operation_id=operation_id,
                    file_data=file_data if file_data else b'',
                    content_length_count=content_length_count,
                    operation_path=operation_path
                )
            else:
                print("authentication error...")
                writer.write(b"[CloudStorage] AccessDenied:")
        except asyncio.TimeoutError:
            return None
        except (OSError, ConnectionResetError):
            self.logger.warning(f"Connection closed unexpectedly by {far_host_peername}")
            return None
        except Exception as e:
            # unexpected error handling
            far_host_peername = locals().get("far_host_peername", "(far_host_peername not provided)")
            exception_details = traceback.format_exc()
            self.logger.error(f"Error while handling request from {far_host_peername}: {str(e)}\nTraceback: {exception_details}")
            print(f"UnexpectedError: Error while handling request from {far_host_peername}: {e}", exception_details, sep="\n")
        finally:
            # close connection
            writer.close()
            await writer.wait_closed()
    
    async def shutdown_worker(self):
        try:
            while not self.main_server.shutdown_event.is_set():
                await asyncio.sleep(1)  # Keep the worker alive until a shutdown signal is received
            # Shut down the cloud server gracefully
            raise ServerExternalShutdown("Shutdown signal received, terminating worker...")
        except asyncio.CancelledError:
            await self.stop_server()
            self.logger.info("[CloudServer] Shutdown worker terminated.")

    async def stop_server(self):
        self.server_stream.close()
        await self.server_stream.wait_closed()
        self.logger.info(f"[CloudServer] Closing server...")
    
    def terminate(self):
        # TODO future cleanup
        ...

    def on_terminate(self):
        """Override this method to handle server termination event."""
        pass

    async def start_server(self):
        try:
            self.timeout = 60
            self.buffer_size_limit = 65536
            if self.secure:
                self.certificatePath = os.path.join(pathlib.Path(__file__).parent, 'Certificates/ssl_tls_certificate.pem')
                self.privateKeyPath = os.path.join(pathlib.Path(__file__).parent, 'Certificates/server_private_key.pem')
                self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                self.context.load_cert_chain(
                    certfile=self.certificatePath, 
                    keyfile=self.privateKeyPath
                )
                self.server_stream = await asyncio.start_server(
                    self.handle_cloud_request, self.host,
                    self.port, ssl=self.context
                )
            else:
                self.server_stream = await asyncio.start_server(
                    self.handle_cloud_request, self.host, self.port
                )
            self.logger.info(f"[CloudStorage] Cloud storage running on {self.host}:{self.port}")
            print(f"[CloudStorage] Cloud storage running on {self.host}:{self.port}")
            try: # catches CancelledError when server closed outside the event loop (remotely from "terminate" command)
                await self.server_stream.serve_forever()
            except asyncio.exceptions.CancelledError:
                self.terminate()
                self.logger.info(f"[CloudStorage] Server terminated...")
                print(f"[CloudStorage] Server terminated...")
        except OSError as e:
            if e.errno == 10048:
                self.logger.warning("[Fluxon] Cloud server is already running.")
                print("[Fluxon] Cloud server is already running.")

    def __init__(self, secure, host, port, filesystem_folder, filesystem_auth_model, filesystem_database, main_server:Server):
        self.secure = secure
        self.host = host
        self.port = port
        self.filesystem_folder = pathlib.Path(filesystem_folder)
        self.filesystem_auth_model = filesystem_auth_model
        self.filesystem_database = filesystem_database
        self.main_server = main_server
        self.logger = logging.getLogger("CloudStorage")
        self.operation_flags = {
            "create_directory": 1,
            "write_file": 2,
            "delete_item": 3,
            "read_file": 4,
            "read_tree": 5
        }
