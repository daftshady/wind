Wind: Super-fast web framework
==============================
Wind is microframework based on asynchronous networking library benchmarking `tornado`.

Usage sketch.

        from wind.web.app import WindApp, path
        from wind.web.httpserver import HTTPServer

        def hello_wind(request):
            return 'hello wind!'

        app = WindApp([
                path(hello_wind, route='/', methods=['get'])
                ])
        server = HTTPServer(app=app)
        server.run_simple('127.0.0.1', 7000)

This usage interfaces are made for the purpose of testing performance. (not frozen at all)

So, it may be fully revised.


Note
====
It's currently under active development. 

Because it's not released yet, using this framework in its current state is at your own risk.

I don't recommend you to use this framework now because it's in fucking unstable state.

I will update whole README when it's released.
