#coding: utf-8
import logging,sys,signal
import logging.config
from logging.handlers import TimedRotatingFileHandler
from threading import Lock
from services import *
import gevent
from gevent.queue import Queue
import signal
import time
import importlib

import servershare
from util.commonutil import *

from systemconfig import *
from syncevent import *
from connection import *

from db.connect import *

import redis

class ServiceItem:
    u"""
    路由表中代表服务的数据结构
    1）serviceId，服务Id
    2）serverName 所在服务的名字
    3) connection 和所在服务的连接频道对象
    """
    def __init__(self, serviceId, serverName, connection = None):
        self.serviceId = serviceId
        self.serverName = serverName
        self.connection = connection

    def __repr__(self):
        return str(self.serviceId) + ":" + self.serverName + ":" + str(self.connection)

class Server:

    u"""
    服务器对象，各个服务都通过服务器对象，可进行
    1）服务之间通讯
    2）读取配置

    服务器对象主要的功能包括
    1) 初始化
    2）读取配置
    3）装载服务
    4）实现通讯机制

    服务器维护以下关键数据结构
    1）路由表：当收到事件后需要查询路由表寻找事件的接收服务器
    2）服务表：该表保存服务数据，服务和网络的关系
    3）通讯频道表：该表保存当前的通道数据信息
    """
    def __init__(self, conf):
        self.conf = conf
        self.route = {}
        self.services = {}
        self.lock = Lock()
        self.name = self.conf.myself.name
        # create route table
        for s in self.conf.servers:
            for svcId,svc in s.services.items():
                self.route[svcId] = ServiceItem(svcId,s.name)
                #logging.info(" add service in route : %d : %s" , svcId,s.name)
        # 同步事件处理
        self.sync_handler = SyncEventHandler()
        self.factory = ConnectionFactory(self,self.name)

        self.redis = redis.Redis(*conf.get_redis_config("server_redis"))



    def setServiceConnection(self, target, connection):
        u"""
        网络层在网络协议建立后，请求服务器对象建立和对端Server的通讯频道
        1）服务器对象创建connection对象
        2）服务器对象为每个服务设置通讯connection"""

        svc_ids = []
        for k,v in self.route.items():
            if v.serverName == target:
                v.connection = connection
                svc_ids.append(v.serviceId)

        for svc in self.services.values():
            svc.on_server_connect(target,svc_ids,connection != None)

        return connection

    def getServiceConnection(self,serviceId):
        item = self.route.get(serviceId)
        if item != None:
            return item.connection
        return None

    def registeService(self,service):
        u"""服务注册函数，服务注册成功后，则可以收发消息"""
        self.services[service.serviceId] = service

    def unregisteService(self,service):
        u"""服务注销函数，服务注册成功后，则可以收发消息"""
        del self.services[service.serviceId]

    def handle_network_event(self,connection,event):
        u"""
        connection收到相应的事件后将调用服务器对象的handle方法
        服务器对象根据dstId，转发给相应的本地服务
        """
        self._dispatchEvent(event)


    def sendEvent(self,eventData,srcId=-1,dstId=-1,eventType=-1,param1=-1,param2=-1,origEvent=None):
        u"""
        可通过调用本函数，发送事件给指定服务
        1）服务器对象首先检查目标服务的位置
        2）对于远程服务，通过connection对象发送事件至对端服务器
        3）对于本地服务，则直接转发
        eventData : 发送的数据
        srcId : 源服务的标记，如origEvent不为空，则为origEvent.dstId
        dstId : 目标服务的标记，如origEvent不为空，则为origEvent.srcId
        eventType: 事件  型，如果不填写则为－1
        origEvent: 为源事件
        """
        # check whether event should be sent over network or not
        if origEvent != None:
            srcId = origEvent.dstId
            dstId = origEvent.srcId
            param1 = origEvent.param1
            param2 = origEvent.param2
        item = self.route.get(dstId)

        if item == None:
            logging.warning("Event(%s) Missing due to no this service(%d)",eventData,dstId)
            return -1

        event = Event.createEvent(srcId,dstId,eventType,param1,param2,eventData)
        # print "----->",srcId,dstId,eventType,param1,param2,item.serverName,self.name
        if item.serverName == self.name: # local event
            self._dispatchEvent(event)
        else:
            if item.connection == None:
                logging.warning("Event(event=%d,dstId=%d) Missing due to network problem",eventType,dstId)
                return
            item.connection.send(event.toStream())
        return event.tranId

    def sendSyncEvent(self,eventData,srcId=-1,dstId=-1,eventType=-1,param1=-1,param2=-1,wait = True,timeout = 10):
        item = self.route.get(dstId)
        if item == None:
            logging.warning("Event(%s) Missing due to no this service(%d)",eventData,dstId)
            return None

        event = Event.createSyncRequestEvent(srcId,dstId,eventType,param1,param2,eventData)
        helper = self.sync_handler.add_event(event)

        if item.serverName == self.name: # local event
            self._dispatchEvent(event)
        else:
            if item.connection == None:
                logging.warning("Event(%s) Missing due to network problem",eventData)
                return None
            item.connection.send(event.toStream())
        if wait:
            return helper.get_response(timeout)
        else:
            return helper

    def responseSyncEvent(self,eventData,srcId=-1,dstId=-1,eventType=-1,param1=-1,param2=-1,origEvent=None):
        if origEvent != None:
            srcId = origEvent.dstId
            dstId = origEvent.srcId
            param1 = origEvent.param1
            param2 = origEvent.param2
        item = self.route.get(dstId)

        if item == None:
            logging.warning("Event(%s) Missing due to no this service(%d)",eventData,dstId)
            return -1

        event = Event.createSyncResponseEvent(srcId,dstId,eventType,param1,param2,eventData,origEvent)
        if item.serverName == self.name: # local event
            self._dispatchEvent(event)
        else:
            if item.connection == None:
                logging.warning("Event(event=%d,dstId=%d) Missing due to network problem",eventType,dstId)
                return
            item.connection.send(event.toStream())
        return event.tranId

    def _dispatchEvent(self,event):
        u"""分发事件至本地服务的函数"""
        # logging.info("receive a event %d,%d,%d:",event.eventType,event.tranId,event.srcId)
        if event.mode == EVENT_MODE_SYNC_RESP:
            self.sync_handler.set_response(event)
            #logging.info("event %d response is ready",event.tranId)
        else:
            svc = self.services.get(event.dstId)
            if svc != None:
                try:
                    svc.dispatch(event)
                except Exception as e:
                    logging.warning("Event(%s) Missing due to queue is full",event)
            else:
                logging.warning("Event(%s) Missing due to no this service",event)


    def _dispatchTimerEvent(self,event):
        u"""分发时间事件至本地服务的函数"""
        svc = self.services.get(event.dstId)
        if svc != None:
            svc.dispatchTimerEvent(event)
        else:
            logging.warning("Event(%s) Missing due to no this service",event)

    def installServices(self):
        u"""通过配置文件的信息，启动，初始化和注册服务"""
        for server_config in self.conf.servers:
            for svcId,svc in server_config.services.items():
                code = svc.options["handler"]
                mod =  importlib.import_module(code[:code.rindex(".")])
                id = svc.id

                service = eval("mod." + code[code.rindex(".")+1:] + "(self,id)")
                if hasattr(service,"setup_route"):
                    service.setup_route()

                # setup service handler
                if server_config.name == self.conf.myself.name:
                    service.init()
                    logging.info(color.strong("install service ==> %s(%d)") % (code,id))
                    self.registeService(service)
        """
        for svcId,svc in self.conf.myself.services.items():
            code = svc.options["handler"]
            mod =  importlib.import_module(code[:code.rindex(".")])
            id = svc.id

            service = eval("mod." + code[code.rindex(".")+1:] + "(self,id)")
            logging.info("install service ==> %s(%d)" % (code,id))
            self.registeService(service)
        """

    def localBroadcastEvent(self,eventType,param1,param2,eventData):
        u"""实现本地服务广播"""
        for id,svc in self.services.items():
            evt = Event.createEvent(-1,svc.serviceId,eventType,param1,param2,eventData)
            self._dispatchEvent(evt)


    def getServerConfig(self,serverName):
        u"""获得指定服务器的配置信息"""
        for server in self.conf.servers:
            if server.name == serverName:
                return server

        return None

    def getMyselfConfig(self):
        return self.conf.myself

    def getServiceConfig(self,serviceId):
        u"""获得指定服务的配置信息"""
        return self.conf.myself.services[serviceId]

    def hasService(self,serviceName):
        for k,svc in self.conf.myself.services.items():
            if svc.service == serviceName:
                return True
        return False

    def getServiceIds(self,serviceName):
        u""" 获得指定服务名称的服务标识"""
        return [x.id for x in self.conf.services[serviceName]]

    def run(self):
        conf = self.conf
        logging.info("Setup network configuration....")
        for i in range(0,len(conf.servers)):
            if conf.servers[i].name == self.name:
                self.factory.start_server_connection(conf.servers[i].port)
                break
            else:
                self.factory.create_client_connection(self.name,conf.servers[i].ip,conf.servers[i].port)

        logging.info(color.red("System Started"))
        """
        try :   
            loop = gevent.core.loop()
            loop.run()
        except:
            pass
            #traceback.print_exc()
        """


    def stop(self):
        u"""停止各个服务"""
        for service in self.services.values():
            service.stop()

        #time.sleep(5)
        for service in self.services.values():
            self.unregisteService(service)
        logging.info(color.red("==> stop server <=="))



