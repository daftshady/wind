"""

    wind.web.app
    ~~~~~~~~~~~~

    Web application serving http requests.

"""

import json
import types
import traceback
from wind.log import wind_logger, LogType
from wind.compat import urlparse, parse_qsl
from wind.web.httpmodels import (
    HTTPRequest, HTTPResponse, HTTPMethod,
    HTTPStatusCode, HTTPResponseHeader)
from wind.exceptions import ApplicationError, HTTPError
from wind.web.datastructures import FlexibleDeque, CaseInsensitiveDict


def path(handler, route='', methods=[]):
    """Api method for providing intuition to url binding."""
    return Path(handler, route=route, methods=methods)


class WindApp(object):
    """Wind web application
    We expect that our app usage code will be like this, and it works now.
    This usage interface is made for the purpose of testing `performance`.
    It may be revised later.

    `hello wind!` Example::

        from wind.web.httpserver import HTTPServer
        from wind.web.app import WindApp, path, Resource

        def hello_wind(request):
            return 'hello wind!'

        class HelloResource(Resource):
            def handle_get(self):
                self.write('hello wind!')
                self.finish()

        app = WindApp([
                path(hello_wind, route='/', methods=['get']),
                path(HelloResource, route='/resource', methods=['get'])
                ])
        server = HTTPServer(app=app)
        server.run_simple('127.0.0.1', 9000)

    """

    def __init__(self, urls):
        self._dispatcher = PathDispatcher(urls)

    def react(self, conn, request):
        if not isinstance(request, HTTPRequest):
            raise ApplicationError('Can only react to `HTTPRequest`')

        path = self._dispatcher.lookup(request.path)
        if path is None:
            # No registered path. We don't need to handle this request.
            # XXX: Should expose various error states in `react`.
            # (Not only returning False stupidly)

            # Let's make a path to error.
            path = Path(self._error_handler, error_path=True)

        # Synchronously run handling method. (Temporarily)
        path.follow(conn, request)

    def _error_handler(self, request):
        raise HTTPError(HTTPStatusCode.NOT_FOUND)


class PathDispatcher(object):
    def __init__(self, urls=[]):
        try:
            self._paths = []
            self._paths.extend(urls)
        except (ValueError, TypeError) as e:
            raise ApplicationError(
                'Form should be `List` of `(handler, route, method)` `Tuple`.')

    def lookup(self, url):
        for path in self._paths:
            if url == path.route:
                return path


class Path(object):
    """Contains information needed for handling HTTP request."""

    def __init__(
        self, handler, route=None, methods=[],
        error_path=False, **kwargs):
        """Initialize path.
        @param handler:
            Method or Class inherits from `Resource`.
        @param route: URI path when serving HTTP request.
        @param methods:
            Allowed HTTP methods. `List` of string indicating method.

        """
        # if handler is not method binding, delay handler creation time
        # to time when actually serving request.
        if isinstance(handler, (types.FunctionType, types.MethodType)):
            handler = self._wrap_handler(handler)
        self._handler = handler
        self._error_path = error_path
        if not self._error_path:
            self._route = self._process_route(route)
            self._methods = \
                [self._validate_method(method.lower()) for method in methods]

    @property
    def route(self):
        return self._route

    @property
    def methods(self):
        return self._methods

    @property
    def error_path(self):
        return self._error_path

    def allowed(self, method):
        """Assume param `method` has already converted to lowercase"""
        if hasattr(self, '_methods'):
            return method in self._methods

    def follow(self, conn, request):
        """Go after the path!
        When this method is called from app, `Resource` in path will
        react to HTTP request.

        """
        if isinstance(self._handler, type):
            # Actual handler creation for user-defined `Resource`.
            self._handler(path=self).react(conn, request)
        else:
            self._handler.react(conn, request)

    def _validate_method(self, method):
        if not method in HTTPMethod.all():
            raise ApplicationError("Unsupported HTTP method '%s'" % method)
        return method

    def _wrap_handler(self, handler):
        """
        If handler is method, wraps handler with `Resource` initialized with
        this path. Return newly created `Resource` object.

        """
        if not hasattr(handler, '__call__'):
            raise ApplicationError(
                'Request handler registered to app should be callable')

        resource = Resource(path=self)
        resource.inject(method=handler)
        return resource

    def _process_route(self, route):
        """Process with regex in route"""
        # XXX: Not implemented yet
        return route


