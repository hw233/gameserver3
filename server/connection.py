#coding: utf-8
import gevent
from gevent.server import StreamServer
from gevent.queue import Queue

import binascii

import sys,logging
import struct
import traceback
from threading import Lock

# ����Э�飺������֮���ڽ���TCP�����Ƚ������֣��������Է���������
# ����������Ӧ��С��20���ֽ�
formatOfShakeHand = "<HH20s" # magic code + server name
lengthOfShakeHand = struct.calcsize(formatOfShakeHand)


# ������֮��ͨѶ������Ϣͷ��ʽ
# ͨѶ��ͷ���ݰ�����
#   ���� ����Ϣ���ͣ�ͬ����Ϣ���첽��Ϣ
#   ���� ��ȡֵΪ�������ݰ��ĳ���
#   ������ID��ȡֵΪ�����߷���ID
#   ������ID��ȡֵΪ�����߷���ID
#   ���ͣ�  ȡֵΪ��Ϣ����
#   ����ID��ȡֵΪ����ID���ɷ��ͷ������Զ�����
#   ���Ӳ���1��
#   ���Ӳ���2��

# mode + length + src id + dst id + type + transactionId + param1 + param2 
formatOfHeader = "<HHHHllll" 
lengthOfHeader = struct.calcsize(formatOfHeader)

# ������������Ψһ������
tid = 0
idLock = Lock()

EVENT_MODE_ASYNC        = 0 # �첽��Ϣ
EVENT_MODE_SYNC_REQ     = 1 # ͬ������
EVENT_MODE_SYNC_RESP    = 2 # ͬ����Ӧ 

def transactionId():
    global tid,idLock
    #idLock.acquire()
    tid = tid + 1
    tmp = tid
    #idLock.release()
    return tmp
    
# ������֮��ͷ���֮�䴫�ݵĶ�����
class Event:
    def __init__(self,mode,length,sid,did,eventType,tid,param1,param2,eventData):
        self.mode = mode
        self.length = length
        self.srcId = sid
        self.dstId = did
        self.eventType = eventType
        self.tranId = tid
        self.param1 = param1
        self.param2 = param2
        self.eventData = eventData
    
    def toStream(self):
        length = len(self.eventData) + lengthOfHeader 
        return struct.pack(formatOfHeader,self.mode,length, \
                    self.srcId,self.dstId,self.eventType, \
                    self.tranId,self.param1,self.param2) + self.eventData
        
    @staticmethod
    def createEvent(sid,did,eventType,param1,param2,eventData):
        length = lengthOfHeader + len(eventData)
        return Event(EVENT_MODE_ASYNC,length,sid,did,eventType,transactionId(),param1,param2,eventData)
        
    @staticmethod
    def createSyncRequestEvent(sid,did,eventType,param1,param2,eventData):
        length = lengthOfHeader + len(eventData)
        return Event(EVENT_MODE_SYNC_REQ,length,sid,did,eventType,transactionId(),param1,param2,eventData)  
    
    @staticmethod
    def createSyncResponseEvent(sid,did,eventType,param1,param2,eventData,origEvent):
        length = lengthOfHeader + len(eventData)
        return Event(EVENT_MODE_SYNC_RESP,length,sid,did,eventType,origEvent.tranId,param1,param2,eventData)    
        
    @staticmethod
    def createExistedEvent(mode,length,sid,did,eventType,tid,param1,param2,eventData):
        return Event(mode,length,sid,did,eventType,tid,param1,param2,eventData)
    
    @staticmethod
    def createEventFromStream(data):
        l = len(data)
        if l < lengthOfHeader:
            return (False,None)
        (mode,length,sid,did,eventType,tid,param1,param2) = struct.unpack_from(formatOfHeader,data)
        if l < length:
            return (False,None)
        return (True,Event.createExistedEvent(mode,length,sid,did,eventType,tid,param1,param2,data[lengthOfHeader:length]))

_close_connection = object()

