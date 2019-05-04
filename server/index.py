# -*- coding: utf-8 -*-
__author__ = 'Administrator'
from gevent.wsgi import WSGIServer
from main_web import app


if __name__ == '__main__':
    http_server = WSGIServer(('', 8001), app)
    http_server.serve_forever()