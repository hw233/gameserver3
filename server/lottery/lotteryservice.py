# -*- coding: utf-8 -*-
__author__ = 'Administrator'
import traceback

from services import GameService
from message.base import *
from message.resultdef import *
from util.handlerutil import *
from util.commonutil import *
from dal.core import *
from dal.core import *
from helper import protohelper
from helper import systemhelper

from proto.lottery_pb2 import *

from lottery import *
from lotteryconf import GAMECONF

class LotteryService(GameService):
    def setup_route(self):
        self.registe_command(BigRewardReq, BigRewardResp, self.handle_big_reward)
        self.registe_command(LotteryOpenReq, LotteryOpenResp, self.handle_open)
        self.registe_command(LotteryCloseReq, LotteryCloseResp, self.handle_close)
        self.registe_command(GoldChangeReq, GoldChangeResp, self.handle_gold_change)
        self.registe_command(LotteryBetReq, LotteryBetResp, self.handle_bet)

    def init(self):
        self.redis = self.server.redis
        self.dal = DataAccess(self.redis)
        self.table = Table(self)

    @USE_TRANSACTION
    def handle_open(self, session, req, resp, event):
        if systemhelper.is_lottery_close(req.header.user):
            resp.header.result = RESULT_FAILED_LOTTERY_FIX
            return

        user_info = self.dal.get_user(req.header.user)
        if user_info == None:
            self.sit_table_error(resp.body)
            return
        self.table.lock.acquire()
        try:
            self.table.sit_table(user_info, event.srcId)
            self.table.get_sit_table_proto_struct(user_info, resp.body)
            resp.header.result = 0
        except:
            traceback.print_exc()
            resp.header.result = -1
            self.sit_table_error(resp.body)
        finally:
            self.table.lock.release()

    @USE_TRANSACTION
    def handle_close(self, session, req, resp, event):
        if req.header.user not in self.table.push_players:
            resp.header.result = RESULT_FAILED_INVALID_NOT_EXISTS
            return
        self.table.lock.acquire()
        try:
            self.table.leave_table(req.header.user)
            resp.header.result = 0
        except:
            traceback.print_exc()
            resp.header.result = -1
        finally:
            self.table.lock.release()

    @USE_TRANSACTION
    def handle_gold_change(self, session, req, resp, event):
        if systemhelper.is_lottery_close(req.header.user):
            resp.header.result = RESULT_FAILED_LOTTERY_FIX
            return
        self.table.game.get_gold_change_proto_struct(resp.body)
        resp.header.result = 0

    @USE_TRANSACTION
    def handle_bet(self, session, req, resp, event):
        if not self.table.in_table(req.header.user):
            resp.header.result = RESULT_FAILED_INVALID_NOT_EXISTS
            return

        user_info = self.dal.get_user(req.header.user)
        if req.body.auto_bet_number > 0:
            if user_info.get_gold() < sum([x.bet_gold for x in req.body.bet]) * req.body.auto_bet_number:
                resp.header.result = RESULT_FAILED_NO_ENOUGH_GOLD
                return

        if req.body.auto_bet_number == -1:
            if not self.table.get_lottery_auto_users(user_info.id):
                resp.header.result = RESULT_FAILED_AUTO_BET_ERROR
                return
            else:
                # 取消自动投
                self.table.lock.acquire()
                try:

                    if self.table.game.can_bet == False:
                        resp.header.result = RESULT_FAILED_NOT_BET_ERROR
                        return
                    result_gold = self.table.game.auto_bet_cancel(session, user_info.id)
                    if result_gold < 0:
                        # 用户取消失败，最后一局取消无效
                        result_gold = 0
                    self.table.game.get_result_proto_struct(result_gold, user_info.get_gold(), resp.body.result)
                    resp.header.result = 0
                    return
                except:
                    traceback.print_exc()
                    resp.header.result = -1
                finally:
                    self.table.lock.release()
        else:

            if user_info.get_gold() < GAMECONF['bet_min']:
                resp.header.result = RESULT_FAILED_NO_ENOUGH_GOLD
                return

            self.table.lock.acquire()
            try:
                if self.table.game.can_bet == False:
                    resp.header.result = RESULT_FAILED_NOT_BET_ERROR
                    return
                if req.body.auto_bet_number == 0:
                    if self.table.game.check_bet(user_info.id, req.body.bet):
                        bets_gold = self.table.game.bet(user_info.id, req.body.bet)
                    else:
                        resp.header.result = RESULT_FAILED_BET_MAX
                        return
                elif req.body.auto_bet_number > 0:
                    bets_gold = self.table.auto_bet(user_info.id, req.body.bet, req.body.auto_bet_number)
                self.table.game.get_result_proto_struct(-bets_gold, user_info.get_gold(), resp.body.result)
                resp.header.result = 0
                return
            except:
                traceback.print_exc()
                resp.header.result = -1
            finally:
                self.table.lock.release()


    @USE_TRANSACTION
    def handle_big_reward(self, session, req, resp, event):
        for user, reward_log,reward_gold in get_reward_log(session):
            protohelper.set_lottery_reward_log(resp.body.players.add(), user, reward_gold, reward_log, user.sex, user.vip_exp)
        resp.header.result = 0

    def sit_table_error(self, pb):
        pb.live_seconds = -1
        pb.remain_seconds = -1
        pb.reward_gold_pool = -1
        pb.last_baozi = -1
        pb.remain_auto_bet = -1
        pb.last_big_winner = None

