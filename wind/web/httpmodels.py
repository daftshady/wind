"""

    wind.web.httpmodels
    ~~~~~~~~~~~~~~~~~~~

    Provides models for http request handling.

"""

from wind import __version__
from wind.web.stream import SocketStream
from wind.exceptions import WindException
from wind.datastructures import CaseInsensitiveDict
from wind.web.codec import encode, to_str, decode_dict
from wind.compat import urlparse, parse_qsl, basestring


class HTTPStatusCode():
    """Class for HTTP status code enum"""
    # Public access fields.
    OK = '200'
    NOT_MODIFIED = '304'
    BAD_REQUEST = '400'
    FORBIDDEN = '403'
    NOT_FOUND = '404'
    METHOD_NOT_ALLOWED = '405'
    INTERNAL_SERVER_ERROR = '500'


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


class HTTPRequestContentType():
    """Only supports form content types"""
    DEFAULT = 'application/x-www-form-urlencoded'
    MULTIPART = 'multipart/form-data'


class HTTPHeader(object):
    def __init__(self, dict_=None):
        self._headers = CaseInsensitiveDict(dict_ or {})

    def add_content_length(self, value):
        self.add('Content-Length', value)

    @property
    def content_type(self):
        return self._headers.get('Content-Type', '')

    @property
    def content_length(self):
        return int(self._headers.get('Content-Length', 0))

    def get(self, key):
        return self._headers.get(key)

    def add(self, key, value):
        self._headers[key] = value

    def remove(self, key):
        self._headers.pop(key, None)

    def update(self, headers):
        self._headers.update(headers)

    def to_dict(self):
        """Returns `CaseInsensitiveDict` of headers"""
        return self._headers

    def default(self):
        """Should return `CaseInsensitiveDict`"""
        return CaseInsensitiveDict()

    def clear(self):
        self._headers = self.default()

    def __repr__(self):
        return '<HTTPHeader [%s]>' % (self._headers)


class HTTPRequestHeader(HTTPHeader):
    @property
    def if_none_match(self):
        return self._headers.get('If-None-Match', '')


class HTTPResponseHeader(HTTPHeader):
    def __init__(self, dict_=None):
        self._headers = self.default()
        self._headers.update(dict_ or {})

    def add_etag(self, etag):
        self.add('Etag', etag)

    def default(self):
        return CaseInsensitiveDict({
            'Content-Type': 'text/html; charset=UTF-8',
            'Server': 'wind ' + __version__
            })

    def to_json_content(self):
        self._headers['Content-Type'] = 'application/json; charset=UTF-8'


class HTTPRequest(object):
    """HTTP Request object"""
    def __init__(
            self, url=None, method=None, headers=None,
            params=None, body=None, auth=None, cookies=None, version=None):

        self.url = url
        if isinstance(method, basestring):
            self.method = method.lower()
        self.headers = headers or {}
        self.params = params or {}
        self.body = body
        self.auth = auth
        self.cookies = cookies
        self.version = version

    @property
    def path(self):
        return urlparse(self.url).path

    def __repr__(self):
        return '<HTTPRequest [%s]>' % (self.method)