class Resource(object):
    """Class for web resource.
    May inherit this class to implement `comet` or asynchronously
    handle HTTP request.
    This class may be fully revised later in the level that does
    not break overall apis.

    Methods for the caller:

    - __init__(path=None)
    - react(conn, request)
    - inject(method=None)
    - write(chunk, left=False)
    - finish()

    Methods may be overrided:

    - initialize()
    - handle_get(request)
    - handle_post(request)
    - handle_put(request)
    - handle_delete(request)
    - handle_head(request)

    """
    def __init__(self, path=None):
        self._path = path
        self._synchronous_handler = None
        self._conn = None
        self._request = None
        self._response = None
        self._processing = False
        self._write_buffer = FlexibleDeque()
        self._write_buffer_bytes = 0
        self._response_header = HTTPResponseHeader()
        self._asynchronous = True
        self.initialize()

    def initialize(self):
        """Constructor hook"""
        pass

    def inject(self, method=None):
        if hasattr(method, '__call__') and path is not None:
            self._synchronous_handler = method

    def react(self, conn, request):
        self._processing = True
        self._conn = conn
        self._request = request

        try:
            if not self._path.allowed(request.method) \
                and not self._path.error_path:
                self._raise_not_allowed()

            if self._synchronous_handler is not None:
                # Simply run synchronous handler for test!
                chunk = self._synchronous_handler(request)
                self.write(chunk)
                self.finish()
            else:
                # Execute request handler
                getattr(self, 'handle_' + request.method)()
                if not self._asynchronous:
                    self.finish()
        except HTTPError as e:
            http_errors = \
                [HTTPStatusCode.NOT_FOUND, HTTPStatusCode.METHOD_NOT_ALLOWED]
            if e.args[0] in http_errors:
                self._generate_response(status_code=e.args[0])
                self.finish()
        except Exception as e:
            wind_logger.log(traceback.format_exc(), LogType.ACCESS)
            self._generate_response(
                status_code=HTTPStatusCode.INTERNAL_SERVER_ERROR)
            self.finish()

    def write(self, chunk, left=False):
        if isinstance(chunk, dict):
            chunk = json.dumps(chunk)
            self._response_header.to_json_content()

        if chunk:
            if left:
                self._write_buffer.appendleft(chunk)
            else:
                self._write_buffer.append(chunk)
            self._write_buffer_bytes += len(chunk)

    def finish(self):
        """Finish this resource connection by sending response"""
        if self._response is None:
            self._generate_response()
        self.write(self._response.raw(), left=True)
        self._write_buffer.gather(self._write_buffer_bytes)
        self._conn.stream.write(self._write_buffer.popleft(), None)
        self._conn.close()

        self._log_access()
        self._processing = False
        self._clear()

    def _generate_response(self, status_code=HTTPStatusCode.OK):
        # Generate response headers
        if self._write_buffer:
            self._response_header. \
                add_content_length(self._write_buffer_bytes)

        self._response = HTTPResponse(
            headers=self._response_header.to_dict(),
            status_code=status_code)

    def _clear(self):
        self._conn = self._request = None
        self._write_buffer = FlexibleDeque()
        self._write_buffer_bytes = 0
        self._response_header.clear()

    def handle_get(self):
        self._raise_not_allowed()

    def handle_post(self):
        self._raise_not_allowed()

    def handle_put(self):
        self._raise_not_allowed()

    def handle_delete(self):
        self._raise_not_allowed()

    def handle_head(self):
        self._raise_not_allowed()

    def _raise_not_allowed(self):
        raise HTTPError(HTTPStatusCode.METHOD_NOT_ALLOWED)

    def _log_access(self):
        if self._request is not None and self._response is not None:
            msg = '%s %s %s' % \
                (self._request.method.upper(), self._request.url,
                    self._response.status_code)
            wind_logger.log(msg, LogType.ACCESS)

