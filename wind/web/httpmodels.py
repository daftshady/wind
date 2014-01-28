"""

    wind.web.httpmodels
    ~~~~~~~~~~~~~~~~~~~
    
    Provides models for http request handling.

"""

from wind.web.stream import SocketStream
from wind.exceptions import WindException


class HTTPRequest(object):
    """HTTP Request object"""
    def __init__(self, 
        url=None,
        method=None,
        headers={},
        params={},
        auth=None,
        cookies=None):
        
        self.url = url
        self.method = method
        self.headers = headers
        self.params = params
        self.auth = auth
        self.cookies = cookies
    
    def __repr__(self):
        return '<HTTPRequest [%s]>' % (self.method)


class HTTPResponse(object):
    """HTTP Response object"""
    def __init__(self,
        request=None,
        headers={},
        cookies=None,
        status_code=None,
        raw=None
        ):
        self.request = request
        self.headers = headers
        self.cookies = cookies
        self.status_code = status_code
        self.raw = raw
    
    def __repr__(self):
        return '<HTTPResponse [%s]>' % (self.status_code)


class HTTPConnection(object):
    """HTTP Connection object containing stream instance"""
    def __init__(self, stream, address):
        self._stream = stream
        self._address = address
        self._close_callback = None
    
    @property
    def stream(self):
        return self._stream

    def open(self, close_callback=None):
        self._close_callback = close_callback
        self._stream.open()

    def close(self):
        self._stream.close()
        self._run_close_callback()

    def _run_close_callback(self):
        if self._close_callback is not None:
            callback = self._close_callback
            self._close_callback = None
            try:
                callback()
            except TypeError:
                raise WindException(
                    'Provide valid close callback in Connection')

    def __repr__(self):
        return '<HTTPConnection [%s]>' % (self.address)


class HTTPHandler(object):
    """Handles HTTP Requests from client.
    1. Parse header.
    2. Parse body.
    3. Send response if needed.
    
    Methods for the caller:

    - __init__(connection)
    - serve_request()

    """
    def __init__(self, socket_, address):
        """Constructor, should not be overriden"""
        self._conn = HTTPConnection(SocketStream(socket_), address)

    def serve_request(self):
        """Serves single http request with initialized connection"""
        self._conn.open(close_callback=self._conn_close_callback)
        # Start handling http request by reading header.
        self._conn.stream.read_until(b"\r\n\r\n", self._parse_header)

    def _conn_close_callback(self):
        pass

    def _parse_header(self, chunk):
        pass

    def __repr__(self):
        return '<HTTPHandler [%s]' %s (self._conn.address)

