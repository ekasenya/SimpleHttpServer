import errno
import logging
import select
import socket
import threading
import shutil


def _eintr_retry(func, *args):
    """restart a system call interrupted by EINTR"""
    while True:
        try:
            return func(*args)
        except (OSError, select.error) as e:
            if e.args[0] != errno.EINTR:
                raise


class TCPServer:
    """Base class for various socket-based server classes.
    Defaults to synchronous IP stream (i.e., TCP).
    Methods for the caller:
    - __init__(server_address, RequestHandlerClass, bind_and_activate=True)
    - serve_forever(poll_interval=0.5)
    - shutdown()
    - handle_request()  # if you don't use serve_forever()
    - fileno() -> int   # for select()
    Methods that may be overridden:
    - server_bind()
    - server_activate()
    - get_request() -> request, client_address
    - handle_timeout()
    - verify_request(request, client_address)
    - process_request(request, client_address)
    - shutdown_request(request)
    - close_request(request)
    - handle_error()
    Methods for derived classes:
    - finish_request(request, client_address)
    Class variables that may be overridden by derived classes or
    instances:
    - timeout
    - address_family
    - socket_type
    - request_queue_size (only for stream sockets)
    - allow_reuse_address
    Instance variables:
    - server_address
    - socket
    """

    address_family = socket.AF_INET

    socket_type = socket.SOCK_STREAM

    request_queue_size = 5

    allow_reuse_address = False

    timeout = None

    def __init__(self, server_address):
        """Constructor.  May be extended, do not override."""
        self.server_address = server_address
        self.__is_shut_down = threading.Event()
        self.__shutdown_request = False

        self.socket = socket.socket(self.address_family,
                                    self.socket_type)

    def bind_and_activate(self):
        try:
            self.server_bind()
            self.server_activate()
        except Exception:
            self.server_close()
            raise

    def server_bind(self):
        """Bind the socket.
        """
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()

    def server_activate(self):
        """Activate the server.
        """
        self.socket.listen(self.request_queue_size)

    def serve_forever(self, poll_interval=0.5):
        """Handle one request at a time until shutdown.
        Polls for shutdown every poll_interval seconds. Ignores
        self.timeout. If you need to do periodic tasks, do them in
        another thread.
        """
        self.bind_and_activate()

        self.__is_shut_down.clear()
        try:
            while not self.__shutdown_request:
                # XXX: Consider using another file descriptor or
                # connecting to the socket to wake this up instead of
                # polling. Polling reduces our responsiveness to a
                # shutdown request and wastes cpu at all other times.
                r, w, e = _eintr_retry(select.select, [self], [], [],
                                       poll_interval)
                # bpo-35017: shutdown() called during select(), exit immediately.
                if self.__shutdown_request:
                    break
                if self in r:
                    self._handle_request_noblock()
        finally:
            self.__shutdown_request = False
            self.__is_shut_down.set()

    def server_close(self):
        """Called to clean-up the server.
        """
        self.socket.close()

    def fileno(self):
        """Return socket file number.
        Interface required by select().
        """
        return self.socket.fileno()

    def shutdown(self):
        """Stops the serve_forever loop.
        Blocks until the loop has finished. This must be called while
        serve_forever() is running in another thread, or it will
        deadlock.
        """
        self.__shutdown_request = True
        self.__is_shut_down.wait()

    def handle_request(self):
        """Handle one request, possibly blocking.
        Respects self.timeout.
        """
        # Support people who used socket.settimeout() to escape
        # handle_request before self.timeout was available.
        timeout = self.socket.gettimeout()
        if timeout is None:
            timeout = self.timeout
        elif self.timeout is not None:
            timeout = min(timeout, self.timeout)
        fd_sets = _eintr_retry(select.select, [self], [], [], timeout)
        if not fd_sets[0]:
            self.handle_timeout()
            return
        self._handle_request_noblock()

    def _handle_request_noblock(self):
        """Handle one request, without blocking.
        I assume that select.select has returned that the socket is
        readable before this function was called, so there should be
        no risk of blocking in get_request().
        """
        try:
            conn, client_address = self.socket.accept()
            request = TCPClientConnection(conn, client_address)
        except socket.error:
            return

        try:
            self.process_request(request)
        except Exception as e:
            self.handle_error(conn, client_address)
        finally:
            request.close()

    def handle_timeout(self):
        """Called if no new request arrives within self.timeout.
        Overridden by ForkingMixIn.
        """
        pass

    def process_request(self, request):
        """Process request and send answer if need. May be overridden.
        """
        pass

    def handle_error(self, client_conn, client_address):
        logging.info('-'*40)
        logging.info('Exception happened during processing of request from')
        logging.info(client_address)
        import traceback
        logging.info(traceback.format_exc())
        logging.info('-'*40)


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
            pass  # some platforms may raise ENOTCONN here

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


