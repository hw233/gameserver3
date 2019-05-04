#coding: utf-8
import logging
from services import *

import struct
import binascii

import traceback
import time

# from access.accessserver import *
from access.accesswsserver import *
from message.base import *
from message.route import *
from proto.access_pb2 import *

KICKOFF_USER_CONNECTION_ID = QuitGameServerReq.DEF.Value("ID")


class AccessService(IService):
    def init(self):
        serverConfig = self.server.getServiceConfig(self.serviceId)
        print(serverConfig)
        ip = serverConfig.options["access_server_ip"]
        port = int(serverConfig.options["access_server_port"])

        # 新accessserver，只支持websocket
        access_server = AccessWSServer(self.serviceId,self.server.conf,ip,port)

        access_server.set_access_service(self)

        self.access_server = access_server

        # 原有accessserver走tcp和客户端连接
        # access_server = AccessServer(self.serviceId,self.server.conf,ip,port)
        #
        # access_server.set_access_service(self)
        # self.access_server = access_server

    # �����������������AccessService���¼�
    def onEvent(self,event):
        #logging.info("access service OnEvent User=%d event_type=%d", event.param1, event.eventType)

        # ������Ϣת�����ͻ���
        # event.param1 ����û�id������Ϣ����С�ڵ���0��������
        # event.param2 ��Ŷ�Ӧ����id�����С��0��������޶�Ӧ��Ϣ

        if event.eventType == E_SYSTEM_READY:
            logging.info("Access Service Receive System Ready Event")
            return
        elif event.eventType == KICKOFF_USER_CONNECTION_ID:
            old_connection = self.access_server.users.get(event.param1,None)
            if old_connection != None:
                logging.info("Same user is logined so kick off previous one user = %d",event.param1 )
                old_connection.close()
                return

        if event.param1 >= 0 :
            # �û���Ϣ������,event.param1 = userid and event.param2 = transaction,transaction < 0 means it's a event
            self.access_server.response_user_message(event.param1, event.param2, event.eventType,event.eventData)
        else:
            self.access_server.send_client_event(event.param1, event.param2, event.eventType,event.eventData)
            #logging.error("event param1 < -1,so event should be discarded :eventType = %d,transaction=%d",event.eventType,event.tranId)
            #return

if __name__ == "__main__":
    pass


