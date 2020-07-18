import logging
import os
from argparse import ArgumentParser
from datetime import datetime
from mimetypes import types_map
from urllib.parse import unquote

from tcp_server import TCPServer

HOST = 'localhost'
PORT = 8080

NEWLINE = ('\r\n', '\n')

DEFAULT_DOCUMENT_ROOT = './'
DEFAULT_WORKERS_COUNT = 5


class SimpleHTTPServer(TCPServer):
    server_version = 'SimpleHttpServer/1.0'
    http_version = 'HTTP/1.1'
    headers = ''

    MAX_URL_LENGTH = 65537

    RESPONSES = {
        200: 'OK',
        400: 'Bad Request',
        403: 'Forbidden',
        404: 'Not Found',
        405: 'Method Not Allowed',
        414: 'Request-URI Too Long',
        500: 'Server Internal Error'
    }

    HTTP_METHODS = {
        'GET': 'do_get',
        'HEAD': 'do_head'
    }

    def __init__(self, server_address, document_root, workers_count):
        super(SimpleHTTPServer, self).__init__(server_address, workers_count)
        self.document_root = document_root

    def process_request(self, client_conn):
        status_line = self.read_status_line(client_conn)
        self.log_request(status_line)

        if not status_line:
            return

        request_info = self.parse_status_line(client_conn, status_line)
        if not request_info:
            return

        if not request_info['method'] in self.HTTP_METHODS:
            self.write_response(client_conn, 405, 'Method {} Not Allowed'.format(request_info['method']))
            return

        headers = self.read_headers(client_conn)

        method_name = self.HTTP_METHODS[request_info['method']]
        http_method = getattr(self, method_name)
        http_method(client_conn, request_info['path'], headers)

    def read_status_line(self, client_conn):
        status_line = client_conn.read_line(self.MAX_URL_LENGTH).decode('UTF-8')
        if len(status_line) > self.MAX_URL_LENGTH - 1:
            self.write_response(client_conn, 414)
            return

        return status_line

    def parse_status_line(self, client_conn, line):
        words = line.rstrip('\r\n').split()
        if len(words):
            method, target, version = words
            path = os.path.normpath(unquote(target.split('?', 1)[0]))
            if version[:5] != 'HTTP/':
                self.write_response(client_conn, 400, "Bad request version {}".format(version))
                return
            try:
                base_version_number = version.split('/', 1)[1]
                version_number = base_version_number.split(".")
                if len(version_number) != 2:
                    raise ValueError
                version_number = int(version_number[0]), int(version_number[1])
            except (ValueError, IndexError):
                self.write_response(client_conn, 400, "Bad request version {}".format(version))
                return

            if version_number >= (2, 0):
                self.write_response(client_conn, 505, "Invalid HTTP Version {}".format(base_version_number))
                return

            return {'method': method, 'path': path}
        elif not words:
            return
        else:
            self.write_response(client_conn, 400, 'Bad request syntax {}'.format(line))

    def read_headers(self, client_conn):
        headers = {}
        while True:
            header = client_conn.read_line().decode('UTF-8')
            if not header or header in NEWLINE:
                break

            if header.find(':') < 0:
                key, value = header.strip('\r\n').split(': ')
                headers[key] = value
            else:
                headers[header] = ''

        return headers

    def do_get(self, client_conn, path, headers):
        self.send_file(client_conn, path, True)

    def do_head(self, client_conn, path, headers):
        self.send_file(client_conn, path, False)

    def send_file(self, client_conn, target, send_content):
        if '..' in target.split(os.sep):
            self.write_response(client_conn, 403)
            return

        target = os.path.join(self.document_root, target[1:])
        if os.path.isdir(target):
            target = os.path.join(target, 'index.html')

        if not os.path.exists(target):
            self.write_response(client_conn, 404)
            return

        self.send_status_line(client_conn, 200)
        self.send_common_headers(client_conn)
        self.send_header(client_conn, 'Content-Length', str(os.path.getsize(target)))
        self.send_header(client_conn, 'Content-Type', self.get_content_type(target))
        self.end_headers(client_conn)

        if send_content:
            self.send_file_content(client_conn, target)

    def send_file_content(self, client_conn, target):
        f = None
        try:
            try:
                f = open(target, 'rb')
            except IOError:
                self.write_response(client_conn, 404)
                return
            client_conn.write_file(f)
        finally:
            if f:
                f.close()

    def get_content_type(self, file_name):
        content_type = types_map[os.path.splitext(file_name)[1]]
        return content_type

    def write_response(self, client_conn, code, message=''):
        self.send_status_line(client_conn, code, message)
        self.send_common_headers(client_conn)
        self.end_headers(client_conn)

    def send_status_line(self, client_conn, code, message=''):
        client_conn.write_line('{} {} {}'.format(self.http_version, code, message or self.RESPONSES[code]))

    def send_common_headers(self, client_conn):
        self.send_header(client_conn, 'Date,', datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GTM'))
        self.send_header(client_conn, 'Server', self.server_version)
        self.send_header(client_conn, 'Connection', 'close')

    def send_header(self, client_conn, keyword, value):
        client_conn.write_line('{}: {}'.format(keyword, value))

    def end_headers(self, client_conn):
        client_conn.write_line('')

    def log_request(self, status_request_line):
        logging.info('Request received: {}'.format(status_request_line.rstrip('\r\n')))


def get_config_params():
    parser = ArgumentParser()
    parser.add_argument("--r", default=DEFAULT_DOCUMENT_ROOT)
    parser.add_argument("--w", default=DEFAULT_WORKERS_COUNT)

    try:
        w = int(parser.parse_args().w)
    except ValueError:
        w = DEFAULT_WORKERS_COUNT

    return parser.parse_args().r, w


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S', level=logging.INFO)
    logging.info("Starting server at {}".format(PORT))

    document_root, workers_count = get_config_params()

    server = SimpleHTTPServer((HOST, PORT), document_root, workers_count)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
