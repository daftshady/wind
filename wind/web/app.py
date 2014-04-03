"""

    wind.web.app
    ~~~~~~~~~~~~
    
    Web application serving http requests.

"""

import json
from urlparse import urlparse, parse_qs
from wind.log import wind_logger, LogType
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
    Therefore, it may be fully revised.
    
    `hello wind!` Example::

        from wind.web.app import WindApp, path
        from wind.web.httpserver import HTTPServer

        def hello_wind(request):
            return 'hello wind!'

        app = WindApp([
                path(hello_wind, route='/', methods=['get'])
                ])
        server = HTTPServer(app=app)
        server.run_simple('127.0.0.1', 7000)

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
        # self._handler is `Resource` object.
        self._handler = self._wrap_handler(handler)
        if not error_path:
            self._route = self._process_route(route)
            self._methods = \
                [self._validate_method(method.lower()) for method in methods]
    
    @property
    def route(self):
        return self._route
    
    @property
    def methods(self):
        return self._methods

    def allowed(self, method):
        """Assume param `method` has already converted to lowercase"""
        return method in self._methods
    
    def follow(self, conn, request):
        """Go after the path!
        When this method is called from app, `Resource` in path will
        react to HTTP request.
        
        """
        self._handler.react(conn, request)

    def _validate_method(self, method):
        if not method in HTTPMethod.all():
            raise ApplicationError("Unsupported HTTP method '%s'" % method)
    
    def _wrap_handler(self, handler):
        """
        If handler is method, wraps handler with `Resource`
        Return newly created `Resource` object.
        
        """
        if not hasattr(handler, '__call__'):
            raise ApplicationError(
                'Request handler registered to app should be callable')

        resource = Resource(path=self)
        resource.inject(handler)
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

    Methods may be overrided

    - handle_get(request)
    - handle_post(request)
    - handle_put(request)
    - handle_delete(request)
    - handle_head(request)

    """
    def __init__(self, path=None):
        self._path = path
        self._synchronous = path is not None
        self._synchronous_handler = None
        self._conn = None
        self._request = None
        self._response = None
        self._processing = False
        self._write_buffer = FlexibleDeque()
        self._write_buffer_bytes = 0
        self._response_header = HTTPResponseHeader()
        self.initialize()

    def initialize(self):
        """Constructor hook"""
        pass

    def inject(self, method):
        if hasattr(method, '__call__') and self._synchronous:
            self._synchronous_handler = method
    
    def react(self, conn, request):
        self._processing = True
        self._conn = conn
        self._request = request
        if self._synchronous_handler is not None:
            # Simple run synchronous handler for test!
            try:
                chunk = self._synchronous_handler(request)
                self.write(chunk)
                self.finish()
            except HTTPError as e:
                if e.args[0] == HTTPStatusCode.NOT_FOUND:
                    self._generate_response(status_code=e.args[0])
                    self.finish()
            except Exception as e:
                # TODO: Log for warning
                self._generate_response(
                    status_code=HTTPStatusCode.INTERNAL_SERVER_ERROR)
                self.finish()
            return
    
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

    def handle_get(self, request):
        pass

    def handle_post(self, request):
        pass
    
    def handle_put(self, request):
        pass

    def handle_delete(self, request):
        pass

    def handle_head(self, request):
        pass
    
    def _log_access(self):
        if self._request is not None and self._response is not None:
            msg = '%s %s %s' % \
                (self._request.method.upper(), self._request.url, 
                    self._response.status_code)
            wind_logger.log(msg, LogType.ACCESS)

