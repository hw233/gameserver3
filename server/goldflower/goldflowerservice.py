#coding: utf-8

import json
import logging
import traceback
import socket
import gevent
import binascii
from ctypes import *

import random,time
from datetime import datetime
from datetime import date as dt_date
from datetime import time as dt_time

from hall.hallobject import *
from config.vip import *

from services import GameService
from message.base import *
from message.resultdef import *

from proto.constant_pb2 import *
from proto.access_pb2 import *
from proto.game_pb2 import *

from db.connect import *

from util.handlerutil import *
from util.commonutil import *

from goldflower.table import *
from goldflower.game import *
from dal.core import *


class GoldFlowerService(GameService):
    def setup_route(self):
        self.registe_command(LeaveTableReq,LeaveTableResp,self.handle_leave_table)
        self.registe_command(SetPlayerReadyReq,SetPlayerReadyResp,self.handle_set_player_ready)
        self.registe_command(BetActionReq,BetActionResp,self.handle_bet_action)
        self.registe_command(KickOtherReq,KickOtherResp,self.handle_kick_other)

    def init(self):
        self.registe_handler(SitTableReq,SitTableResp,self.handle_sit_table)
        self.registe_handler(LeaveTableInternalReq,LeaveTableInternalResp,self.handle_leave_table_internal)
        self.registe_handler(OfflineReq,OfflineResp,self.handle_offline)
        self.registe_handler(UpdateTablePlayerReq,UpdateTablePlayerResp,self.handle_update_table_player)


        self.room_id = self.serviceId
        self.table_manager = TableManager(self)
        self.redis = self.server.redis

        keys = self.redis.keys("u1*")
        for k in keys:
            self.redis.delete(k)


    def get_table(self,user):
        return self.table_manager.get_player_table(user)


    @USE_TRANSACTION
    def handle_sit_table(self,session,req,resp,event):
        table = None
        self.table_manager.lock.acquire()
        try :
            result,table = self.table_manager.sit_table(req.body.table_id, \
                    req.header.user,event.srcId, req.body.not_tables, req.body.table_type)

            if result < 0:
                resp.header.result = result
                return
            table.get_proto_struct(req.header.user,resp.body.table)
            resp.body.room_id = self.room_id
            resp.header.result = 0
        finally :
            self.table_manager.lock.release()


    @USE_TRANSACTION
    def handle_leave_table(self,session,req,resp,event):
        table = self.get_table(req.header.user)
        if table == None:
            resp.header.result = RESULT_FAILED_INVALID_TABLE
            return

        table.lock.acquire()
        try:
            table.remove_player(req.header.user)
            resp.header.result = 0
        finally:
            table.lock.release()


    @USE_TRANSACTION
    def handle_leave_table_internal(self,session,req,resp,event):
        table = self.get_table(req.header.user)
        if table == None:
            resp.header.result = RESULT_FAILED_INVALID_TABLE
            return False

        table.lock.acquire()
        try:
            table.remove_player(req.header.user)
        finally:
            table.lock.release()
        return False

    @USE_TRANSACTION
    def handle_offline(self,session,req,resp,event):
        table = self.get_table(req.header.user)
        if table == None:
            resp.header.result = RESULT_FAILED_INVALID_TABLE
            return False

        table.lock.acquire()
        try:
            table.player_disconnected(req.body.uid)
        finally:
            table.lock.release()
        return False


    @USE_TRANSACTION
    def handle_set_player_ready(self,session,req,resp,event):
        table = self.get_table(req.header.user)
        if table == None:
            resp.header.result = RESULT_FAILED_INVALID_TABLE
            return False

        table.lock.acquire()
        try :
            result = table.game.set_ready(req.header.user)
            resp.header.result = result
        finally:
            table.lock.release()

    @USE_TRANSACTION
    def handle_bet_action(self,session,req,resp,event):
        table = self.get_table(req.header.user)
        if table == None:
            resp.header.result = RESULT_FAILED_INVALID_TABLE
            return False

        game = table.game
        table.lock.acquire()
        try :
            uid = req.header.user
            if game.start_time <= 0:
                resp.header.result = RESULT_FAILED_NOT_START
                return

            if req.body.action == SEE_POKER:
                pokers = game.see_poker(uid)
                if pokers == None:
                    resp.header.result = -1
                    return
                pokers.get_proto_struct(resp.body.pokers)
                resp.header.result = 0
            else:
                result= game.bet(req.header.user,req.body.action,req.body.gold,req.body.other)
                resp.header.result = result
        finally:
            table.lock.release()


    @USE_TRANSACTION
    def handle_kick_other(self,session,req,resp,event):

        # 踢走某人，游戏中不可以踢人
        table = self.get_table(req.body.other)
        if table == None or table.game != None and table.game.is_gambler(req.body.other):
            resp.header.result = RESULT_FAILED_NO_KICK
            return

        # 背包中是否存在相关道具
        bag = BagObject(self)
        if bag.has_item(session, req.header.user, ITEM_MAP['kick'][0]) == False:
            resp.header.result = RESULT_FAILED_INVALID_BAG
            return

        # 权限验证，被踢的人在vip6及以上等级有免踢权限
        other_user = session.query(TUser).filter(TUser.id == req.body.other).first()
        vip = VIPObject(self)
        if vip.to_level(other_user.vip_exp) >= NO_KICK_LEVEL:
        # if 'no_kick' in VIP_CONF[other_user.vip]['auth']:
            resp.header.result = RESULT_FAILED_NO_KICK
            return

        # 使用道具
        result = bag.use_user_item(session, req.header.user, ITEM_MAP['kick'][0])
        if result <= 0:
            resp.header.result = RESULT_FAILED_INVALID_BAG
            return

        # 踢走某人操作
        if table == None:
            resp.header.result = RESULT_FAILED_INVALID_TABLE
            return
        table.lock.acquire()
        try :
            table.kick_player(req.header.user, req.body.other)
        finally:
            table.lock.release()

        # 返回数据
        item = ItemObject.get_item(session, ITEM_MAP['kick'][0])
        pb = resp.body.result.items_removed.add()
        pb.id = item.id
        pb.name = item.name
        pb.icon = item.icon
        pb.description = item.description
        pb.count = result
        resp.header.result = 0

        resp.body.other = other_user.id

    @USE_TRANSACTION
    def handle_update_table_player(self,session,req,resp,event):
        table = self.get_table(req.header.user)
        if table == None:
            return False
        table.lock.acquire()
        try :
            table.update_player_info(req.header.user)
        finally:
            table.lock.release()

        return False