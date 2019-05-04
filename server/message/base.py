#coding: utf8

import struct
from threading import Lock
from ctypes import *
from proto import *
import proto
import logging


class MessageMapping:
    _mapping = {}
    
    @staticmethod
    def get_message_def(cmd):
        return MessageMapping._mapping.get(cmd,None)

    @staticmethod
    def set_message_handler(cmd,service):
        message_def = MessageMapping._mapping.get(cmd,None)
        if message_def == None:
            raise "message id = %d is not exist " % cmd
        message_def.service = service

    @staticmethod
    def get_message_class(cmd):
        msgdef = MessageMapping._mapping.get(cmd,None)
        if msgdef == None:
            return None
        return msgdef.msg_cls

    @staticmethod
    def init():
        if len(MessageMapping._mapping) != 0:
            return

        pb2s = []
        
        tmp = dir(proto)
        for p in tmp:

            if p.endswith("pb2"):
                pb2s.append(getattr(proto,p))
        
        for pb2 in pb2s:
            tmp = dir(pb2)
            for c in tmp :
                cls = getattr(pb2,c)

                if c.endswith("Req") or c.endswith("Resp") or c.endswith("Event"):
                    if hasattr(cls,"DEF") and hasattr(cls,"ID"):
                        MessageMapping._mapping[cls.ID] = MessageDef(None,cls)
        




class MessageUtil(object):
    _ID_BEGIN   = 0x100
    _ID_END     = 0x10000000
    _lock = Lock()
    _transaction_id = _ID_BEGIN
    @staticmethod
    def generate_transaction_id():
        #MessageUtil._lock.acquire()
        MessageUtil._transaction_id = MessageUtil._transaction_id + 1
        if MessageUtil._transaction_id >= MessageUtil._ID_END:
            MessageUtil._transaction_id = MessageUtil._ID_BEGIN
        tmp = MessageUtil._transaction_id
        #MessageUtil._lock.release()
        return tmp


HEADER = ">iiiiii"
SIZEOF_HEADER = struct.calcsize(HEADER)
class Header(Structure):
    _pack_ = 1
    _fields_ = [("length",c_int),
                ("command",c_int),
                ("transaction",c_int),
                ("user",c_int),
                ("result",c_int),
                ("route",c_int),
                ]
                
    def __init__(self,length = 0,command = 0,transaction = 0,user = 0,result = 0,route = -1,buf = None):
        self.length = length
        self.command = command
        self.transaction = transaction
        self.user = user
        self.result = result
        self.route = route
        if (buf != None):
            self.decode(buf)
   
    def encode(self):
        """
        length  = sizeof(self)
        p       = cast(pointer(self), POINTER(c_char * length))
        return p.contents.raw
        """
        return struct.pack(HEADER,self.length,self.command,self.transaction,self.user,self.result,self.route)
        
    def decode(self,buf,buf_size = None,start = 0):
        if start == None:
            start = 0
        """
        length      = sizeof(Header)
        stream      = (c_char * length)()
        stream.raw  = buf[start:start+length]
        p           = cast(stream, POINTER(Header))
        return p.contents
        """
        (self.length,self.command,self.transaction,self.user,self.result,self.route) = struct.unpack_from(HEADER,buf,start)
        return self

    def __repr__(self):
        return '<Header length={0},command={1},transaction={2},user={3},result={4},route={5} />'.format(self.length,self.command,self.transaction,self.user,self.result,self.route)
   
class ClientMessage:
    def __init__(self):
        self.header = None
        self.body = None
    
    def ok(self):
        self.header.result = 0
        
    def fail(self,code):
        self.header.result = code
    
    def encode(self):
        body_str = self.body.SerializeToString()
        self.header.length = len(body_str) + SIZEOF_HEADER
        stream = self.header.encode() + body_str 
        return stream

def get_header(buf,buf_size = None,start = 0):
    if buf_size == None:
        buf_size = len(buf)
    sizeof_header = SIZEOF_HEADER
    if buf_size < (start + sizeof_header):
        return None
    header = Header().decode(buf,start)
    logging.info('========<')
    logging.info(header)
    return header