if __name__ == "__main__":
    import gevent
    from gevent import monkey;monkey.patch_all()

    from message.base import *
    # 加载配置proto
    MessageMapping.init()

    # 设置当前启动的服务，例如：server1
    import os
    os.chdir(sys.path[0])
    file = "system.ini"
    if len(sys.argv) > 1:
        myselfName = sys.argv[1]
    else:
        logging.error("需要输入server名字")
        sys.exit()
    
    console = False
        
    for i in range(len(sys.argv)):
        if sys.argv[i] == "-console":
            console = True
        elif sys.argv[i] == "-conf":
            file = sys.argv[i+1]        
        
            
    if console:
        logging.basicConfig(level=logging.DEBUG, \
                        format='%(asctime)s %(levelname)s %(message)s', \
                        stream=sys.stdout, \
                        filemode='a')
    else:
        log_fmt = '%(threadName)s %(asctime)s %(levelname)s %(message)s'
        formatter = logging.Formatter(log_fmt)

        log_file_handler = TimedRotatingFileHandler(filename='logs/'+myselfName, when="midnight", interval=1, backupCount=2)
        log_file_handler.setFormatter(formatter)

        logging.basicConfig(level=logging.INFO,format=log_fmt)
        logger = logging.getLogger()
        logger.addHandler(log_file_handler)
        # logging.basicConfig(level=logging.DEBUG, \
        #                 format='%(asctime)s %(levelname)s %(message)s', \
        #                 stream=sys.stdout, \
        #                 filemode='a')
        # logging.basicConfig(level=logging.DEBUG, format="%(threadName)s:%(asctime)s %(levelname)s %(message)s",
        #                filename= "./" + myselfName + ".log",filemode='a')
        # logging.config.fileConfig("log4p.conf")
                        
    logging.info("System Starting -> loading configuration %s" , file)
    conf = SystemConfig(file,myselfName)   
    logging.info("System Starting -> creating server instance and initializing")
    servershare.SERVER = server = Server(conf)
    
    logging.info("System Starting -> preparing starting " )
    logging.info("Installing Services Now")
    
    system_config = conf.system_config
    
    DATABASE.setup_user_session(*conf.get_database_config("userdb"))
    DATABASE.setup_session(*conf.get_database_config("gamedb"))    
    
    server.installServices()
    
    _queue = Queue()    
    
    def quit():
        _queue.put_nowait(None)
    
    gevent.signal(signal.SIGINT,quit)
    
    #print server.conf.services
    #print server.route
    try:
        server.run()
        _queue.get()
        server.stop()
    except:
        pass
        #traceback.print_exc()
    sys.exit()

        
    
