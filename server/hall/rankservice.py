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



from services import GameService
from message.base import *
from message.resultdef import *

from proto.constant_pb2 import *
from proto.struct_pb2 import *
from proto.hall_pb2 import *
from proto.rank_pb2 import *

from util.handlerutil import *

from db.connect import *
from db.announcement import *

from helper import protohelper
from dal.core import *

from hall.rank import *

class RankService(GameService):
    def setup_route(self):
        self.registe_command(QueryRankReq,QueryRankResp,self.handle_rank)

    def init(self):
        self.redis = self.server.redis
        self.da = DataAccess(self.redis)
        self.rank = Rank(self)

    # 排名查询
    @USE_TRANSACTION
    def handle_rank(self, session, req, resp, event):

        # // 排行榜类型
        # enum RankType {
        # 	RANK_WEALTH = 1;
        # 	RANK_CHARGE = 2;
        # 	RANK_CHARM = 3;
        # 	RANK_MAKE_MONEY = 4;
        #   RANK_WAR = 5;
        # }
        #
        # // 排行榜参数
        # enum RankTime{
        # 	RANK_ALL_TIME = 0;
        # 	RANK_YESTERDAY = 1;
        # 	RANK_TODAY = 2;
        # 	RANK_LAST_MONTH = 3;
        # 	RANK_THIS_MONTH = 4;
        # 	RANK_LAST_WEEK = 5;
        # 	RANK_THIS_WEEK = 6;
        # }
        items = []
        if req.body.rank_type == RANK_WEALTH:
            # 总财富榜
            items = self.rank.wealth_top(session, 0)
        elif req.body.rank_type == RANK_CHARGE:
            # 日充值榜
            items = self.rank.charge_top(session, req.body.rank_time)
            my_rank = -1
            for index, item in enumerate(items):
                if item.get('uid') == req.header.user:
                    my_rank = index + 1
            resp.body.my_rank = my_rank if my_rank != -1 else -1
            items = items[:10]
        elif req.body.rank_type == RANK_MAKE_MONEY:
            # 周赚金榜
            items = self.rank.make_money_top(session, req.body.rank_time)
            my_rank = -1
            for index, item in enumerate(items):
                if item.get('uid') == req.header.user:
                    my_rank = index + 1
            resp.body.my_rank = my_rank if my_rank != -1 else -1
            items = items[:10]
        elif req.body.rank_type == RANK_WAR:
            # 红黑盈利榜
            items = self.rank.war_top(session, req.body.rank_time)
            my_rank = -1
            for index, item in enumerate(items):
                if item.get('uid') == req.header.user:
                    my_rank = index + 1
            resp.body.my_rank = my_rank if my_rank != -1 else -1
            items = items[:10]
        elif req.body.rank_type == RANK_LOTTERY:
            # print 'lottery...'
            # 时时彩排行榜
            items = self.rank.lottery_big_reward(session, req.body.rank_time)
            my_rank = -1
            for index, item in enumerate(items):
                if item.get('uid') == req.header.user:
                    my_rank = index + 1
            resp.body.my_rank = my_rank if my_rank != -1 else -1
            items = items[:10]
        elif req.body.rank_type == RANK_TEXAS:
            # 德州排行榜
            items = self.rank.texas_top_rank(session, req.body.rank_time)
            my_rank = -1
            for index, item in enumerate(items):
                if item.get('uid') == req.header.user:
                    my_rank = index + 1
            resp.body.my_rank = my_rank if my_rank != -1 else -1
            items = items[:10]

        for index in range(len(items)):
            protohelper.set_top(resp.body.players.add(), items[index], index)
        resp.header.result = 0