def get_request(buf,buf_size = None,start = 0):
    print('=====>')
    print(buf,type(buf))
    if buf_size == None:
        buf_size = len(buf)
    sizeof_header = SIZEOF_HEADER
    if buf_size < (start + sizeof_header):
        return None
    header = Header().decode(buf,start)
    
    request_type = MessageMapping.get_message_class(header.command)
    sizeof_body = header.length - SIZEOF_HEADER
    if buf_size < (start + sizeof_header + sizeof_body):
        return None
    request = ClientMessage()
    request.body = request_type()
    request.body.ParseFromString(buf[start + sizeof_header : start + sizeof_header + sizeof_body])
    request.header = header
    return (request,start + sizeof_header + sizeof_body)

def get_response(buf,buf_size = None,start = 0):
    if buf_size == None:
        buf_size = len(buf)
    sizeof_header = SIZEOF_HEADER
    if buf_size < (start + sizeof_header):
        return None
    header = Header().decode(buf,start)
    
    response_type = MessageMapping.get_message_class(header.command)
    sizeof_body = header.length - SIZEOF_HEADER

    if buf_size < (start + sizeof_header + sizeof_body):
        return None
        
    response = ClientMessage()
    response.body = response_type()
    response.body.ParseFromString(buf[start + sizeof_header : start + sizeof_header + sizeof_body])
    response.header = header
    return (response,start + sizeof_header + sizeof_body)
    
def get_message(buf,buf_size = None,start = 0):
    if buf_size == None:
        buf_size = len(buf)
    sizeof_header = SIZEOF_HEADER
    if buf_size < (start + sizeof_header):
        return None
    header = Header().decode(buf,start)
    
    sizeof_body = header.length - SIZEOF_HEADER
    if buf_size < (start + sizeof_header + sizeof_body):
        return None
    
    msg_def = MessageMapping.get_message_def(header.command)
    msg_cls = msg_def.msg_cls
        
    msg = ClientMessage()
    msg.body = msg_cls()
    msg.body.ParseFromString(buf[start + sizeof_header : start + sizeof_header + sizeof_body])
    msg.header = header
    return (msg,start + sizeof_header + sizeof_body)
    

def create_client_message(cls,user = None):
    message = ClientMessage()
    message.body = cls()
    message.header = Header()
    message.header.user = -1 if user == None else user
    message.header.command = cls.DEF.Value("ID")
    message.header.transaction = -1
    message.header.result = -1
    return message
    
def create_client_event(event_cls,user = None):
    event = ClientMessage()
    event.body = event_cls()
    event.header = Header()
    event.header.user = -1 if user == None else user
    event.header.command = event_cls.DEF.Value("ID")
    event.header.transaction = -1
    event.header.result = 0
    return event

def create_response(req):
    response_type = MessageMapping.get_message_class(req.header.command + 1)
    resp = ClientMessage()
    resp.body = response_type()
    resp.header = Header()
    resp.header.user = req.header.user
    resp.header.command = req.header.command + 1
    resp.header.transaction = req.header.transaction
    resp.header.result = -1
    return resp

def create_event(event_type,user = None):
    event_cls = MessageMapping.get_message_class(event_type)
    event = ClientMessage()
    event.body = event_cls()
    event.header = Header()
    event.header.user = -1 if user == None else user
    event.header.command = event_type
    event.header.transaction = -1
    event.header.result = 0
    return event
    
def create_request(request_type):
    request_cls = MessageMapping.get_message_class(request_type)
    request = ClientMessage()
    request.body = request_cls()
    request.header = Header()
    request.header.user = -1
    request.command = request_type
    request.header.transaction = -1
    request.header.result = -1
    return request
    
def create_internal_message(msg_type):
    request_cls = MessageMapping.get_message_class(msg_type)
    request = ClientMessage()
    request.body = request_cls()
    request.header = Header()
    request.header.user = -1
    request.header.command = msg_type
    request.header.result = -1
    request.header.transaction = -1
    return request  
    
def display_message(message):
    print("------------- %s ,result :%d---------------" % (message.body.DESCRIPTOR.name,message.header.result))
    print(str(message.body)  )
    print("------------- end    ---------------")

class MessageDef:
    def __init__(self,service,msg_cls):
        self.service = service
        self.msg_id = msg_cls.ID
        self.msg_cls = msg_cls
    


def MessageID(msg_cls):
    return msg_cls.DEF.Value("ID")

