#coding: utf-8

import gevent
from gevent import monkey;monkey.patch_all()

import redis
import json

from gevent.pool import Pool
from gevent.server import StreamServer
from gevent.queue import Queue

from threading import Lock
import binascii
import logging
import traceback, copy
import time
from ctypes import *

from message.base import *
from message.resultdef import *
from proto.access_pb2 import *
from proto.hall_pb2 import *

from config import var

LOGOUT_RESP_ID = LogoutResp.DEF.Value("ID")
CONNECT_GAME_SERVER_REQ_ID = ConnectGameServerReq.DEF.Value("ID")
KICKOFF_USER_CONNECTION_ID = QuitGameServerReq.DEF.Value("ID")
HEARTBEAT_ID = HeartbeatReq.DEF.Value("ID")


CLIENT_TIMEOUT = 600
MAX_CONNECTIONS = 400
LOOP_PERIOD = 60

_close_client = object()

class AccessClientConnection(object):
    _ID_BEGIN = 0x40000000
    _ID_END = 0x90000000
    def __init__(self,access_server,sock):
        self.access_server = access_server
        self.user = -1
        self.sock = sock
        self.is_safe = False
        self.transactions = {}
        self._transaction = AccessClientConnection._ID_BEGIN
        
        self.login_time = 0
        self.heartbeat_time = 0
        self.session = None
        self.connection_id = "%d-%d" % (self.access_server.access_service.serviceId,time.time())
        
        self._lock = Lock()
        self._receive_queue = Queue()
        self._send_queue = Queue()
        self._closed = False
        
        gevent.spawn(self._run_receive)
        gevent.spawn(self._run_send)
        
    def generate_transaction_id(self):
        #self._lock.acquire()
        self._transaction += 1
        if self._transaction >= AccessClientConnection._ID_END:
            self._transaction = AccessClientConnection._ID_BEGIN
        tmp = self._transaction
        #self._lock.release()
        return tmp
    
    def send(self,msg):
        self._send_queue.put_nowait(msg)
    
    def handle_message(self,msg):
        self._receive_queue.put_nowait(msg)    
    
    def _run_receive(self):
        _queue = self._receive_queue
        while True:
            msg = _queue.get()
            if msg == _close_client:
                self.sock.close()
                break
            try :
                self.on_message(msg)
            except:
                traceback.print_exc()
    
    def _run_send(self):
        _queue = self._send_queue
        begin = 0
        while True:
            msg = _queue.get()
            if msg == _close_client:
                self.sock.close()
                break
            if var.DEBUG:
                request,idx = get_message(msg)
                logging.info("<== send message back: cmd=%d | user=%d | result=%d " %(request.header.command,self.user,request.header.result))

            try :
                self.sock.sendall(msg)
            except:
                traceback.print_exc()

            if var.DEBUG:
                logging.info("message body sent :\n" + str(request.body))

    def close(self):
        if self._closed:
            return 
        self.access_server.users.pop(self.user,None)
        self.handle_message(_close_client)
        self.send(_close_client)    
        self._closed = True
        
        req = create_client_message(QuitGameServerReq,self.user)
        self.access_server.access_service.forward_message(req.header,req.encode())
        
        # ���session��������������Ϣ���û������������ӳ����Ϣ
        if self.session != None and self.access_server.redis.hget("sessions",self.user) == self.session:
            self.access_server.redis.hdel("sessions",self.user)
        if self.access_server.redis.hget("server" + str(self.access_server.server_id),self.user) == self.connection_id:
            self.access_server.redis.hdel("server" + str(self.access_server.server_id),self.user)
            self.access_server.redis.hdel("mapping",self.user)
        
        self.user = -1
            
    def connect_server(self,client_message):
        req,index = get_request(client_message.data)
                
        session = int(self.access_server.redis.hget("sessions",req.header.user))
        
        if session == req.body.session:
            self.heartbeat_time = int(time.time())
            self.is_safe = True
            self.user = req.header.user
            self.login_time = int(time.time())
            self.session = session

            old_server_id = self.access_server.redis.hget("mapping",req.header.user)
            if old_server_id != None and int(old_server_id) != self.access_server.server_id:
                old_server_id = int(old_server_id)
                self.access_server.access_service.forward_message_directly(old_server_id,KICKOFF_USER_CONNECTION_ID,req.header.user,-1)
            old_connection = self.access_server.users.get(req.header.user,None)
            if old_connection != None:
                logging.info("Same user is logined so kick off previous one user = %d",req.header.user )
                # 断开前需要发事件通知客户端
                event = create_client_event(NotificationEvent)
                event.header.user = req.header.user
                event.header.result = 0
                event.body.type = 5 # N_KICK_OFF = 5;
                old_connection.send(event.encode())
                old_connection.close()
            self.access_server.users[req.header.user] = self

            self.access_server.redis.hset("server" + str(self.access_server.server_id),req.header.user,self.connection_id)
            self.access_server.redis.hset("mapping",req.header.user,self.access_server.server_id)

            self.access_server.access_service.forward_message(client_message.header,client_message.data)

            resp = create_client_message(ConnectGameServerResp,req.header.user)
            resp.header.result = 0
            resp.body.server_time = int(time.time())
            self.send(resp.encode())
        else:
            logging.info("login is failure ,so close it !" )
            resp = create_client_message(ConnectGameServerResp,req.header.user)
            resp.header.result = -1
            self.send(resp.encode())
            self.close()    
    
    def on_message(self,client_message):
    	#request,idx = get_request(client_message.data)

        if var.DEBUG:
            request,idx = get_request(client_message.data)
            logging.info("==> receive message : cmd=%d | user=%d | route=%d " %(client_message.header.command, \
                                                    client_message.header.user,client_message.header.route))
            logging.info("message body:\n" + str(request.body))

        if client_message.header.command == HeartbeatReq.ID:
            self.heartbeat_time = int(time.time())
            resp = create_client_message(HeartbeatResp,client_message.header.user)
            resp.header.result = 0
            self.send(resp.encode())
            return

        
        if not self.is_safe:
            if client_message.header.command != CONNECT_GAME_SERVER_REQ_ID:
                logging.info("the first message must be ConnectGamerServer , user = %d" + str(client_message.header.user))
                self.close()
            else:
                self.connect_server(client_message)
                
            return
        else:
            if client_message.header.command == CONNECT_GAME_SERVER_REQ_ID:
                self.connect_server(client_message)
                return 
                        
        result = self.on_safe_message(client_message)
        
        if result < 0:
            logging.info("result(%d) is failure and user = %d, it should not happen",result,client_message.header.user)
            self.close()
            
    def on_safe_message(self,client_message):
        access_server = self.access_server
        if client_message.header.user in access_server.blacklist_users:
            logging.info("user(%d) in access_server.blacklist, so delete user in access_server.users" % client_message.header.user)
            access_server.users.pop(client_message.header.user)
        # ����Ƿ�ȫ��¼��
        if (client_message.header.user not in access_server.users or client_message.header.user != self.user):
            logging.info("it should not happen,then close connection")
            self.close()
            return -1
            
        #logging.info("receive a client message :%d",client_message.header.command)
        self.transactions[client_message.header.transaction] = client_message
        # ת������������
        # �޸�����ʱ��
        self.heartbeat_time = int(time.time())
        access_server.access_service.forward_message(client_message.header,client_message.data)
        return 0


