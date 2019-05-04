# coding: utf-8

import json
import logging
import traceback
import socket
import gevent
import binascii
from ctypes import *

import random, time
from datetime import datetime
from datetime import date as dt_date
from datetime import time as dt_time

from config.vip import *

from services import GameService
from message.base import *
from message.resultdef import *

from proto.constant_pb2 import *
from proto.access_pb2 import *
from proto.game_pb2 import *
from proto.war_pb2 import *

from db.connect import *

from util.handlerutil import *
from util.commonutil import *

from dal.core import *

from wartable.table import *
from wartable.gameconf import *
from wartable import robot
from helper import protohelper
from helper import systemhelper


class WarTableService(GameService):
    def setup_route(self):
        self.registe_command(SitWarTableReq, SitWarTableResp, self.handle_sit)
        self.registe_command(LeaveWarTableReq, LeaveWarTableResp, self.handle_leave)
        self.registe_command(WarBetActionReq, WarBetActionResp, self.handle_bet)

        self.registe_command(QueryPoolRankReq, QueryPoolRankResp, self.handle_pool)
        self.registe_command(QueryTrendReq, QueryTrendResp, self.handle_trend)
        self.registe_command(QueryWarPlayerReq,QueryWarPlayerResp,self.handle_query_player)
        self.registe_command(QueryRichReq,QueryRichResp,self.handle_query_rich)

        self.registe_command(OfflineReq,OfflineResp,self.handle_offline)




    def init(self):

        self.redis = self.server.redis
        self.dal = DataAccess(self.redis)
        self.table = Table(self)
        self.robot_manager = robot.RobotManager(self.table)
        self.table.robot_manager = self.robot_manager
        self.redis.delete('war_online')

    @USE_TRANSACTION
    def handle_sit(self, session, req, resp, event):
        if systemhelper.is_war_close(req.header.user):
            resp.header.result = RESULT_FAILED_WAR_FIX
            return

        logging.info(u'enter sit table handler user-%d' % req.header.user)
        user = self.dal.get_user(req.header.user)
        if user == None:
            resp.header.result = RESULT_FAILED_ACCOUNT_INVALID
            return
        if user.gold < TABLE_GAME_CONF[0]:
            resp.header.result = RESULT_FAILED_NO_ENOUGH_GOLD
            return
        if self.table.game == None:
            resp.header.result = RESULT_FAILED_INVALID_RUNNING
            return

        self.table.lock.acquire()
        try:
            self.table.sit_table(user, event.srcId)
            self.table.get_proto_struct(resp.body.table)
            resp.body.red_total = self.table.game.red_total
            resp.body.black_total = self.table.game.black_total
            resp.body.lucky_total = self.table.game.lucky_total
            player = self.table.players.get(user.id)
            player.get_proto_struct(resp.body.player)

            logging.info(u'sit-用户：%d，金币：%d 进入牌桌, service_id=%d', user.id, user.gold, player.access_service)
            logging.info(u'sit-当前用户%d获得牌桌数据：幸运星=%s，财富榜=%s，奖池=%d，剩余时间=%s' %
                          (user.id, resp.body.table.lucky_player.uid, str([x.uid for x in resp.body.table.rich_players]), resp.body.table.reward_pool, resp.body.table.remain_time))
            logging.info(u'sit-当前用户%d获得用户数据：金币=%d，总局数=%d，最大赢取=%d，最近赢取=%d，最近20押注=%d' %
                          (resp.body.player.uid, resp.body.player.gold, resp.body.player.total_games,resp.body.player.max_win_gold,resp.body.player.recent_win_games, resp.body.player.recent_bet_gold))
            resp.header.result = 0
        except:
            traceback.print_exc()
            resp.header.result = -1
        finally:
            self.table.lock.release()

    @USE_TRANSACTION
    def handle_leave(self, session, req, resp, event):
        self.table.lock.acquire()
        try:
            if not self.table.players.has_key(req.header.user):
                resp.header.result = RESULT_FAILED_INVALID_NOT_EXISTS
                return
            self.table.remove_player(req.header.user)
            logging.info(u'leave=用户%d，离开了牌局' % req.header.user)
            resp.header.result = 0
        except:
            traceback.print_exc()
            resp.header.result = -1
        finally:
            self.table.lock.release()

    @USE_TRANSACTION
    def handle_bet(self, session, req, resp, event):
        self.table.lock.acquire()
        try:
            player = self.table.players.get(req.header.user, None)
            if player == None:
                resp.header.result = RESULT_FAILED_INVALID_IN_WAR
                return
            if player.user_dal.gold < TABLE_GAME_CONF[0]:
                resp.header.result = RESULT_FAILED_NO_ENOUGH_GOLD
                return
            if int(req.body.chip.gold) > int(player.user_dal.gold):
                resp.header.result = RESULT_FAILED_LESS_GOLD
                return
            if self.table.game.is_running() == False:
                resp.header.result = RESULT_FAILED_NOT_START
                return
            if req.body.action_type in (1, -1) and self.table.game.player_actions.has_key(req.header.user):
                action_list = [x.action_type for x in self.table.game.player_actions[req.header.user] if x.action_type != 0]
                if req.body.action_type == 1 and len(action_list) > 0:
                    if action_list[0] != 1:
                        resp.header.result = RESULT_FAILED_BET_OTHER
                        return
                elif req.body.action_type == -1 and len(action_list) > 0:
                     if action_list[0] != -1:
                        resp.header.result = RESULT_FAILED_BET_OTHER
                        return

            if self.table.game.player_actions.has_key(req.header.user):
                bet_total = sum([x.gold for x in self.table.game.player_actions[req.header.user]])
                if (req.body.chip.gold + bet_total) > TABLE_GAME_CONF[15]:
                    resp.header.result = RESULT_FAILED_BET_OVER
                    return

            if req.body.chip.gold > TABLE_GAME_CONF[15]:
                resp.header.result = RESULT_FAILED_BET_OVER
                return

            result = self.table.game.bet(player, req.body.action_type, req.body.chip.gold)

            self.table.players[req.header.user].idle_time = time.time()

            resp.body.action_type = req.body.action_type
            resp.body.chip.gold = req.body.chip.gold
            resp.body.gold = int(player.gold)
            resp.header.result = result
        except:
            traceback.print_exc()
            resp.header.result = -1
        finally:
            self.table.lock.release()

    @USE_TRANSACTION
    def handle_pool(self, session, req, resp, event):
        self.table.lock.acquire()
        try:
            for log in self.table.game_log.get_award_lists(session, 10, self):
                log.get_proto_struct(resp.body.players.add())
        finally:
            self.table.lock.release()
        resp.header.result = 0


    @USE_TRANSACTION
    def handle_trend(self, session, req, resp, event):
        self.table.lock.acquire()
        try:
            for log in self.table.game_log.data_brief[-20:]:
                log.get_proto_struct(resp.body.history.add())

            for log in self.table.game_log.get_poker_path():
                log.get_proto_struct(resp.body.history_road.add())
        finally:
            self.table.lock.release()

        resp.header.result = 0

    @USE_TRANSACTION
    def handle_offline(self, session, req, resp, event):
        if self.table == None:
            resp.header.result = RESULT_FAILED_INVALID_TABLE
            return False

        self.table.lock.acquire()
        try:
            if self.table.players.has_key(req.header.user):
                if self.table.players[req.header.user].access_service != -1:
                    self.table.players[req.header.user].offline_time = int(time.time())
        finally:
            self.table.lock.release()
        return False

    @USE_TRANSACTION
    def handle_query_player(self, session, req, resp, event):
        user = self.dal.get_user(req.body.uid)
        if user == None:
            resp.header.result = RESULT_FAILED_ACCOUNT_INVALID
            return
        self.table.lock.acquire()
        try:

            if self.table.players.has_key(req.body.uid):
                    self.table.players[req.body.uid].brief_log(self.table, req.body.uid)
                    self.table.players[req.body.uid].get_proto_struct(resp.body.player)
            else:
                resp.header.result = RESULT_FAILED_INVALID_NOT_EXISTS
                return
            # for player in self.table.rank.get_top_players():
            #     if player.uid == req.body.uid:
            #         player.brief_log(self.table, req.body.uid)
            #         player.get_proto_struct(resp.body.player)
            #         break
        except:
            traceback.print_exc()
        finally:
            self.table.lock.release()
        resp.header.result = 0

    @USE_TRANSACTION
    def handle_query_rich(self, session, req, resp, event):
        if self.table.game == None:
            resp.header.result = RESULT_FAILED_INVALID_RUNNING
            return

        sizeof_rich = req.body.size
        if sizeof_rich > 50:
            sizeof_rich = 20

        self.table.lock.acquire()
        try:
            if self.table.rank.has_lucky():
                self.table.rank.lucky_player.get_proto_struct(resp.body.players.add())

            my_rank = -1
            for index, player in enumerate(self.table.rank.top_players[:sizeof_rich]):
                player.get_proto_struct(resp.body.players.add())
                if player.uid == req.header.user:
                   my_rank = index
            resp.body.my_rank = my_rank
        except:
            traceback.print_exc()
        finally:
            self.table.lock.release()
        resp.header.result = 0