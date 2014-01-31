"""

    wind.web.httpmodels
    ~~~~~~~~~~~~~~~~~~~
    
    Provides models for http request handling.

"""

# It doesn't guarantee backward compatibility.
from urlparse import urlparse, parse_qsl

from wind.web.stream import SocketStream
from wind.exceptions import WindException
from wind.web.datastructures import CaseInsensitiveDict


class HTTPStatusCode():
    """Class for HTTP status code enum"""
    # Public access fields.
    SUCCESS = 200
    BAD_REQUEST = 400
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    INTERNAL_SERVER_ERROR = 500


class HTTPMethod():
    """Class for HTTP methods enum"""
    # Public access fields.
    GET = 'get'
    POST = 'post'
    PUT = 'put'
    HEAD = 'head'
    DELETE = 'delete'
    
    @staticmethod
    def all():
        return [
            HTTPMethod.GET, HTTPMethod.POST, HTTPMethod.PUT, 
            HTTPMethod.HEAD, HTTPMethod.DELETE
            ]


class HTTPHeader(object):
    def __init__(self, dict_={}):
        self._headers = CaseInsensitiveDict(dict_)

    @property
    def content_length(self):
        return int(self._headers.get('content-length', 0))


class HTTPRequest(object):
    """HTTP Request object"""
    def __init__(self, 
        url=None,
        method=None,
        headers=None,
        params={},
        body=None,
        auth=None,
        cookies=None):
        
        self.url = url
        if isinstance(method, basestring):
            self.method = method.lower()
        self.headers = headers 
        self.params = params
        self.body = body
        self.auth = auth
        self.cookies = cookies
    
    @property
    def path(self):
        return urlparse(self.url).path

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
    
    @property
    def address(self):
        return self._address

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

    Inner callbacks:

    - _parse_header(chunk)
    - _parse_body(chunk)
    - _parse_params(request)

    """
    def __init__(self, socket_, address, app=None):
        """Constructor, should not be overriden"""
        self._conn = HTTPConnection(SocketStream(socket_), address)
        self._app = app
        self._request = None

    def serve_request(self):
        """Serves single http request with initialized connection"""
        self._conn.open(close_callback=self._conn_close_callback)
        # Start handling http request by reading header.
        self._conn.stream.read_until(
            b"\r\n\r\n", self._parse_header, include=True)

    def _conn_close_callback(self):
        pass

    def _parse_header(self, chunk):
        try:
            if not chunk:
                # XXX: Grap this exception.
                return

            # Parse first chunk of request 
            separator = b'\r\n'
            meta, raw_headers = chunk.split(separator, 1)
            method = meta.split()[0]
            url = meta.split()[1]

            # Generate Headers Dict.
            raw_headers = raw_headers.split(separator)
            raw_headers = filter(lambda x:x, raw_headers)
            headers = HTTPHeader(
                dict([raw.split(': ', 1) for raw in raw_headers]))

            # Generate `HTTPRequest`
            self._request = HTTPRequest(
                url=url, method=method, headers=headers)
            
            content_length = self._request.headers.content_length
            if content_length != 0:
                self._conn.stream.read_bytes(content_length, self._parse_body)
            else:
                if self._request.method == HTTPMethod.GET:
                    self._request.params = self._parse_params(self._request)
            
            self._handle_request()

        except IndexError:
            raise WindException('Invalid header on incoming HTTP request')
    
    def _parse_body(self, chunk):
        if self._request is None:
            raise WindException(
                '_parse_body is not spawned from _parse_header')
        
        self._request.body = chunk
        if self._request.method == HTTPMethod.POST:
            self._request.params = self._parse_params(self._request)
        else:
            raise NotImplementedError
        
    def _parse_params(self, request):
        """Parse params in HTTP Request and return params `Dict` 
        
        """
        try:
            if request.method == HTTPMethod.GET:
                return dict(parse_qsl(urlparse(request.url).query))
            elif request.method == HTTPMethod.POST:
                return dict(parse_qsl(request.body))
            else:
                raise NotImplementedError(
                    '`_parse_params` for `%s`' % request.method)
        except ValueError:
            # XXX: We need to give more details about this error here.
            raise WindException('Error occured while parsing params')
            

    def _handle_request(self):
         if self._app is not None:
            self._app.react(self._conn, self._request)
       
    def __repr__(self):
        return '<HTTPHandler [%s]' % (self._conn.address[0])
