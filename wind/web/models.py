"""

    wind.web.models
    ~~~~~~~~~~~~~~~
    
    Provides models for http request handling.

"""

class Request(object):
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


class Response(object):
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
