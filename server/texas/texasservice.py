# -*- coding: utf-8 -*-
__author__ = 'Administrator'
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
from proto.texas_pb2 import *

from db.connect import *
from db.texas_player import *

from util.handlerutil import *
from util.commonutil import *

from dal.core import *
from helper import systemhelper

from table import TableManager,Player


class TexasService(GameService):
    def setup_route(self):
        self.registe_command(TexasLeaveTableReq,TexasLeaveTableResp,self.handle_leave_table)
        self.registe_command(TexasBetActionReq,TexasBetActionResp,self.handle_bet_action)
        self.registe_command(TexasQueryPlayerReq,TexasQueryPlayerResp,self.handle_query_player)

    def init(self):
        self.registe_handler(TexasSitTableReq,TexasSitTableResp,self.handle_sit_table)
        self.registe_handler(TexasUpdatePlayerReq,TexasUpdatePlayerResp,self.handle_update_player)

        self.room_id = self.serviceId
        self.table_manager = TableManager(self)
        self.redis = self.server.redis

    def get_table(self,user):
        return self.table_manager.get_player_table(user)

    @USE_TRANSACTION
    def handle_sit_table(self,session,req,resp,event):
        if event.srcId != 5800:
	    if systemhelper.is_texas_close(req.header.user):
                resp.header.result = RESULT_FAILED_TEXAS_FIX
                return

        table = None
        self.table_manager.lock.acquire()
        try :
            result,table = self.table_manager.sit_table(req.body.table_id, \
                    req.header.user,event.srcId, req.body.not_tables)
            if result < 0:
                resp.header.result = result
                return
            table.get_proto_struct(resp.body.table)

            if table.game != None:
                if req.header.user in table.game.gamblers:
                    gambler = table.game.gamblers[req.header.user]
                    if len(gambler.pokers) > 0:
                        resp.body.own_pokers.uid = gambler.uid
                        for poker in gambler.pokers:
                            poker.get_proto_struct(resp.body.own_pokers.pokers.add())
                else:
                    if table.game.status > TEXAS_START:
                        table.game.new_watch(req.header.user)

            resp.body.room_id = self.room_id
            resp.header.result = result
        except:
            traceback.print_exc()
        finally :
            self.table_manager.lock.release()

    @USE_TRANSACTION
    def handle_bet_action(self,session,req,resp,event):
        table = self.get_table(req.header.user)
        if table == None:
            resp.header.result = RESULT_FAILED_INVALID_TABLE
            return False

        game = table.game
        table.lock.acquire()
        try :
            if req.body.texas_status != table.game.status:
                result = RESULT_FAILED_NOT_START
            else:
                result = game.bet(req.header.user, req.body.bet_type, req.body.action_gold, req.body.bet_reward_gold)
            resp.header.result = result
        except:
            traceback.print_exc()
        finally:
            table.lock.release()

    @USE_TRANSACTION
    def handle_leave_table(self,session,req,resp,event):
        table = self.get_table(req.header.user)
        if table == None:
            resp.header.result = RESULT_FAILED_INVALID_TABLE
            return

        table.lock.acquire()
        try:
            resp.header.result = table.remove_player(req.header.user)
            if len(table.players) == 0 and table.game != None:
                table.game.handle_hand(-1)

        finally:
            table.lock.release()

    @USE_TRANSACTION
    def handle_query_player(self,session,req,resp,event):

        table = self.get_table(req.body.uid)
        if table == None:
            resp.header.result = RESULT_FAILED_INVALID_TABLE
            return False

        player = table.players[req.body.uid]
        player.get_brief_proto_struct(resp.body.player_brief)
        player_record = session.query(TTexasPlayer).filter(TTexasPlayer.uid == player.uid).first()
        if player_record:
            resp.body.play_count = player_record.play_count
            resp.body.win_rate =  int(player_record.win_count / float(player_record.play_count) * 100)
            resp.body.big_win_gold = player_record.max_win_gold
        else:
            resp.body.play_count = 0
            resp.body.win_rate =  0
            resp.body.big_win_gold = 0
        resp.header.result = 0


    @USE_TRANSACTION
    def handle_update_player(self,session,req,resp,event):
        table = self.get_table(req.header.user)
        if table == None:
            return False
        table.lock.acquire()
        try :
            table.update_player_info(req.header.user)
        finally:
            table.lock.release()

        return False
