"""

    wind.web.app
    ~~~~~~~~~~~~
    
    Web application serving http requests.

"""

from urlparse import urlparse, parse_qs
from wind.exceptions import ApplicationError
from wind.web.httpmodels import (
    HTTPRequest, HTTPResponse, HTTPMethod, HTTPStatusCode)
from wind.web.datastructures import FlexibleDeque, CaseInsensitiveDict


class WindApp(object):
    """Wind web application
    
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
            return False
        
        # Synchronously run handling method. (Temporarily)
        path.follow(conn, request)
 

class PathDispatcher(object):
    def __init__(self, urls):
        try:
            self._paths = []
            for handler, route, methods in urls:
                self._paths.append(Path(handler, route, methods))
        except (ValueError, TypeError) as e:
            raise ApplicationError(
                'Form should be `List` of `(handler, route, method)` `Tuple`.')
    
    def lookup(self, url):
        for path in self._paths:
            if url in path.route:
                return path


class Path(object):
    """Contains information needed for handling HTTP request."""

    def __init__(self, handler, route, methods, **kwargs):
        """Initialize path.
        @param handler: 
            Method or Class inherits from `Resource`.
        @param route: URI path when serving HTTP request.
        @param methods: 
            Allowed HTTP methods. `List` of string indicating method.

        """
        # self._handler is `Resource` object.
        self._handler = self._wrap_handler(handler)
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
        from types import FunctionType
        if not hasattr(handler, '__call__'):
            raise ApplicationError(
                'Request handler registered to app should be callable')

        if isinstance(handler, FunctionType):
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
        self._processing = False
        self._write_buffer = FlexibleDeque()
        self._write_buffer_bytes = 0
        self._response_header = CaseInsensitiveDict()
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
            except TypeError as e:
                #raise ApplicationError(e)
                raise
            return
    
    def write(self, chunk, left=False):
        # TODO: Consider json write
        if chunk:
            if left:
                self._write_buffer.appendleft(chunk)
            else:
                self._write_buffer.append(chunk)
            self._write_buffer_bytes += len(chunk)

    def finish(self):
        """Finish this resource connection by sending response"""
        # Generate response headers
        if self._write_buffer:
            self._append_response_header(
                'Content-Length', self._write_buffer_bytes)

        response = HTTPResponse(
            headers=self._response_header,status_code=HTTPStatusCode.OK)
        self.write(response.raw(), left=True)
        self._write_buffer.gather(self._write_buffer_bytes)
        self._conn.stream.write(self._write_buffer.popleft(), None)
        self._conn.close()

        self._processing = False
        self._clear()
    
    # HTTP response header related methods
    def _append_response_header(self, key, value):
        self._response_header[key] = value
    
    def _clear(self):
        self._conn = self._request = None
        self._write_buffer = FlexibleDeque()
        self._write_buffer_bytes = 0
        self._response_header = CaseInsensitiveDict()

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

