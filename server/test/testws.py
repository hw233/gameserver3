from __future__ import print_function

import os,time
import geventwebsocket
import struct

from geventwebsocket.server import WebSocketServer

import proto.access_pb2

from message.base import create_client_message

def echo_app(environ, start_response):
    print('0----->')
    websocket = environ.get("wsgi.websocket")
    print('1----->',websocket)
    if websocket is None:
        return http_handler(environ, start_response)
    print('2----->')
    try:
        while True:
            print('1')
            message = websocket.receive()
            print('2')
            # m = message.decode()
            print(message,len(message))
            print('--->11')
            # print(struct.unpack('>i',message[0:4]),struct.unpack('>i',message[4:8]))
            cc = bytes(message[24:])
            print(cc,type(cc))
            ns = proto.access_pb2.ConnectGameServerReq.FromString(cc)
            print(ns.ID)

            resp = create_client_message(proto.access_pb2.ConnectGameServerResp)
            resp.body.server_time = int(time.time())
            resp.header.length = len(resp.body.SerializeToString())
            resp.header.result = 0
            resp_data = resp.encode()
            print(resp_data)
            websocket.send(resp_data)
            # print(proto.access_pb2.ConnectGameServerReq.ParseFromString(bytes(message[24:]).decode()))
            # print('--->22')

            # websocket.send(message)
        websocket.close()
    except geventwebsocket.WebSocketError as ex:
        print("{0}: {1}".format(ex.__class__.__name__, ex))


def http_handler(environ, start_response):
    if environ["PATH_INFO"].strip("/") == "version":
        start_response("200 OK", [])
        return [agent]

    else:
        start_response("400 Bad Request", [])

        return ["WebSocket connection is expected here."]


path = os.path.dirname(geventwebsocket.__file__)
agent = bytearray("gevent-websocket/%s" % (geventwebsocket.get_version()),
                  'latin-1')

print("Running %s from %s" % (agent, path))
WebSocketServer(("0.0.0.0", 8800), echo_app, debug=True).serve_forever()