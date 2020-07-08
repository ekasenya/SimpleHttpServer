import logging
from datetime import datetime

from tcp_server import TCPServer

HOST = 'localhost'
PORT = 65432

NEWLINE = (b'\r\n', b'\n')

RESPONSES = {
    200: 'OK',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed'
}


class SimpleHTTPServer(TCPServer):
    server_version = 'SimpleHttpServer/1.0'
    headers = ''

    def process_request(self, client_conn):
        self.read_request(client_conn)
        self.write_response(client_conn, 200)

    def read_request(self, client_conn):
        print('*' * 40)
        print('Start process request')

        cnt = 0
        while True:
            line = client_conn.read_line()
            print(line)
            if line in NEWLINE:
                break

            if cnt != 0:
                self.headers += line.decode('UTF-8')
            cnt += 1

        print('Finish process request')
        print('*' * 40)

    def write_response(self, client_conn, code):
        self.send_status_line(client_conn, code, RESPONSES[code])
        self.send_headers(client_conn)

    def send_status_line(self, client_conn, code, message):
        client_conn.write_line('HTTP/1.1 {} {}'.format(code, message))

    def send_headers(self, client_conn):
        self.send_header(client_conn, 'Date,', datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GTM'))
        self.send_header(client_conn, 'Server', self.server_version)
        self.send_header(client_conn, 'Content-Length', '')
        self.send_header(client_conn, 'Content-Type', 'text/plain; charset=utf-8')
        self.send_header(client_conn, 'Connection', 'keep-alive')

    def send_header(self, client_conn, keyword, value):
        client_conn.write_line('{}: {}'.format(keyword, value))


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Starting server at {}".format(PORT))

    server = SimpleHTTPServer((HOST, PORT))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
