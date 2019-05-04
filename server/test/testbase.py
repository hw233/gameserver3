#coding: utf-8
'''
Created on 2012-2-20

@author: Administrator
'''
import importlib
import time,traceback
import threading
import sys,logging

from db.connect import *
from message.base import *
import socket

from proto.access_pb2 import *
from proto.game_pb2 import *
from proto.constant_pb2 import *

logging.basicConfig(level=logging.DEBUG,                        
                        format='%(threadName)s:%(asctime)s %(levelname)s %(message)s',
                        filename='./test.log',
                        #stream=sys.stdout,
                        filemode='a')


HOST = "127.0.0.1"
#HOST = "192.168.1.105"
LOGIN_PORT = 20014
ACCESS_PORT = 18004

class TestClient:
    Client = None

    def __init__(self,user_name,password):
        self.user_name = user_name
        self.password = password
        self.user = -1
        self.transaction_id = 0 
        self.buf = ""
        self.socket = None
        self.login_socket = None
        self.setup_login_socket()
        TestClient.Client = self
    
    def setup_socket(self):
        if self.socket != None:
            self.socket.close()
            self.socket = None
        try :
            self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.socket.connect((HOST,ACCESS_PORT))
        except:
            print "cant setup socket for access server"
   
   
    def setup_login_socket(self):
        if self.login_socket != None:
            self.login_socket.close()
            self.login_socket = None    
            
        try :
            self.login_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.login_socket.connect((HOST,LOGIN_PORT))
        except:
            traceback.print_exc()
            print "cant setup socket for login server"
    
    def transaction(self):
        self.transaction_id += 1
        return self.transaction_id
    
    def connect_game_server(self,userid,session,last_server):
        req = create_client_message(ConnectGameServerReq)
        req.header.user = userid
        #req.header.result = session
        #req.body.accountid = userid
        req.body.session = session
         
        self.socket.send(req.encode())
        return self.get_message()
    """
    def enter_game_server(self,userid,server_id):    
        req = create_client_message(EnterGameServerReq)
        req.header.user = userid
        #req.header.route = 300
        req.body.server_id = server_id   
        self.socket.send(req.encode())
        return self.get_message()
    """
    def login(self):
        self.setup_socket()
        req = create_client_message(LoginReq)
        req.header.user = 0
        req.body.device_id = "dasfadsfsdaf"
        req.body.password = self.password
        req.body.mobile=self.user_name
        self.login_socket.send(req.encode())
        resp = self.get_message(self.login_socket)
        self.user = resp.body.uid
        return resp
    
    def check_upgrade(self):
        self.setup_socket()
        req = create_client_message(CheckUpgradeReq)
        req.header.user = 0
        req.body.version = 1
        self.login_socket.send(req.encode())
        return self.get_message(self.login_socket)
    
        
    def test_connect_server(self):
        resp = self.login()
        display_message(resp)
        resp = self.connect_game_server(resp.body.uid,resp.body.session,1)
        display_message(resp)
        return resp
            
           
    def test_enter_server(self):
        resp = self.test_connect_server()
        #resp = self.enter_game_server(resp.header.user,1)
        display_message(resp)
        return resp
    
    def call_message(self,userid,req_cls,*args):
        req = create_client_message(req_cls)
        req.header.user = userid
        for i,field in enumerate(req_cls.DESCRIPTOR.fields):
            #print "----->setting",req.body,field.name
            if args[i] == "None":
                continue
                #setattr(req.body,field.name,None)
            elif field.type == field.TYPE_INT32:
                setattr(req.body,field.name,int(args[i]))
            elif field.type == field.TYPE_STRING:
                setattr(req.body,field.name,args[i])
            elif field.type == field.TYPE_BOOL:
                if args[i].strip().lower() == "false":
                    setattr(req.body,field.name,False)
                else:
                    setattr(req.body,field.name,True)
            elif field.type == field.TYPE_ENUM:
                setattr(req.body,field.name,int(args[i]))

        self.socket.send(req.encode())
        return self.get_message()    
        
    def call_message_by_name(self,user,proto,message,*args):
        m = importlib.import_module("proto." + proto + "_pb2")
        print proto,message,args
        cls = getattr(m,message)
        resp = self.call_message(user,cls,*args)
        display_message(resp)
        return resp        
       
    def get_messages(self, countof):
        for i in range(countof):
            yield self.get_message()
    
    def get_message(self,socket = None):
        if socket == None:
            socket = self.socket
        while True :
            data = socket.recv(4096)
            if len(data) == 0:
                continue
            self.buf += data
            result = get_message(self.buf)
            if result != None:
                self.buf = self.buf[result[1]:]
                msg = result[0]
                return msg
    
    def idle(self,func = None):  
        while True:
            msg = self.get_message()
            display_message(msg)
            if func != None:
                func(msg)
        return resp        

def test_check_upgrade():
    client = TestClient("lxk","123456")
    resp = client.check_upgrade()
    print resp.body
    print "=====> result === >",resp.header.result
    
def test_oneuser(user,password,*args):
    session = Session()
    try:
        #user = session.query(TUser).filter(TUser.id == 204).first()
        #
        client = TestClient(user,password)
        resp = client.call_message_by_name(args[0],args[1],*args[2:]) 
        print "== result ==>",resp.header.result
    finally:
        session.close()
    
    
def test_manyuser(num = None,*args):        
    if num == None:
        num = 200
    session = Session()
    try:
        users = session.query(TUser).limit(num)
    finally:
        session.close()
    
    threads = []
        
    for user in users:
        a = []
        a.append(user.name)
        a.append(user.password)
        a.extend(args)
        thread = threading.Thread(target=test_oneuser,args = a)
        thread.setDaemon(True) 
        threads.append(thread)
    
    begin_time = int(time.time())
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
        
    logging.info("users %d,time %d,",users.count(),int(time.time()) - begin_time)
        
    
if __name__ == "__main__":
    #test_oneuser(sys.argv[1],sys.argv[2],*sys.argv[3:])
    #test_manyuser(None,*sys.argv[1:])
    #test_check_upgrade()
    pass
    


