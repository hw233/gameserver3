# -*- coding: utf-8 -*-
__author__ = 'Administrator'


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

from services import GameService
from message.base import *
from message.resultdef import *

from db.connect import *

from proto.access_pb2 import *
from proto.texas_pb2 import *
from proto.constant_pb2 import *
from proto.struct_pb2 import *


from util.handlerutil import *

from config.var import *

from texasroom import *


class TexasRoomService(GameService):
    def setup_route(self):
        self.registe_command(TexasSitTableReq,TexasSitTableResp,self.handle_sit_table)
        self.registe_command(OfflineReq,OfflineResp,self.handle_offline)
        self.registe_command(TexasUpdatePlayerReq,TexasUpdatePlayerResp,self.handle_update_table_player)

    def init(self):
        self.redis = self.server.redis
        max_user = self.getConfigOption("max_user","100")
        self.room_manager = TexasRoomManager(self,int(max_user))

    @USE_TRANSACTION
    def handle_sit_table(self,session,req,resp,event):
        logging.info("====> Sit Table Now: %d", req.header.user)

        if req.body.table_id < 0:
            uid = req.header.user
            room_id = self.room_manager.get_user_room(uid)
            if room_id < 0:
                room_id = self.room_manager.find_room()
                if room_id < 0:
                    resp.header.result = -1
                    return

            new_req = create_client_message(TexasSitTableReq)
            new_req.header.user = uid
            new_req.header.transaction = req.header.transaction
            new_req.body.table_id = req.body.table_id
            # new_req.body.table_type = req.body.table_type
            for tid in req.body.not_tables:
                new_req.body.not_tables.append(tid)

            self.forward_proxy_message(event.srcId,room_id,new_req.header.command, \
                            new_req.header.user,new_req.header.transaction,new_req.encode())
        else:
            uid = req.header.user
            new_room_id = self.room_manager.find_room()
            if new_room_id < 0:
                resp.header.result = 0
                return

            room_id = self.room_manager.get_user_room(uid)
            if room_id > 0 and new_room_id != room_id:
                new_req = create_client_message(TexasLeaveInternalReq)
                new_req.header.user = uid
                new_req.header.transaction = req.header.transaction
                self.forward_proxy_message(event.srcId,room_id,new_req.header.command, \
                                req.header.user,req.header.transaction,new_req.encode())

            new_req = create_client_message(TexasSitTableReq)
            new_req.header.user = uid
            new_req.header.transaction = req.header.transaction
            new_req.body.table_id = req.body.table_id
            # new_req.body.table_type = req.body.table_type
            for tid in req.body.not_tables:
                new_req.body.not_tables.append(tid)
            # new_req.body.not_tables.append(req.body.table_id)
            self.forward_proxy_message(event.srcId,new_room_id,new_req.header.command, \
                            req.header.user,req.header.transaction,new_req.encode())


        return False


    @USE_TRANSACTION
    def handle_offline(self,session,req,resp,event):
        uid = req.header.user
        room_id = self.room_manager.get_user_room(uid)
        if room_id > 0:
            new_req = create_client_message(OfflineReq)
            new_req.header.user = uid
            new_req.body.uid = uid
            self.forward_proxy_message(event.srcId,room_id,new_req.header.command, \
                            req.header.user,req.header.transaction,new_req.encode())

        return False

    @USE_TRANSACTION
    def handle_update_table_player(self,session,req,resp,event):
        uid = req.header.user
        room_id = self.room_manager.get_user_room(uid)
        if room_id > 0:
            new_req = create_client_message(TexasUpdatePlayerReq,uid)
            self.forward_proxy_message(event.srcId,room_id,new_req.header.command, \
                            req.header.user,req.header.transaction,new_req.encode())

        return False