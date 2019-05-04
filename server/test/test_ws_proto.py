from message.base import *
from proto.access_pb2 import *

# req = create_client_message(ConnectGameServerReq)
# req.header.user = 2
# # req.header.result = session
# req.body.session = 49511
# # b'\x10\xe7\x82\x03' <class 'bytes'>
# print(req.encode(),type(req.encode()))
# edata = req.encode()
#
# print(edata)
#
# decode_data = ConnectGameServerReq
#
# qq = decode_data.ParseFromString(edata[24:])
# print(decode_data)
# print(qq)
#



cgs = ConnectGameServerReq()
cgs.session = 99999
print(cgs.DEF)

with open('test_proto.txt', 'wb') as fd:
    cc = cgs.SerializeToString()
    print(cc,type(cc))
    fd.write(cc)

print('write success~!!!!!!')

with open('test_proto.txt', 'rb') as fd2:
    ccccc = ConnectGameServerReq()
    ss = fd2.read()
    print(ss,type(ss))
    cgs2 = ccccc.FromString(ss)
    # print(cgs2,type(cgs2))
    print(cgs2.session)
# cgs2 = ConnectGameServerReq.ParseFromString(secret_cgs)
# print(cgs2)