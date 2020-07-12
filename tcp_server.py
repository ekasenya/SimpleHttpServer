import logging
import shutil
import socket
import threading
from concurrent.futures import ThreadPoolExecutor


class TCPServer:
    address_family = socket.AF_INET
    socket_type = socket.SOCK_STREAM

    request_queue_size = 5

    allow_reuse_address = False

    def __init__(self, server_address, workers_count):
        self.server_address = server_address
        self.workers_count = workers_count
        self.__is_shut_down = threading.Event()
        self.__shutdown_request = False

        self.socket = socket.socket(self.address_family,
                                    self.socket_type)

        self.executor = ThreadPoolExecutor(max_workers=workers_count)

    def bind_and_activate(self):
        try:
            self.server_bind()
            self.server_activate()
        except Exception:
            self.server_close()
            raise

    def server_bind(self):
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()

    def server_activate(self):
        self.socket.listen(self.request_queue_size)

    def serve_forever(self):
        self.bind_and_activate()

        self.__is_shut_down.clear()
        try:
            while not self.__shutdown_request:
                try:
                    conn, client_address = self.socket.accept()
                except socket.error:
                    self.handle_error(None, None)
                    continue

                self.executor.submit(self.handle_request, (conn, client_address))
        finally:
            self.__shutdown_request = False
            self.__is_shut_down.set()

    def server_close(self):
        self.socket.close()

    def shutdown(self):
        self.__shutdown_request = True
        self.__is_shut_down.wait()

    def handle_request(self, params):
        request = TCPClientConnection(params[0], params[1])
        try:
            self.process_request(request)
        except Exception as e:
            self.handle_error(params[1])
        finally:
            request.close()

    def process_request(self, request):
        """Process request and send answer if need. May be overridden.
        """
        pass

    def handle_error(self, client_address):
        import traceback
        logging.info('----------------------------------------\r\n' 
                     'Exception happened during processing of request\r\n{}'
                     '{}\r\n'
                     '----------------------------------------\r\n'
                     .format(client_address + '\r\n' if client_address else '', traceback.format_exc())
                     )


class TCPClientConnection:
    rbufsize = -1
    wbufsize = 0

    def __init__(self, conn, client_address):
        self.connection = conn
        self.client_address = client_address
        self.rfile = self.connection.makefile('rb', self.rbufsize)
        self.wfile = self.connection.makefile('wb', self.wbufsize)

    def read_line(self, size=-1):
        return self.rfile.readline(size)

    def write_line(self, line):
        if line:
            self.wfile.write(line.encode('UTF-8'))
        self.wfile.write('\r\n'.encode('UTF-8'))

    def write_message(self, message):
        self.wfile.write(message.encode('UTF-8'))

    def write_file(self, f):
        shutil.copyfileobj(f, self.wfile)

    def shutdown_request(self):
        try:
            self.connection.shutdown(socket.SHUT_WR)
        except socket.error:
            pass

    def close(self):
        if not self.wfile.closed:
            try:
                self.wfile.flush()
            except socket.error:
                pass

        self.shutdown_request()

        self.wfile.close()
        self.rfile.close()

        self.connection.close()
