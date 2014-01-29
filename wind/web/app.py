"""

    wind.web.app
    ~~~~~~~~~~~~
    
    Web application serving http requests.

"""

from wind.exceptions import ApplicationError
from wind.web.httpmodels import HTTPRequest, HTTPResponse


class WindApp(object):
    """Wind web application
    
    """
    def __init__(self, urls):
        """
        We want to implement our app usage code like this.

        """
        self._dispatcher = PathDispatcher(urls)
    
    def react(self, request):
        if not isinstance(request, HTTPRequest):
            raise ApplicationError('Can only react to `HTTPRequest`')

        path = self._dispatcher.lookup(request.url)
        if path is None:
            # No registered path. We don't need to handle this request.
            # XXX: Should expose various error states in `react`.
            # (Not only returning False stupidly)
            return False
        
        # Synchronously run halding method. (Temporarily)
        

class PathDispatcher(object):
    def __init__(self, urls):
        try:
            self._paths = []
            for handler, route, methods in urls:
                self._paths.append(Path(handler, route, methods))
        except ValueError:
            raise ApplicationError(
                'Invalid url form. 
                Form should be `List` of `(handler, route, method)` `Tuple`.')
    
    def lookup(self, url):
        for path in self._paths:
            if url in path.route:
                return path


class Path(object):
    """Contains information needed for handling HTTP request."""
    _METHODS = ['get', 'post', 'put', 'head', 'patch']

    def __init__(self, handler, route, methods, **kwargs):
        """Initialize path.
        @param handler: Method for handling HTTP request.
        @param route: URI path when serving HTTP request.
        @param methods: 
            Allowed HTTP methods. `List` of string indicating method.

        """
        if not hasattr(handler, '__call__'):
            raise ApplicationError(
                'Request handler registered to app should be method')
        self._handler = self._validate_handler(handler)
        self._route = self._process_route(route)
        self._methods = \
            [self.validate_method(method.lower()) for method in methods]
    
    @property
    def route(self):
        return self._route
    
    @property
    def methods(self):
        return self._methods

    def allowed(self, method):
        """Assume that param `method` has already converted to lowercase"""
        return method in self._methods
    
    def _validate_method(self, method):
        if not method in self._METHODS:
            raise ApplicationError("Unsupported HTTP method '%s'" % method)
    
    def _validate_handler(self, handler):
        if not hasattr(handler, '__call__'):
            raise ApplicationError(
                'Request handler registered to app should be method')

    def _process_route(self, route):
        """Process with regex in route"""
        # XXX: Not implemented yet
        return route

