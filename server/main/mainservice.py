#coding: utf-8

import json
import logging
import traceback
import gevent

import binascii
from ctypes import *
from sqlalchemy.sql import select, update, delete, insert, and_, subquery, not_, null, func, text,exists
from sqlalchemy import desc

import random,time
from datetime import datetime
from hall.messagemanager import *

from services import GameService
from message.base import *
from message.resultdef import *

from db.connect import *

from proto.game_pb2 import *
from proto.access_pb2 import *
from proto.constant_pb2 import *
from proto.struct_pb2 import *

from util.handlerutil import *

from config.var import *
from hall.hallobject import *
from dal.core import DataAccess
from hall.hallobject import VIPObject


class MainService(GameService):
    def setup_route(self):
        self.registe_command(ConnectGameServerReq,ConnectGameServerResp,self.handle_connect_game_server)
        self.registe_command(QuitGameServerReq,QuitGameServerResp,self.handle_quit_game_server)
        self.registe_command(GetServerTimeReq,GetServerTimeResp,self.handle_get_server_time)
    
    def init(self):
        self.redis = self.server.redis
        self.redis.delete("online") 
        gevent.spawn_later(3, self.sys_kick_player,self.redis)
        self.vip = VIPObject(self)
    
    def notify_offline(self,session,userid):
        req = create_client_message(OfflineReq)
        req.header.user = userid
        req.body.uid = userid
        gevent.spawn_later(0.1,self.broadcast_message,req.header,req.encode())
    def notify_online(self,session,userid,access_service):
        req = create_client_message(OnlineReq)
        req.header.user = -1
        req.body.uid = userid
        req.body.access_service_id = access_service
        gevent.spawn_later(0.1,self.broadcast_message,req.header,req.encode())
    
    @USE_TRANSACTION
    def handle_connect_game_server(self,session,req,resp,event):
        now = int(time.time())
        self.redis.hset("online",req.header.user,event.srcId)
        self.notify_online(session,req.header.user,event.srcId)
        resp.header.result = 0
        logging.info("====> User Connect Now: %d", req.header.user)

        # da = DataAccess(self.redis)
        # user_info = da.get_user(req.header.user,must_update=True)

        # # 财富榜人物上线了，广播
        # RankObject.gold_top_online_broadcast(self, session, req.header.user)
        #
        # # vip10及以上玩家登陆，全服广播
        # if self.vip.to_level(user_info.vip_exp) >= 10:
        #     MessageManager.sleep_sec(6, MessageManager.push_vip_login, *(self.redis, user_info.vip_exp, user_info.nick, user_info.id))
            # MessageManager.push_vip_login(self.redis, self.vip.to_level(user_info.vip_exp), user_info.nick, user_info.id)

        return False
    
    @USE_TRANSACTION
    def handle_get_server_time(self,session,req,resp,event):        
        resp.body.server_time = int(time.time() * 1000)
        resp.header.result = 0

    @USE_TRANSACTION
    def handle_quit_game_server(self,session,req,resp,event):
        logging.info("----> User Quit Now: %d", req.header.user)
        self.redis.hdel("online",req.header.user)

        self.notify_offline(session,req.header.user)
        return False    

    def sys_kick_player(self,r):
        while True:
            _, uid = r.brpop('sys_kick_player')
            self.redis.hdel("online",int(uid))
            self.notify_offline(None,int(uid))
            gevent.sleep(3) 
    
if __name__ == "__main__":
    pass