class AccessRawMessage:
    def __init__(self,header,data):
        self.header = header
        self.data = data
        self.receive_time = time.time()
        
    def get_message_data(self):
        return self.data 

        
class AccessServer:
    def __init__(self,server_id,conf,ip,port):
        self.conf = conf
        self.port = port
        self.server_id = int(server_id)
        # ��������Ȩ���û���Ϣ
        self.users = {}
        self.blacklist_users = []
       
        self.lock = Lock()        
        self.access_service = None
        pool = Pool(2000)
        
        self.redis = redis.Redis(*conf.get_redis_config("access_redis"))
        
        self.redis.delete("server" + str(self.server_id))
        self.redis.delete("queue" + str(self.server_id))
        self.redis.hmset("server" + str(self.server_id),{"id":self.server_id,"ip":ip,"port":port})
        self.blacklist_users = [int(x) for x in self.redis.hkeys('sys_blacklist')]
        
        gevent.spawn_later(20,self.check_connection)
        gevent.spawn(StreamServer(("0.0.0.0",self.port),self.handle_access_socket,spawn = pool).serve_forever)
        gevent.spawn(self.handle_queue)
        gevent.spawn_later(3,self.kick_user,self.redis)
        
    def handle_access_socket(self,sock,address):
        logging.info("a client connecting now .....")
        buffer = ""
        conn = AccessClientConnection(self,sock)
        try :
            while True:
                header = get_header(buffer,len(buffer),0)
                if header == None or header.length > len(buffer):
                    data = sock.recv(1024)
                    if data == None or len(data) == 0:
                        #logging.info("disconnected now ---> no data")
                        break
                    
                    buffer += data
                    continue
                if header.length < SIZEOF_HEADER:
                    logging.info("Error: message length = %d, its length is less than SIZEOF_HEADER", header.length)
                    break
                msg = AccessRawMessage(header,buffer[:header.length])
                #logging.info("receive a message ==>" + str(msg))
                buffer = buffer[header.length:]
                conn.handle_message(msg)
        except:
            # logging.info('except******************************>')
            # traceback.print_exc()
            pass
        finally:
            # logging.info('finally******************************>')
            conn.close()          
        

    def set_access_service(self, service):
        global MAX_CONNECTIONS
        self.access_service = service
        MAX_CONNECTIONS = int(service.getConfigOption("max_connections",1000))
        
    
    
        
    # ������Ӧ�û��¼����ͻ���            
    def response_user_message(self, user, transaction,event_type, data):
        connection = self.users.get(user,None)
        if connection == None:
            logging.info("user %d is not exist:event_type = %d",user,event_type)
            return 
            
        if transaction in connection.transactions:
            client_message = connection.transactions.pop(transaction,None)
            connection.send(data)
        else:
            connection.send(data)
            return 
        
        if event_type == LOGOUT_RESP_ID:
            connection.close()

    def send_client_event(self,user,transaction,event_type,data):
        connection = self.users.get(user,None)
        if connection == None:
            logging.info("user %d is not exist:event_type = %d",user,event_type)
            return

        connection.send(data)

    def handle_queue(self):
        while True:
            try:
                #data = self.redis.brpoplpush("queue" + str(self.server_id),"queue_debug")
                _,data = self.redis.brpop("queue" + str(self.server_id))

                user,transaction,event_type = struct.unpack_from("llh",data)
                
                msg = data[struct.calcsize("llh"):]
                    
                connection = self.users.get(user,None)
                if connection == None:
                    logging.info("user %d is not exist:event_type = %d",user,event_type)
                    continue 
                    
                connection.send(msg)
                
                if event_type == LOGOUT_RESP_ID:
                    self.disconnect_client(user)   
            except:
                traceback.print_exc()
                pass
                              
        
    # �Ͽ��Ѿ���Ȩ�Ŀͻ��˵�����    
    def disconnect_client(self, user):
        connection = self.users.pop(user,None)
        if connection != None:
            connection.close()
    
    def check_connection(self):
        HEARTBEAT_TIME = 30

        while True:
            now = time.time()
            for user, connection in self.users.items():
                no_error = False
                for transaction, client_message in connection.transactions.items():
                    if now - client_message.receive_time > LOOP_PERIOD:
                        # ������쳣��Ϣ����ֱ�Ӷ���
                        connection.transactions.pop(transaction,None)
                        logging.error(" user %d,message %d ,transaction %d is timeout",
                            client_message.header.user, client_message.header.command, client_message.header.transaction)
                        #self.disconnect_client(client_message.header.user)
                        break
                else:
                    no_error = True

            for user, connection in self.users.items():
                if now - connection.heartbeat_time >= 30:
                    logging.error(" user %d has no heartbeat ,so disconnect it",user)
                    #self.disconnect_client(user)
            gevent.sleep(LOOP_PERIOD)

    def kick_user(self,r):
        while True:
            _, suid = r.brpop('sys_kick')
            kick_user = json.loads(suid)
            if kick_user['cancel'] > 0:
                self.blacklist_users.remove(kick_user['uid'])
            else:
                self.blacklist_users.append(kick_user['uid'])
                self.disconnect_client(kick_user['uid'])
            gevent.sleep(3)