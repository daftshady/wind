"""

    wind.web.httpserver
    ~~~~~~~~~~~~~~~~~~~
    
    Http server inherits socketserver.TCPServer.

"""

from wind.socketserver import TCPServer
from wind.web.httpmodels import HTTPHandler


class HTTPServer(TCPServer):
    """HTTPServer class"""
    def __init__(self, looper=None, app=None, *args, **kwargs):
        self._app = app
        super(HTTPServer, self).__init__(*args, **kwargs)

    def _connection_handler(self, socket_, address):
        handler = HTTPHandler(socket_, address, app=self._app)
        handler.serve_request()