class ClientConnection:
    def __init__(self,host,client_name,server_ip,port):
        self.client_name = client_name
        self.server_name = None
        self.host = host
        self.server_ip = server_ip
        self.port = port
        self.sock = None
        self.peer_address = None
        self.is_shakehand = False
        gevent.spawn(self._run)
        
        self._send_queue = Queue()
        gevent.spawn(self._run_send)
    
    def __repr__(self):
        return "ClientConnection:" + self.server_name
    
    def _run_send(self):
        _queue = self._send_queue
        # print _queue
        while True:
            msg = _queue.get()
            # print '----------------------------------------------->',msg

            if msg==_close_connection:
                break
            else:
                if self.sock != None:
                    # print 'send all'
                    self.sock.sendall(msg)
    
    def connectionMade(self):
        self.peer_address = self.sock.getpeername()
        self.send(struct.pack(formatOfShakeHand,20,7,self.client_name))
        self.buffer = "" 
        self.is_shakehand = False       

    def connectionLost(self,reason):
        self.host.setServiceConnection(self.server_name,None)
        self.peer_address = None
        self.server_name = None
    
    def dataReceived(self,data):
        if self.is_shakehand:
            self.buffer += data
            while True:     
                (result,event) = Event.createEventFromStream(self.buffer)
                if result:
                    self.buffer = self.buffer[event.length:]
                    self.host.handle_network_event(self,event)
                else:
                    return
        else:
            self.buffer += data
            if len(self.buffer) < lengthOfShakeHand:
                return
            (magicCode1,magicCode2,self.server_name) = struct.unpack(formatOfShakeHand,self.buffer[:lengthOfShakeHand])
            self.server_name = self.server_name.strip("\x00")
            self.host.setServiceConnection(self.server_name,self)
            self.buffer = self.buffer[lengthOfShakeHand:]
            self.is_shakehand = True
            logging.info("server(%s:%s) shake hand successful",self.getPeer(),self.server_name)
    
    def __del__(self):
        logging.info("client(%s) low level connection is deleted : ",self.getPeer())
        
    def getPeer(self):
        if self.peer_address != None:
            return self.peer_address
        return None
        
    def send(self,data):
        # print 'client server',data
        self._send_queue.put_nowait(data)
        
    def _run(self):
        while True:
            try :
                self.sock = gevent.socket.create_connection((self.server_ip,self.port),)
                self.connectionMade()
                while True:
                    data = self.sock.recv(1024)
                    # print 'client rece now',data
                    if data == None or len(data) == 0:
                        # peer is closed
                        break
                    self.dataReceived(data)    
            except:
                #traceback.print_exc()
                if self.sock != None:
                    self.sock.close()
                    self.sock = None
                    self.connectionLost(-1)
            finally:
                if self.sock != None:
                    self.sock.close()
                    self.sock = None
                    self.connectionLost(None)
            logging.info("server is lost %s and try it again",self.server_name)
            gevent.sleep(1)

class ServerConnection:
    def __init__(self,host,server_name):
        self.host = host
        self.server_name = server_name
        self.client_name = None
        self.sock = None
        self.is_shakehand = False
        self.peer_address = None
        
        self._send_queue = Queue()
        gevent.spawn(self._run_send)
    
    def _run_send(self):
        _queue = self._send_queue
        while True:
            msg = _queue.get()
            # print '----------------------------------------------->',msg==_close_connection

            if msg==_close_connection:
                break
            else:
                # print '====>',self.sock == None
                if self.sock != None:
                    # print 'bigban send all',msg
                    # print dir(self.sock),self.sock
                    self.sock.sendall(msg)
    
    def connectionMade(self):
        self.peer_address = self.sock.getpeername()
        self.buffer = ""
        self.is_shakehand = False

    def connectionLost(self,reason):
        self.host.setServiceConnection(self.client_name,None)
        self.peer_address = None
        self.client_name = None
    
    def dataReceived(self,data):
        # print 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',data
        if self.is_shakehand:
            self.buffer += data
            while True:     
                (result,event) = Event.createEventFromStream(self.buffer)
                if result:
                    self.buffer = self.buffer[event.length:]
                    self.host.handle_network_event(self,event)
                else:
                    return
        else:
            self.buffer += data
            if len(self.buffer) < lengthOfShakeHand:
                return
            (magicCode1,magicCode2,self.client_name) = struct.unpack(formatOfShakeHand,self.buffer[:lengthOfShakeHand])
            self.client_name = self.client_name.strip("\x00")
            self.send(struct.pack(formatOfShakeHand,magicCode1,magicCode2,self.host.name))
            self.host.setServiceConnection(self.client_name,self)
            self.buffer = self.buffer[lengthOfShakeHand:]
            self.is_shakehand = True
            logging.info("server(%s:%s) shake hand successful",self.getPeer(),self.client_name)

    def __del__(self):
        logging.info("server(%s) low level connection is deleted : ",self.getPeer())
        
    def __repr__(self):
        return "ServerConnection:" + self.client_name
        
    def getPeer(self):
        if self.peer_address != None:
            return self.peer_address
        return None
        
    def send(self,data):
        # print 'server server'

        self._send_queue.put_nowait(data)

    def handle(self,sock,address):
        try :
            self.sock = sock
            self.connectionMade()
            while True:
                # print '1111111111111111111111111111111111111111111111111'
                data = self.sock.recv(1024)
                # print 'one guy exit',data
                if data == None or len(data) == 0:
                    break
                self.dataReceived(data)    
        except:
            if self.sock != None:
                self.sock.close()
                self.sock = None
                self.connectionLost(-1)
        finally:
            if self.sock != None:
                self.sock.close()
                self.connectionLost(None)
            self._send_queue.put_nowait(_close_connection)
            
        logging.info("client is lost %s ",self.client_name)


class ConnectionFactory:
    def __init__(self,host,server_name):
        self.host = host
        self.server_name = server_name
    
    def create_client_connection(self,client_name,server_ip,port):
        return ClientConnection(self.host,client_name,server_ip,port)        
        
    def handle_server_connection(self,sock,address):
        ServerConnection(self.host,self.server_name).handle(sock,address)
        
    def start_server_connection(self,port):
        gevent.spawn(StreamServer(("0.0.0.0",port),self.handle_server_connection).serve_forever)
        
        