class HTTPResponse(object):
    """HTTP Response object"""
    def __init__(
            self, request=None, reply=None, headers=None,
            cookies=None, status_code=None):

        self.request = request
        self.reply = reply
        self.headers = HTTPResponseHeader()
        self.headers.update(headers or {})
        self.cookies = cookies
        self.status_code = status_code
        if self.status_code is not None:
            self.reply = self._generate_reply(self.status_code)

    def raw(self):
        if self.reply is not None:
            separator = b'\r\n'
            raw = encode(self.reply) + separator
            for k, v in self.headers.to_dict().items():
                raw += encode(k) + b': ' + encode(v) + separator
            raw += separator
            return raw

    def _generate_reply(self, status_code):
        version = self.request.version

        def reply(list_):
            return ' '.join(list_)
        code = HTTPStatusCode
        if status_code == code.OK:
            return reply([version, code.OK, 'OK'])
        elif status_code == code.NOT_MODIFIED:
            return reply([version, code.NOT_MODIFIED, 'Not Modified'])
        elif status_code == code.BAD_REQUEST:
            return reply([version, code.BAD_REQUEST, 'Bad Request'])
        elif status_code == code.FORBIDDEN:
            return reply([version, code.FORBIDDEN, 'Forbidden'])
        elif status_code == code.NOT_FOUND:
            return reply([version, code.NOT_FOUND, 'Not Found'])
        elif status_code == code.METHOD_NOT_ALLOWED:
            return reply(
                [version, code.METHOD_NOT_ALLOWED,
                    'Method Not Allowed'])
        elif status_code == code.INTERNAL_SERVER_ERROR:
            return reply(
                [version, code.INTERNAL_SERVER_ERROR,
                    'Internal Server Error'])

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
        return '<HTTPConnection [%s]>' % (self.address[0])


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
                # XXX: Grab this exception.
                return

            # Parse first chunk of request
            separator = b'\r\n'
            meta, raw_headers = chunk.split(separator, 1)
            method, url, version = meta.split()

            # Generate Headers Dict.
            raw_headers = raw_headers.split(separator)
            raw_headers = filter(lambda x: x, raw_headers)
            headers = HTTPRequestHeader(
                dict(to_str(raw.split(b': ', 1)) for raw in raw_headers))

            # Generate `HTTPRequest`
            # Convert bytes of `url`, `method` to str so that `HTTPRequest`
            # has only request params that is `str` type.
            self._request = HTTPRequest(
                url=to_str(url), method=to_str(method),
                version=to_str(version), headers=headers)
            content_length = self._request.headers.content_length
            if content_length != 0:
                self._conn.stream.read_bytes(content_length, self._parse_body)
                return
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
            self._request.params = \
                self._parse_params(self._request)
        else:
            raise NotImplementedError

        self._handle_request()

    def _parse_params(self, request):
        """Parse params in HTTP Request and return params `Dict`

        """
        # XXX: Why params pasing methods are in `HTTPHandler`?
        try:
            if request.method == HTTPMethod.GET:
                return self._parse_get_params(request)
            elif request.method == HTTPMethod.POST:
                return self._parse_post_params(request)
            else:
                raise NotImplementedError(
                    '`_parse_params` for `%s`' % request.method)
        except ValueError:
            # XXX: We need to give more details about this error here.
            raise WindException('Error occured while parsing params')

    def _parse_get_params(self, request):
        return decode_dict(dict(parse_qsl(urlparse(request.url).query)))

    def _parse_post_params(self, request):
        if request.headers. \
                content_type.startswith(HTTPRequestContentType.DEFAULT):
            return decode_dict(dict(parse_qsl(request.body)))
        elif request.headers. \
                content_type.startswith(HTTPRequestContentType.MULTIPART):
            params = {}
            self._parse_multipart(
                request.headers.content_type, request.body, params=params)
            return decode_dict(params)

    def _parse_multipart(self, content_type, chunk, params=None):
        try:
            boundary = ''
            # Find boundary
            for type_ in content_type.split(';'):
                pairs = type_.strip().partition('=')
                if pairs[0] == 'boundary':
                    boundary = pairs[2]
            if not boundary:
                raise WindException('Multipart header has no boundary')

            separator = b'--'
            end = chunk.find(separator + boundary + separator)
            contents = [
                x for x in chunk[:end].split(separator + boundary) if x]

            # Iterate each content to parse data.
            for content in contents:
                content_end_idx = content.find(b'\r\n\r\n')
                value = content[content_end_idx+4:-2]
                elements = content[:content_end_idx].split(';')
                elements = [x.strip() for x in elements]

                # Separate contents sticked each other.
                for elem in elements:
                    if b'\r\n' in elem:
                        elements.remove(elem)
                        elements.extend(elem.split(b'\r\n'))

                content_params = CaseInsensitiveDict()

                def inject_param(raw, separator):
                    pairs = raw.split(separator)
                    # Remove unnecessary quote in param string.
                    k, v = pairs
                    if v.startswith('"') and v.endswith('"'):
                        v = v[1:-1]
                    content_params[k] = v

                for elem in elements:
                    if elem.find(': ') != -1:
                        inject_param(elem, ': ')
                        continue
                    if elem.find('=') != -1:
                        inject_param(elem, '=')
                        continue

                name = content_params.get('name')
                if content_params.get('filename'):
                    # TODO: Implement it
                    pass

                if params is not None:
                    params[name] = value

        except Exception as e:
            # TODO: Warn for invalid post body
            raise e

    def _handle_request(self):
        if self._app is not None:
            self._app.react(self._conn, self._request)

    def __repr__(self):
        return '<HTTPHandler [%s]' % (self._conn.address[0])
