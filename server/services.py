#coding: utf-8
import gevent
from gevent.queue import Queue

import struct
import logging
import time
from random import randint
import random
import traceback

from message.base import *
from message.route import *


# ����Ϊ���з�����Ļ���
# ÿ������������һ���������߳��У�ϵͳ��֤onEvent���̰߳�ȫ�ĺ���

E_SYSTEM_READY = 99999

_quit_svc = object()

class BaseService:
    # ���캯����һ��������û�������Ҫ�����Լ��Ĺ��캯������ͨ�������init()����ʵ�ֳ�ʼ������
    # ��������Լ��Ĺ��캯��������Ҫ���ñ����__init__����
    # serverΪ����������ʵ��
    # serviceIdΪ����ķ����ʶ
    # qSizeΪ��Ϣ���еĳ��ȣ������ö��г��ȵ���Ϣ����������
    def __init__(self,server,serviceId,thread_num = 1):
        self.server = server 
        self.queue = Queue()
        self.serviceId = serviceId
        for _ in range(thread_num):
            gevent.spawn(self._run)
        #self.init()

    def on_server_connect(self,server_name,service_ids,is_connect):
        pass

    # ���������յ��¼��󣬻���ø÷������¼����������
    # ������ʱ���ܴ���µ���Ϣ�����׳��쳣
    # �û��������ض���÷���
    def dispatch(self,event):
        try:
            # logging.info("queue size:%s",self.queue.qsize())
            self.queue.put_nowait(event)
        except:
            logging.exception("�������쳣")
        #logging.info("is full: %s",self.queue.full())
    
        
    # ��ʼ���������������ͨ�����¶���÷�������ɳ�ʼ������
    def init(self):
        pass    

    def sendEvent(self,eventData,dstId=-1,eventType=-1,param1=-1,param2=-1):
        self.server.sendEvent(eventData,self.serviceId,dstId,eventType,param1,param2)

    # �û�������Ҫ���¶���÷�����ʵ���Լ����߼�
    def onEvent(self,event):
        pass
    
    def stop(self):
        pass

    def _run(self):
        while True:
            try:
                msg = self.queue.get()
                # print 'base server get msg now',msg
                if msg == _quit_svc:
                    break
                self.onEvent(msg)
            except:
                logging.exception("�¼��������쳣(onEvent)")


    def getServiceConfig(self):
        return self.server.getServiceConfig(self.serviceId)

    def getServerConfig(self):
        return self.server.getMyselfConfig()

    def getConfigOption(self,key,default_value):
        options = self.getServiceConfig().options
        if key in options:
            return options[key]
        else:
            return default_value

    # ת���û��¼�����������
    def forward_message(self,header,data):
        dst_id = ROUTE.get_any_service(self.server,header)
        if dst_id == None:
            logging.info("No service handler for %d" % header.command)
            return
        self.server.sendEvent(data,self.serviceId,dst_id,header.command,header.user,header.transaction)
    
    def forward_message_directly(self,dst_id,event_type,user,transaction,data):    	
        self.server.sendEvent(data,self.serviceId,dst_id,event_type,user,transaction)
        
    def forward_proxy_message(self,src_id,dst_id,event_type,user,transaction,data):
        self.server.sendEvent(data,src_id,dst_id,event_type,user,transaction)
    
    # �㲥���¼���������Ϣ�����з��� 
    def broadcast_message(self,header,data):
        ids = ROUTE.get_all_service(self.server,header)
        if ids == None:
            logging.info("No service handler for %d" % header.command)
            return
        for dst_id in ids:
            self.server.sendEvent(data,self.serviceId,dst_id,header.command,header.user,header.transaction)

    def send_client_event(self,access_server_id,user,event_type,data):
        #pkg = struct.pack("llh" + str(len(data)) + "s",user,-1,event_type,data)
        #self.server.redis.lpush("queue"+str(access_server_id),pkg)
        self.server.sendEvent(data,self.serviceId,access_server_id,event_type,user,-1)


class IMultiTaskService(BaseService):
    def __init__(self,server,serviceId,thread_num = 5):
        self.event_handlers = {}
        BaseService.__init__(self,server,serviceId,thread_num)
        

class GameService(IMultiTaskService):
    def registe_command(self,req,resp,handler):
        MessageMapping.set_message_handler(req.DEF.Value("ID"),self.__class__.__name__)
        self.event_handlers[req.ID] = handler

    def registe_handler(self,req,resp,handler):
        self.event_handlers[req.ID] = handler
    
    def onEvent(self, event):
        event_type = event.eventType
        if event_type not in self.event_handlers:
            logging.info(" No valid event handler for event:%d", event_type)
            return 
        handler = self.event_handlers[event_type]
        try :
            # print 'song handler now ',handler,event.srcId,event.dstId
            handler(event)
        except:
            logging.exception("Error Is Happend for event %d", event_type)    

    

class IService(BaseService):
    def __init__(self,server,serviceId,qSize = 1024):
        BaseService.__init__(self,server,serviceId,qSize)
        

        
class TestService(IService):
    def init(self):
        self.count = 1
        
    def onEvent(self,event):
        self.count = self.count + 1
        event_data = "Hi,Hello TestClient : %d" % self.count
        if event.srcId >= 0:
            self.server.sendEvent(event_data,self.serviceId,event.srcId,100,event.param1,event.param2)
        