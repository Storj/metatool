import socketserver


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class MyRequestHandler(socketserver.StreamRequestHandler):
    """
    Request handler for testing metadisk.py.

    """

    def handle(self):
        self.data = self.rfile.readline().strip().split()
        url = self.data[1].decode("utf-8").replace('/', '_')
        message = getattr(self, 'response{}'.format(url))()
        self.wfile.write(message)


    def response_api_files_(self):
        message = b'HTTP/1.0 200 OK\n'
        body = b'\n[]\n'
        headers = {
            'Content-Type': 'application/json',
            'Content-Length': len(body),
        }
        for line in sorted(headers.items()):
            message += bytes('%s: %s\n' % line, 'utf-8')
        message += body
        return message
