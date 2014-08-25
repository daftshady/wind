#!/usr/bin/env python
# Copyright (c) 2014 Park Ilsu. See LICENSE for details.

from wind.web.httpserver import HTTPServer
from wind.web.app import WindApp, path, Resource


class HelloResource(Resource):
    def handle_get(self):
        self.write('Hello')
        self.finish()


def main():
    app = WindApp([
        path(HelloResource, route='/', methods=['get'])
    ])

    server = HTTPServer(app=app)
    server.run_simple('0.0.0.0', 9000)


if __name__ == '__main__':
    main()
