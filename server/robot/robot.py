#coding: utf-8
import gevent
from gevent import monkey;monkey.patch_all()

import json
import logging
import traceback
from sqlalchemy.sql import select, update, delete, insert, and_,or_, subquery, not_, null, func, text,exists
from sqlalchemy import desc

import random,time

from collections import Counter
from datetime import datetime,timedelta
from datetime import date as dt_date
from datetime import time as dt_time

from proto.access_pb2 import *
from proto.constant_pb2 import *
from proto.game_pb2 import *
from proto.chat_pb2 import *
from proto.friend_pb2 import *
from proto import struct_pb2 as pb2

from goldflower.game import *
from goldflower.gameconf import *

from message.base import *
from message.resultdef import *

from util.commonutil import *

from db.connect import *
from db.user import *
from db.account_book import *
from db.user_goldflower import *
from db.lucky import *
from db.robot import *
from db.friend_apply import *

from helper import dbhelper

from strategy import *

from dal.core import *

ROBOT_JIJIN = 1
ROBOT_PINGHENG = 2
ROBOT_BAOSHOU = 3

CHAT_WAIT_TOO_LONG = 1

EMOTION_WAIT_TOO_LONG = {
    1:2,
    2:5,
    3:11,
}

RESPONSE_CHAT = [
    (90,-1,0),
    (5,1,3),
    (10,1,6),
    (10,1,12),
]
# 配置方式（rate,type,content）,-1:不说话，1：代表表情，2：代表短语
LOST_5_GAMES = [
    (90,-1,0),
    (5,1,2),
    (5,1,9),  # 今天可真是够背的
]

WIN_3_GAMES = [
    (80,-1,0),
    (10,1,14),
    (10,1,3), # 今天可赚大发了，哈哈”
]

LOST_GAME = [
    #(91,-1,0),
    #(4,1,2),
    #(3,1,9),
    #(2,1,1),
    (31,-1,0),
    (24,1,2),
    (23,1,9),
    (22,1,1),
]

SIT_TABLE = [
    (60,1,10),
    (30,1,2),
    (5,1,9),
    (5,1,1),
]

WIN_GAME = [
    #(91,-1,0),
    #(5,1,14),
    #(4,1,15),
    (31,-1,0),
    (35,1,14),
    (34,1,15),
]

AFTER_COMPARE = [
    (60,-1,0),
    (20,1,8),
    (20,1,13),
]

CHAT_SHOW_HAND = [
    (90,-1,0),
    (5,1,13),
    (3,1,8),
    (2,1,6),
]

TABLE_CHIPS = {
    TABLE_L : [200,500,1000,2000,3000],
    TABLE_M : [2000,3000,5000,10000,20000],
    TABLE_H : [10000,20000,30000,50000,100000],
    TABLE_H2 :[50000,100000,150000,250000,500000],
}

RECHARGE_GOLD = {
    TABLE_L : (30000,160000),
    TABLE_M : (160000,1500000),
    TABLE_H : (1500000,6000000),
    TABLE_H2 :(6000000,50000000),
}

ROBOTS_PERCENT = {
    TABLE_L:   40,
    TABLE_M:   30,
    TABLE_H:   20,
    TABLE_H2:  10,
}



class BetStrategy:
    def __init__(self,robot):
        self.robot = robot


    def get_pokers_level(self,pokers):
        if pokers.poker_type == P_BAOZI:
            return 0
        elif pokers.poker_type == P_TONGHUASHUN and pokers.get_dan_value() >= 10:
            return 1
        elif pokers.poker_type == P_TONGHUASHUN and pokers.get_dan_value() < 10:
            return 2
        elif pokers.poker_type == P_TONGHUA and pokers.get_dan_value() >= 10:
            return 3
        elif pokers.poker_type == P_TONGHUA and pokers.get_dan_value() < 10:
            return 4
        elif pokers.poker_type == P_SHUN and pokers.get_dan_value() >= 10:
            return 5
        elif pokers.poker_type == P_SHUN and pokers.get_dan_value() < 10:
            return 6
        elif pokers.poker_type == P_DUI and pokers.get_dui_value() >= 10:
            return 7
        elif pokers.poker_type == P_DUI and pokers.get_dui_value() < 10:
            return 8
        elif pokers.poker_type == P_DAN and pokers.get_dan_value() >= 13:
            return 9
        else:
            return 10

    def get_see_bet_strategy(self):
        robot = self.robot
        level = self.get_pokers_level(robot.my_pokers)

        if robot.type == ROBOT_BAOSHOU:
            strategy = STRATEGY_BAOSHOU[MAP_BAOSHOU[level]]
        elif robot.type == ROBOT_PINGHENG:
            strategy = STRATEGY_PINGHENG[MAP_PINGHENG[level]]
        elif robot.type == ROBOT_JIJIN:
            strategy = STRATEGY_JIJIN[MAP_JIJIN[level]]

        rate_accept_show_hand = strategy[5](robot,robot.round)
        rate_show_hand = strategy[4](robot,robot.round)
        rate_giveup = strategy[3](robot,robot.round)
        rate_compare = strategy[2](robot,robot.round)
        rate_add = strategy[1](robot,robot.round)
        rate_follow = strategy[0](robot,robot.round)

        return rate_accept_show_hand,rate_show_hand,rate_giveup,rate_compare,rate_add,rate_follow

    def do_bet_action(self):
        action = self.get_bet_action()
        if not self.robot.is_see :
            if action[0] in (SHOW_HAND,GIVE_UP):
                self.bet(SEE_POKER)
                return
        else:
            if action[0] == GIVE_UP:
                not_fails = [player for player in self.robot.players.values() if not player.is_fail and player.uid != self.robot.robot_id]
                pokers = self.robot.my_pokers
                round_min_bet = self.robot.round_min_bet * 2 if self.robot.is_see else self.robot.round_min_bet
                if len(not_fails) == 1 and (pokers.poker_type != P_DAN or (pokers.poker_type == P_DAN and pokers.get_dan_value() > 12)):
                    if self.robot.is_show_hand:
                        if self.robot.total_bet_gold >= 10 * self.robot.action_gold * 2:
                            self.bet(SHOW_HAND)
                            return
                    else:
                        if self.robot.gold * 10 <= self.robot.total_bet_gold:
                            if self.robot.gold > round_min_bet and self.robot.round >= (TABLE_GAME_CONFIG[self.robot.table_type][4] + 1):
                                self.bet(COMPARE,0,not_fails[0].uid)
                                return
                            else:
                                self.bet(SHOW_HAND,)
                                return
                        else:
                            if round_min_bet * 10 <= self.robot.total_bet_gold and self.robot.gold >= round_min_bet:
                                if self.robot.round >= (TABLE_GAME_CONFIG[self.robot.table_type][4] + 1):
                                    self.bet(COMPARE,0,not_fails[0].uid)
                                    return

        self.bet(*action)

    def get_bet_action(self):
        robot = self.robot

        if robot.is_see and robot.x != 1:
            if robot.my_pokers.poker_type == P_DAN and robot.my_pokers.get_dan_value() < 13:
                return (GIVE_UP,)

        rate_accept_show_hand = 0
        rate_show_hand = 0
        rate_giveup = 0
        rate_compare = 0
        rate_add = 0

        if not robot.is_see:
            if robot.type == ROBOT_BAOSHOU:
                rate_accept_show_hand   = 10 + 90 * robot.x + 30 * robot.b * ( 1 - robot.x)
                rate_show_hand          = 1 * (robot.x + 1 - robot.b)
                rate_compare            = 7 * (robot.round - robot.b)+ 10 * (robot.k - 0.5 * robot.x) * robot.round
                rate_add                = 12 - robot.k * 9
                rate_follow             = 90 - 7 *(robot.round - robot.b) - 10 * (robot.k - 0.5 * robot.x) * robot.round + 9 * robot.k

            elif robot.type == ROBOT_PINGHENG:
                rate_accept_show_hand   = 20 + 80 * robot.x + 25 * robot.b * ( 1 - robot.x)
                rate_show_hand          = 3 * (robot.x + 1 - robot.b)
                rate_compare            = 5 * (robot.round - robot.b)+ 6 * (robot.k - 0.7 * robot.x) * robot.round
                rate_add                = 20 - robot.k * 7
                rate_follow             = 85 - 5 *(robot.round - robot.b) - 6 * (robot.k - 0.7 * robot.x) * robot.round + 7 * robot.k
            elif robot.type == ROBOT_JIJIN:
                rate_accept_show_hand   = 30 + 70 * robot.x + 20 * robot.b * ( 1 - robot.x)
                rate_show_hand          = 5 * (robot.x + 1 - robot.b)
                rate_compare            = 3 * (robot.round - robot.b)+ 3 * (robot.k - 1 * robot.x) * robot.round
                rate_add                = 35 - robot.k * 5
                rate_follow             = 70 - 3 *(robot.round - robot.b) - 3 * (robot.k - 1 * robot.x) * robot.round + 5 * robot.k
        else:
            rate_accept_show_hand,rate_show_hand,rate_giveup,rate_compare,rate_add,rate_follow = self.get_see_bet_strategy()

        rate_accept_show_hand = int(rate_accept_show_hand)
        rate_show_hand = int(rate_show_hand)
        rate_giveup = int(rate_giveup)
        rate_compare = int(rate_compare)
        rate_add = int(rate_add)

        robot.info("选择策略 看牌=%s,接受=%d,全压=%d,放弃=%d,比=%d,加=%d,跟=%d",robot.is_see,rate_accept_show_hand,rate_show_hand, \
                                    rate_giveup,rate_compare,rate_add,rate_follow)
        if robot.is_see and random.randint(1,100) < rate_giveup:
            return (GIVE_UP,)

        if robot.is_show_hand:
            # 赌注很大,且对方全压,如果机器人牌还可以,避免机器人直接弃牌
            if robot.is_see and robot.action_gold * 20 <= self.robot.total_bet_gold and robot.x == 0:
                pokers = robot.my_pokers
                if pokers.poker_type != P_DAN or (pokers.poker_type == P_DAN and pokers.get_dan_value() > 13):
                    return (SHOW_HAND,)

            if random.randint(1,100) < rate_accept_show_hand:
                return (SHOW_HAND,)
            else:
                return (GIVE_UP,)
        else:
            not_fails = [player for player in robot.players.values() if not player.is_fail and player.uid != robot.robot_id]
            see_players = [player for player in robot.players.values() if not player.is_fail and player.is_see and player.uid != robot.robot_id]

            round_min_bet = robot.round_min_bet * 2 if robot.is_see else robot.round_min_bet
            if robot.gold < round_min_bet:
                if len(not_fails) == 1 and random.randint(1,100) > rate_giveup:
                    return (SHOW_HAND,)
                else:
                    return (GIVE_UP,)

            if robot.is_see:
                need_gold = TABLE_GAME_CONFIG[robot.table_type][3] * 3 * 2
            else:
                need_gold = TABLE_GAME_CONFIG[robot.table_type][3] * 3

            if robot.round >= (TABLE_GAME_CONFIG[robot.table_type][4] + 1) and robot.gold < need_gold:
                if len(see_players) != 0:
                    return (COMPARE,0,random.choice(see_players).uid)
                else:
                    return (COMPARE,0,random.choice(not_fails).uid)

            if len(not_fails) == 1 and random.randint(1,100) < rate_show_hand:
                return (SHOW_HAND,)
            else:
                if robot.round >= (TABLE_GAME_CONFIG[robot.table_type][4] + 1) and random.randint(1,100) < rate_compare:
                    if len(see_players) != 0:
                        return (COMPARE,0,random.choice(see_players).uid)
                    else:
                        return (COMPARE,0,random.choice(not_fails).uid)
                else:
                    if random.randint(1,100) > rate_add:
                        return (FOLLOW,)
                    else:
                        CHIPS = TABLE_CHIPS[robot.table_type]
                        current_chip = CHIPS.index(robot.round_min_bet)
                        gold = 0
                        ch = robot.decide(40,30,20,10)
                        add = 0
                        if ch == 0:
                            add = 1
                        elif ch == 1:
                            add = 2
                        elif ch == 2:
                            add = 3
                        else:
                            add = 1

                        next_chip = current_chip + add
                        if next_chip >= len(CHIPS):
                            gold = TABLE_GAME_CONFIG[robot.table_type][3]
                        else:
                            gold = CHIPS[next_chip]

                        if robot.is_see:
                            return (ADD,gold * 2) if robot.gold >= gold * 2 else (FOLLOW,)
                        else:
                            return (ADD,gold) if robot.gold >= gold else (FOLLOW,)

    def bet(self,action,gold = 0,other = -1):
        if action == GIVE_UP and random.randint(0,100) < 1:
            self.robot.info("机器人弃牌,模拟逃跑")
            return

        self.robot.info("%s,金币=%d,比牌对手=%d",BetAction.Name(action),gold,other)

        req = create_client_event(BetActionReq,self.robot.robot_id)
        req.body.action = action
        req.body.table_id = self.robot.table_id
        req.body.gold = gold
        req.body.other = other
        gevent.spawn_later(self.robot.get_delay(),self.robot.forward_message,req)

class TablePlayer:
    def __init__(self,uid,seat):
        self.uid = uid
        self.seat = seat


class GamblerPlayer:
    def __init__(self,uid):
        self.uid = uid
        self.is_see = False
        self.is_fail = False
        self.pokers = None


class Robot:
    def __init__(self,manager,robot_id,start_time,duration):
        self.start_time = datetime.combine(datetime.today(),start_time)
        self.end_time = self.start_time + timedelta(seconds = duration)
        self.has_quit_command = False

        self.robot_id = robot_id

        self.manager = manager
        self.service = manager.service

        session = Session()
        try :
            session.begin()
            self.row_robot_user = session.query(TUser).filter(TUser.id == robot_id).first()
            self.row_robot = session.query(TRobot).filter(TRobot.uid == robot_id).first()
            row_lucky = session.query(TLucky).filter(TLucky.uid == robot_id).first()
            if row_lucky == None:
                row_lucky = TLucky()
                row_lucky.uid = robot_id
                row_lucky.lucky = 50
                row_lucky.games = 1
                row_lucky.config_id = 10000
                session.add(row_lucky)
            session.commit()
        except:
            traceback.print_exc()
            session.rollback()
        finally:
            session.close()
            session = None

        self.sex = self.row_robot_user.sex

        self.table_ids = []
        self.game_results = []
        self.type = self.row_robot.type
        self.gold = self.row_robot_user.gold
        self.bet_strategy = BetStrategy(self)

        self.reset_table()
        self.init_gold()

        gevent.spawn(self.check_quit_condition)

    def forward_message(self,message):
        if self.is_game_start or not self.should_quit() :
            self.service.forward_message(message.header,message.encode())
        else:
            self.info("机器人应该退出，所以不能发送任何消息，%s ", message.header.command,color=color.red_bg)

    def init_gold(self):
        if self.gold < 10000 :
            gold = random.randint(30000,150000)
            self.manager.recharge_to(self.robot_id,gold)
            self.gold = gold
            self.info("机器人充值了: %d",self.gold,color=color.red)
        elif self.gold >= 150000000:
            gold = random.randint(10000000,100000000)
            self.manager.recharge_to(self.robot_id,gold)
            self.gold = gold
            self.info("机器人修改充值了: %d",self.gold,color=color.red)

    def reset_table(self):
        self.room_id = -1
        self.table_id = -1
        self.table_type = -1
        self.seat = -1
        self.table_players = {}
        self.table = None

        self.same_table_games = 0
        self.leave_table_rate = 10

        self.is_table_changing = False;

        self.reset_game()

    def reset_game(self):
        self.game = None
        self.is_game_ready = False
        self.is_game_start = False
        self.is_myself_ready = False

        self.players = {}
        self.in_game = False
        self.my_pokers = None
        self.current = -1
        self.can_see = False

        self.last_action = -1

        self.x = 0
        self.b = 1
        self.k = 0

        self.is_see = False
        self.is_other_see = False
        self.is_show_hand = False
        self.is_fail = False
        self.round = 0
        self.round_min_bet = 0
        self.action_gold = 0
        self.total_bet_gold = 0

        session = Session()
        try :
            row_user = session.query(TUser).filter(TUser.id == self.robot_id).first()
            self.gold = row_user.gold
        finally:
            session.close()
            session = None

    def should_quit(self):
        return  self.cant_play() or self.has_quit_command


    def cant_play(self):

        return self.end_time < datetime.now() or self.gold >= 200000000


    def info(self,format,*args,**kwargs):
        if kwargs == None or len(kwargs) == 0:
            logging.info("[%d/%d]" + format,self.robot_id,self.table_id,*args)
        else:
            color = kwargs["color"]
            logging.info(color("[%d/%d]" + format),self.robot_id,self.table_id,*args)

    def error(self,format,*args):
        self.info(format,*args,color=color.red_bg)

    def is_same_table(self,table_id):
        return self.table_id == table_id and not self.is_table_changing

    def get_delay(self):
        if self.row_robot.type == ROBOT_JIJIN:
            return random.randint(100,400)/200.0
        elif self.row_robot.type == ROBOT_PINGHENG:
            return random.randint(100,300)/100.0
        else:
            return random.randint(100,400)/100.0

    def set_player_ready(self,table_id):
        if not self.is_same_table(table_id):
            self.info("准备游戏错误，table_id = %d",table_id,color=color.red_bg)
            return
        req = create_client_event(SetPlayerReadyReq,self.robot_id)
        req.header.route = self.room_id
        req.body.table_id = self.table_id
        req.body.is_ready = True
        self.forward_message(req)
        self.info("开始准备游戏")

    def start(self):
        self.info("启动")
        req = create_client_event(ConnectGameServerReq)
        req.header.user = self.robot_id
        req.body.session = 12121231
        self.forward_message(req)
        gevent.spawn_later(random.randint(1,3),self.sit_table)

    def sit_table(self):
        if self.should_quit():
            self.info("准备离开，不再进桌子")
            return
        self.is_table_changing = True
        self.info("试图坐下")

        req = create_client_event(SitTableReq)
        req.header.user = self.robot_id
        req.body.table_id = -1
        req.body.table_type = self.get_suitable_table_type()
        req.body.not_tables.extend(self.table_ids[-3:])
        self.forward_message(req)

    def handle_sit_table_resp(self,req):
        self.is_table_changing = False
        if req.header.result != 0:
            if not self.should_quit():
                self.info("无法坐下 %d，继续找位置坐",req.header.result,color=color.strong)
                gevent.spawn_later(random.randint(5,10),self.sit_table)
            else:
                self.info("无法坐下 %d, 达到退出条件，机器人准备退出",req.header.result,color=color.blue)
            return

        if req.body.table.id == self.table_id:
            self.info("机器人不应该换桌时坐在原桌，需要重新换桌",color=color.red_bg)
            gevent.spawn_later(self.get_delay(),self.change_table,self.table_id)
            return

        self.reset_table()
        self.room_id = req.body.room_id
        self.table = req.body.table
        self.table_id = self.table.id
        self.table_type = req.body.table.table_type

        self.table_ids.append(self.table_id)

        # 获取牌桌玩家信息
        for player_brief in req.body.table.players:
            self.table_players[player_brief.uid] = TablePlayer(player_brief.uid,player_brief.seat)

        player_ids = [player_brief.uid for player_brief in req.body.table.players]

        self.info("坐下...，当前桌子的状态=%d，玩家=%s",req.body.table.goldflower.start_time,player_ids,color=color.strong)

        for brief in self.table.players:
            if brief.uid == self.robot_id:
                self.seat = brief.seat
                break

        if len(player_ids) == 5 and random.randint(0,100) < 50:
            self.info("坐下...，当前桌子的用户超过5人，准备退出",color=color.strong)
            gevent.spawn_later(random.randint(3,8),self.change_table,self.table_id)
            return

        self.is_game_start = self.table.goldflower.start_time > 0

        if not self.is_game_start:
            if not self.should_quit():
                self.info("落座后，开始第一局游戏")
                gevent.spawn_later(self.get_delay(),self.set_player_ready,self.table_id)
        else:
            gevent.spawn_later(random.randint(70,100)/10.0,self.wait_game_over,self.table_id,20)

    def wait_game_over(self,table_id,rate):
        if not self.is_same_table(table_id):
            self.error("等待游戏结束，但是桌号已经发生变化 %d",table_id)
            return

        if self.is_game_start and not self.in_game:
            if random.randint(0,100) < rate:
                self.info("游戏没有结束，机器人不耐烦，换桌",color=color.strong)
                self.change_table(table_id)
            else:
                gevent.spawn_later(random.randint(40,60)/10.0,self.wait_game_over,table_id,rate + 10)


    def handle_set_player_ready_resp(self,req):
        if req.header.result == RESULT_FAILED_LESS_GOLD:
            self.info("无法准备游戏，钱不足，准备充值，%d",req.header.result,color=color.strong)
            gold = self.manager.recharge(self.robot_id,50000)
            if gold > 0:
                self.gold = gold
            gevent.spawn_later(random.randint(1,6),self.change_table,self.table_id)
        elif req.header.result == RESULT_FAILED_ALREADY_READY:
            self.info("准备游戏失败，准备换桌，错误码%d",req.header.result,color=color.red)
        elif req.header.result < 0:
            self.info("准备游戏失败，准备换桌，错误码%d",req.header.result,color=color.yellow_bg)
            self.change_table(self.table_id)


    def handle_chat_event(self,req):
        if req.body.sender == self.robot_id:
            return

        if req.body.sender in self.manager.robots:
            return

        if self.in_game:
            gevent.spawn_later(random.randint(30,50)/10.0,self.talk_random,RESPONSE_CHAT)

    def handle_emotion_event(self,req):
        if req.body.target_player != self.robot_id:
            return

        if req.body.emotion_id == 1:
            if random.randint(0,100) >= 40:
                return

            gevent.spawn_later(random.randint(30,70)/10.0,self.send_interact_emotion,req.body.sender,1,1)
        else:
            r = random.randint(0,100)
            if r >= 80:
                return

            if r < 70:
                gevent.spawn_later(random.randint(30,100)/10.0,self.send_interact_emotion,req.body.sender,random.randint(2,5),1)
            elif r < 79:
                delay = random.randint(30,100)/10.0
                gevent.spawn_later(delay,self.send_interact_emotion,req.body.sender,random.randint(2,5),1)
                gevent.spawn_later(delay + random.randint(20,30)/10.0,self.send_interact_emotion,req.body.sender,random.randint(2,5),1)
            else:
                gevent.spawn_later(random.randint(20,70)/10.0,self.send_interact_emotion,req.body.sender,random.randint(2,5),10)

    def handle_send_emotion_resp(self,resp):
        if resp.header.result == 0:
            # 互动表情需要消耗金币,需要调用该接口,通知更新数据
            req = create_client_event(UpdateTablePlayerReq,self.robot_id)
            self.forward_message(req)


    def handle_player_ready_event(self,req):
        if req.body.player == self.robot_id:
            self.is_myself_ready = True
            gevent.spawn_later(12,self.wait_ready_too_long_0,self.table_id)
            self.info("自己准备好了")

    def wait_ready_too_long_0(self,table_id):
        if not self.is_same_table(table_id):
            self.info("wait_ready_too_long_0,等待太长时间，且桌号变化了，%d",table_id)
            return
        if not self.is_game_ready:
            gevent.spawn_later(6,self.wait_ready_too_long_1,table_id)

    def wait_ready_too_long_1(self,table_id):
        if not self.is_same_table(table_id):
            self.info("wait_ready_too_long_1,等待太长时间，且桌号变化了，%d",table_id)
            return
        if not self.is_game_ready and not self.in_game:
            ch = self.decide(50,10,10,10)
            if ch == 0:
                self.info("没有开始游戏，机器人不耐烦，换桌",color=color.strong)
                self.change_table(table_id)
            elif ch >=1 and ch <= 3:
                self.send_emotion(EMOTION_WAIT_TOO_LONG[ch])
                gevent.spawn_later(6,self.wait_ready_too_long_2,table_id)
            else:
                gevent.spawn_later(random.randint(5,8),self.wait_ready_too_long_2,table_id)

    def wait_ready_too_long_2(self,table_id):
        if not self.is_same_table(table_id):
            self.info("wait_ready_too_long_2,等待太长时间，且桌号变化了，%d",table_id)
            return
        if not self.is_game_ready:
            self.info("没有开始游戏，机器人实在不耐烦，换桌",color=color.strong)
            self.change_table(table_id)

    def handle_game_ready_event(self,req):
        self.is_game_ready = True

    def handle_game_cancel_event(self,req):
        self.is_game_ready = False

    def handle_game_start_event(self,event):
        self.round_min_bet = TABLE_GAME_CONFIG[self.table_type][2]
        self.action_gold = TABLE_GAME_CONFIG[self.table_type][2]

        for player_gold in event.body.player_golds:
            player = GamblerPlayer(player_gold.uid)
            self.players[player.uid] = player

        pokers_str = self.manager.redis.hget("pokers" , self.table_id)
        self.info("游戏开始了,%s",str(self.players.keys()))
        pokers = json.loads(pokers_str)

        for poker_data in pokers:
            uid = poker_data["uid"]
            p1 = poker_data["p1"].split("-")
            poker1 = Poker(int(p1[0]),int(p1[1]))
            p2 = poker_data["p2"].split("-")
            poker2 = Poker(int(p2[0]),int(p2[1]))
            p3 = poker_data["p3"].split("-")
            poker3 = Poker(int(p3[0]),int(p3[1]))

            player_pokers = PlayerPokers(uid,poker1,poker2,poker3)
            if uid in self.players:
                self.players[uid].pokers = player_pokers

            if uid == self.robot_id:
                self.my_pokers = player_pokers

        self.is_game_start = True
        self.same_table_games += 1
        if self.same_table_games > 3:
            self.leave_table_rate += 5

        self.in_game = False
        for player_gold in event.body.player_golds:
            if player_gold.uid == self.robot_id:
                self.in_game = True
                break

        if self.in_game:
            self.x = 1
            for k,player in self.players.items():
                if k == self.robot_id:
                    continue

                if player.pokers.compare(self.my_pokers) > 0:
                    self.x = 0
                    break

    def get_players_state(self):
        s = ""
        for uid,p in self.players.items():
            s += "[%d-%s-%s]" % (uid,"看" if p.is_see else "未看","败" if p.is_fail else "")
        return s

    def handle_game_over_event(self,req):
        self.info("游戏结束了")
        if self.in_game:
            if req.body.winner == self.robot_id:
                self.game_results.append(1)
            else:
                self.game_results.append(0)

            if sum(self.game_results[-3:]) == 3:
                gevent.spawn_later(random.randint(50,70)/10.0,self.talk_random,WIN_3_GAMES)

            win_gold = req.body.gold if req.body.winner == self.robot_id else 0
            for player_gold in req.body.player_golds:
                if player_gold.uid == self.robot_id:
                    win_gold -= player_gold.bet_gold
                    self.gold = player_gold.gold

            session = Session()
            session.begin()
            try :
                self.row_robot = session.query(TRobot).filter(TRobot.uid == self.robot_id).first()
                self.row_robot.win_gold += win_gold
                session.commit()
            except:
                traceback.print_exc()
                session.rollback()
            finally:
                session.close()
                session = None

        if self.same_table_games >= 5 and random.randint(1,100) < self.leave_table_rate:
            self.info("连续在一个桌上了玩了5把，具备离座条件，换桌，离座概率%d",self.leave_table_rate,color=color.strong)
            if self.last_action in (COMPARE,SHOW_HAND):
                gevent.spawn_later(random.randint(110,130)/10.0,self.change_table,self.table_id)
            else:
                gevent.spawn_later(random.randint(70,80)/10.0,self.change_table,self.table_id)
        else:
            if not self.should_quit():
                if self.last_action in (COMPARE,SHOW_HAND):
                    gevent.spawn_later(random.randint(110,130)/10.0,self.decide_after_game_over,self.table_id)
                else:
                    gevent.spawn_later(random.randint(70,80)/10.0,self.decide_after_game_over,self.table_id)

        self.reset_game()


    def decide_after_game_over(self,table_id):
        if not self.is_same_table(table_id):
            self.error("游戏正常结束后后续处理，桌号变化 %d",table_id)
            return

        if self.should_quit():
            return

        if self.gold < TABLE_GAME_CONFIG[TABLE_L][0]:
            self.init_gold()
            self.change_table(table_id)
            return
        if self.gold < 50000 and self.table_type == TABLE_M:
            self.change_table(table_id)
        else:
            self.info("继续新一局游戏")
            self.set_player_ready(table_id)



    def handle_bet_action_resp(self,resp):
        if resp.header.result == RESULT_FAILED_LESS_GOLD and self.current == self.robot_id:
            self.info(" 没有足够的钱，放弃====> ",color=color.red)
            req = create_client_event(BetActionReq,self.robot_id)
            req.body.action = GIVE_UP
            req.body.table_id = self.table_id
            gevent.spawn_later(1,self.forward_message,req)
        elif resp.header.result != 0:
            self.info(" bet 操作失败，不应该发生 %d",resp.header.result,color=color.red_bg)

    def see_poker_in_other_turn(self):
        if not self.in_game or self.is_fail:
            return

        if self.current == self.robot_id:
            return

        if self.decide_see_poker():
            action = self.bet_strategy.get_bet_action()
            if action[0] == GIVE_UP:
                self.bet_strategy.bet(GIVE_UP)

    def handle_bet_action_event(self,event):
        if not self.in_game:
            return

        if event.body.player == self.robot_id:
            self.info(" 下注信息，用户:%d,动作：%s,金币：%d,对手：%d,赢家:%d,%s",event.body.player,BetAction.Name(event.body.action),
                  event.body.action_gold,event.body.other,event.body.compare_winner,self.get_players_state(),color=color.green)
            if event.body.action not in (SEE_POKER,GIVE_UP):
                self.gold = event.body.gold

        player = self.players.get(event.body.player,None)
        if player == None:
            self.info("something wrong %s",self.players,color=color.red_bg)
            return

        self.last_action = event.body.action

        if event.body.action == GIVE_UP:
            if event.body.player in self.players:
                self.players[event.body.player].is_fail = True
            if event.body.player == self.robot_id:
                self.is_fail = True
        elif event.body.action == COMPARE:
            if event.body.player == self.robot_id or event.body.other == self.robot_id:
                self.b = 0
            two = [event.body.player,event.body.other]
            two.remove(event.body.compare_winner)
            loser = two[0]

            if loser in self.players:
                self.players[loser].is_fail = True
            if loser == self.robot_id:
                self.is_fail = True
                # 发送互动表情
                if random.randint(0,100) < 5:
                    gevent.spawn_later(random.randint(20,40)/10.0,self.send_interact_emotion,event.body.compare_winner,random.randint(2,5),1)

        elif event.body.action == SHOW_HAND:
            self.is_show_hand = True
            if event.body.player == self.robot_id:
                gevent.spawn_later(random.randint(10,20)/10.0,self.talk_random,CHAT_SHOW_HAND)

        elif event.body.action == SEE_POKER:
            self.players[event.body.player].is_see = True

            if event.body.player != self.robot_id:
                self.is_other_see = True
            else:
                self.is_see = True

            if event.body.player == self.robot_id and self.current == self.robot_id:
                # 看完牌后进行操作
                self.bet_strategy.do_bet_action()

        elif event.body.action in (FOLLOW,ADD):
            if self.players[event.body.player].is_see:
                self.round_min_bet = event.body.action_gold / 2
            else:
                self.round_min_bet = event.body.action_gold


        if event.body.action in (FOLLOW,ADD,SHOW_HAND,COMPARE):
            if self.players[event.body.player].is_see:
                self.action_gold = event.body.action_gold / 2
            else:
                self.action_gold = event.body.action_gold

        # 对手看牌且还在座位上
        see_poker_players = [player for player in self.players.values() if player.uid != self.robot_id
                                                and player.is_see and not player.is_fail]
        self.k = 1 if len(see_poker_players) != 0 else 0

        # 有人加注／有人看牌后跟注／有人比牌
        if not self.is_fail and not self.is_see and event.body.player != self.robot_id \
                    and not self.is_next_table_player(event.body.player,self.robot_id):
            if event.body.action == ADD or \
                ( event.body.action == COMPARE and self.robot_id not in (event.body.player,event.body.other))  or \
                ( event.body.action == FOLLOW and self.players[event.body.player].is_see):
                gevent.spawn_later(random.randint(1,2),self.see_poker_in_other_turn)

        if self.is_fail and event.body.action in (GIVE_UP,COMPARE):
            delay = random.randint(1,2) if event.body.action == GIVE_UP else random.randint(3,5)

            if len(self.game_results) >= 5 and sum(self.game_results[-5:]) == 0:
                gevent.spawn_later(random.randint(50,70)/10.0,self.talk_random,LOST_5_GAMES)

            if self.same_table_games >= 5 and random.randint(1,100) < self.leave_table_rate:
                self.info("自己失败了，离桌 ，离桌概率为 %d",self.leave_table_rate,color=color.strong)
                gevent.spawn_later(delay,self.change_table,self.table_id)

        if event.body.action in (COMPARE,ADD,FOLLOW,SHOW_HAND) and event.body.player == self.robot_id:
            self.total_bet_gold += event.body.bet_gold


    def handle_game_turn_event(self,event):
        self.current = event.body.current
        self.round = event.body.round
        if event.body.current != self.robot_id:
            # 首次回合后可以看牌
            self.can_see = True
            gevent.spawn_later(random.randint(11,14),self.wait_player_bet_action,self.current,self.round)
            gevent.spawn_later(random.randint(10,13),self.wait_player_bet_action_emotion,self.current,self.round)
            return
        gevent.spawn_later(1,self.think)

    def wait_player_bet_action(self,current,round):
        if self.current != current or round != self.round:
            return
        if random.randint(0,100) < 3:
            if self.sex == 0:
                self.send_chat(1)
            else:
                self.send_chat(5)

    def wait_player_bet_action_emotion(self,current,round):
        if self.current != current or round != self.round:
            return
        if random.randint(0,100) < 2:
            self.send_interact_emotion(current,random.randint(2,5),1)

    def think(self):
        if not self.in_game or self.is_fail:
            return
        if self.is_see:
            self.bet_strategy.do_bet_action()
        else:
            if not self.decide_see_poker():
                self.bet_strategy.do_bet_action()

        self.can_see = True

    def decide_see_poker(self):
        if self.is_see or not self.can_see:
            return False
        if self.type == ROBOT_BAOSHOU:
            if not self.is_other_see:
                rate = 45 + (self.round + 1 - self.x) * 5 - 30 * self.b
            elif self.round_min_bet >= TABLE_GAME_CONFIG[self.table_type][3]:
                rate = 55 + (self.round + 1 - self.x) * 8 - 30 * self.b
            else:
                rate = 65 + (self.round + 1 - self.x) * 12 - 30 * self.b
        elif self.type == ROBOT_PINGHENG:
            if not self.is_other_see:
                rate = 25 + (self.round + 1 - self.x) * 3 - 20 * self.b
            elif self.round_min_bet >= TABLE_GAME_CONFIG[self.table_type][3]:
                rate = 30 + (self.round + 1 - self.x) * 5 - 20 * self.b
            else:
                rate = 40 + (self.round + 1 - self.x) * 8 - 20 * self.b
        elif self.type == ROBOT_JIJIN:
            if not self.is_other_see:
                rate = 15 * self.b + (self.round + 1 - self.x) * 2 - 10 * self.b
            elif self.round_min_bet >= TABLE_GAME_CONFIG[self.table_type][3]:
                rate = 25 + (self.round + 1 - self.x) * 3 - 10 * self.b
            else:
                rate = 35 + (self.round + 1 - self.x) * 5 - 10 * self.b

        if self.table_type == TABLE_L:
            rate = 70 if rate < 70 and self.total_bet_gold >= 6000 else rate
        elif self.table_type == TABLE_M:
            rate = 70 if rate < 70 and self.total_bet_gold >= 40000 else rate
        elif self.table_type == TABLE_H:
            rate = 70 if rate < 70 and self.total_bet_gold >= 20000 else rate
        elif self.table_type == TABLE_H2:
            rate = 70 if rate < 70 and self.total_bet_gold >= 1000000 else rate

        if rate >= 100 or random.randint(1,100) <= rate:
            self.info("选择看牌")
            req = create_client_event(BetActionReq,self.robot_id)
            req.body.action = SEE_POKER
            req.body.table_id = self.table_id
            self.forward_message(req)
            return True
        return False


    # ====> 添加好友逻辑
    def make_friend(self,uid):
        req = create_client_event(MakeFriendReq)
        req.header.user = self.robot_id
        req.body.target = uid
        req.body.message = u""
        self.forward_message(req)


    def handle_get_friends_resp(self,event):
        if event.header.result < 0:
            return
        friend_ids = [f.uid for f in event.body.friends]
        removed = int(0.5 * len(friend_ids))

        for _ in xrange(removed):
            friend_id = random.choice(friend_ids)
            friend_ids.remove(friend_id)
            req = create_client_event(RemoveFriendMessageReq)
            req.header.user = self.robot_id
            req.body.friend_id = friend_id
            self.forward_message(req)
        gevent.sleep(0.1)
        self.can_add_friend = True

    def handle_get_friend_applies_resp(self,event):
        if event.header.result < 0:
            return
        self.can_add_friend = True
        for ap in event.body.applies:
            if self.can_add_friend:
                gevent.spawn_later(random.randint(5,10),self.do_handle_apply,ap.id,random.randint(0,100) > 20)

    def do_handle_apply(self,apply_id,accept):
        req = create_client_event(HandleFriendApplyReq)
        req.header.user = self.robot_id
        req.body.apply_id = apply_id
        req.body.accept = accept
        self.forward_message(req)

    def handle_handle_apply_resp(self,event):
        if event.header.result < 0:
            self.can_add_friend = False
            self.remove_friends()

    def remove_friends(self):
        req = create_client_event(GetFriendsReq)
        req.header.user = self.robot_id
        req.body.page = 1
        req.body.page_size = 1000
        self.forward_message(req)


    def handle_notify_event(self,event):
        if event.body.type == N_FRIEND_APPLY:
            self.do_handle_friend_apply_event()

    def do_handle_friend_apply_event(self):
        req = create_client_event(GetFriendAppliesReq)
        req.header.user = self.robot_id
        req.body.page = 1
        req.body.page_size = 1000
        self.forward_message(req)

    # =====> 结束好友逻辑

    def shutdown(self):
        req = create_client_event(QuitGameServerReq)
        req.header.user = self.robot_id
        self.forward_message(req)

        self.manager.robots.pop(self.robot_id,None)
        self.manager.prepare_robots.pop(self.robot_id,None)

    def check_quit_condition(self):
        while True:
            gevent.sleep(10)
            if self.should_quit():
                if self.in_game:
                    self.info("机器人应该退出，但是现在还在游戏中",color=color.red_bg)
                    continue

                req = create_client_event(QuitGameServerReq)
                req.header.user = self.robot_id
                self.service.forward_message(req.header,req.encode())
                self.info("机器人退出 !!!",color=color.blue)
                break
                """
                if self.cant_play:
                    session = Session()
                    try :
                        session.begin()
                        row_robot = session.query(TRobot).filter(TRobot.uid == self.robot_id).first()
                        row_robot.state = 2
                        session.commit()
                    except:
                        traceback.print_exc()
                        session.rollback()
                    finally:
                        session.close()
                        session = None
                break
                """

        self.manager.robots.pop(self.robot_id,None)


    def send_chat(self,message):
        data = {}
        data["type"] = 2
        data["uid"] = self.robot_id
        data["nick"] = self.row_robot_user.nick
        data["vip"] = self.row_robot_user.vip
        data["seat"] = self.seat
        data["content"] = message

        req = create_client_event(SendChatReq,self.robot_id)
        req.body.table_id = self.table_id
        req.body.chat_type = CHAT_ZJH
        req.body.message = json.dumps(data)
        self.forward_message(req)

    def send_emotion(self,emotion):
        self.info("机器人发表情：%d", emotion,color=color.underline )
        data = {}
        data["type"] = 1
        data["uid"] = self.robot_id
        data["nick"] = self.row_robot_user.nick
        data["vip"] = self.row_robot_user.vip
        data["seat"] = self.seat
        data["content"] = str(emotion)

        req = create_client_event(SendChatReq,self.robot_id)
        req.body.table_id = self.table_id
        req.body.chat_type = CHAT_ZJH
        req.body.message = json.dumps(data)
        self.forward_message(req)

    def send_interact_emotion(self,player,emotion_id,count):
        self.info("机器人发互动表情:%d,%d,%d",player,emotion_id,count)
        if player == -1:
            raise Exception("player is -1")
        req = create_client_event(SendEmotionReq,self.robot_id)
        req.body.table_id = self.table_id
        req.body.target_player = player
        req.body.emotion_id = emotion_id
        req.body.count = count

        self.forward_message(req)

    def talk_random(self,talks):
        rates = [r[0] for r in talks]
        ch = self.decide(*rates)
        if ch >= len(talks):
            return
        talk = talks[ch]
        if talk[1] < 0:
            return
        if talk[1] == 1:
            self.send_emotion(talk[2])
        elif talk[1] == 2:
            self.send_chat(talk[2])

    def get_suitable_table_type(self):
        if self.gold < TABLE_GAME_CONFIG[TABLE_L][0]:
            self.init_gold()

        need_table_type = self.manager.get_required_robot_table_type()

        if need_table_type < 0:
            if self.gold < 160000:
                table_type = TABLE_L
            elif self.gold < 1500000:
                table_type = TABLE_M
            elif self.gold < 6000000:
                table_type = TABLE_H
            else:
                table_type = TABLE_H2
        else:
            self.set_gold_by_table_type(need_table_type,self.gold)
            table_type = need_table_type

        return table_type


    def set_gold_by_table_type(self,table_type,gold):
        l_gold,h_gold = RECHARGE_GOLD.get(table_type)
        if l_gold <= gold <= h_gold:
            return
        gold = random.randint(l_gold,h_gold)
        self.gold = gold
        self.manager.recharge_to(self.robot_id,gold)


    def change_table(self,table_id):
        if self.is_table_changing:
            self.error("准备换桌，但是正在换桌中")
            return

        if self.table_id != table_id:
            self.error("准备换桌，桌号已经发生改变 %d",table_id)
            return

        self.is_table_changing = True

        self.info("换桌，原桌=%d,not_tables =%s",self.table_id,str(self.table_ids[-3:]),color=color.strong)
        if self.room_id >= 0:
            req = create_client_event(LeaveTableReq,self.robot_id)
            req.header.route = self.room_id
            req.body.table_id = self.table_id
            self.forward_message(req)
            gevent.sleep(3)

        not_tables = self.table_ids[-3:]
        table_type = self.get_suitable_table_type()

        self.is_table_changing = True

        req = create_client_event(SitTableReq,self.robot_id)
        req.body.table_id = -1
        req.body.table_type = table_type
        last_tables = not_tables
        req.body.not_tables.extend(last_tables)

        self.info("已经离桌，尝试坐新桌 %s",str(last_tables),color=color.strong)

        self.forward_message(req)


    def handle_leave_table_resp(self,resp):
        self.info("离开牌桌 %d",resp.header.result,color=color.strong)
        if resp.header.result != 0:
            return
        self.reset_table()


    def handle_table_event(self,req):
        if req.body.event_type == PLAYER_JOIN:
            if req.body.player in self.table_players:
                return
            brief = req.body.player_brief
            self.table_players[req.body.player] = TablePlayer(req.body.player,brief.seat)
        elif req.body.event_type == PLAYER_LEAVE:
            if not req.body.player in self.table_players:
                return
            self.table_players.pop(req.body.player)
        elif req.body.event_type == PLAYER_KICKED and req.body.player != self.robot_id:
            if not req.body.player in self.table_players:
                return
            self.table_players.pop(req.body.player)

        if req.body.event_type == PLAYER_KICKED and req.body.player == self.robot_id:
            self.info("被踢出",color=color.red)
            self.reset_table()
            self.sit_table()

    def next_table_player(self,uid):
        if len(self.table_players) <= 1:
            return None
        if self.table_players.get(uid) == None:
            return None
        seat = self.table_players.get(uid).seat
        players = [p for p in self.table_players.values() if p.seat > seat]
        if len(players) == 0:
            player = min(self.table_players.values(),key = lambda x:x.seat)
        else:
            player = min(players,key = lambda x:x.seat)
        return player

    def is_next_table_player(self,uid,next_uid):
        player = self.next_table_player(uid)
        if player != None and player.uid == next_uid:
            return True
        return False

    def decide(self,*args):
        r = random.randint(0,100)
        total = 0
        for k,p in enumerate(args):
            total += p
            if r <= total:
                return k
        return len(args)

def timestr_to_seconds(timestr):
    hm_str = timestr.split(":")
    hour = int(hm_str[0])
    min = int(hm_str[1])
    return hour * 3600 + min * 60

def random_time(segs_str):
    segs = segs_str.split("-")
    begin = timestr_to_seconds(segs[0])
    end = timestr_to_seconds(segs[1])

    seconds = random.randint(begin,end)
    h = seconds / 3600
    m = (seconds % 3600) / 60
    s = seconds - h * 3600 - m * 60
    return dt_time(h,m,s)

def random_duration(segs_str):
    segs = segs_str.split("-")
    dur = random.randint(int(segs[0]),int(segs[1]))
    dur = 60 if dur < 60 else dur
    return dur

def seconds_between_times(time1,time2, offset = 0):
    seconds1 = time1.hour * 3600 +time1.minute * 60 + time1.second
    seconds2 = time2.hour * 3600 +time2.minute * 60 + time2.second

    return abs(seconds1 - seconds2 - offset)

class RobotManager:
    def __init__(self,service):
        self.service = service
        if service != None:
            self.redis = service.server.redis
        else:
            self.redis = None

        self.robots = {}
        self.prepare_robots = {}
        self.redis.delete("online_robots")

        gevent.spawn(self.manage_robots_console) # 提供在线接口，可以在线进行robot的加载或者停止
        gevent.spawn(self.startup_ready_robots) # 启动符合条件的robot，每隔30秒检查一次
        gevent.spawn_later(1,self.redis.lpush,"robot_cmd","loadall") # 启动时加载所有robot

        gevent.spawn_later(10,self.reload_all_robots_everyday) # 每天3点开始重新加载更新所有robot配置
        #gevent.spawn(self.check_table)

    def shutdown(self):
        for robot in self.robots.values():
            robot.shutdown();
        time.sleep(5)

    def handle_user_online(self,session,uid):
        if uid in self.robots:
            return

        friend_apply = session.query(TFriendApply).filter(TFriendApply.to_uid == uid).first()
        if friend_apply != None:
            return

        user_gf = session.query(TUserGoldFlower).filter(TUserGoldFlower.id == uid).first()
        if user_gf == None or user_gf.total_games == 0:
            robot = random.choice(self.robots.values())
            if robot != None:
                gevent.spawn_later(random.randint(180,300),robot.make_friend,uid)

        #robot = random.choice(self.robots.values())
        #if robot != None and robot.robot_id != uid:
        #    gevent.spawn_later(random.randint(1,2),robot.make_friend,uid)

    # just for testing
    def check_table(self):
        while True:
            user_table_map = self.redis.hgetall("room_users_210")

            keys = self.redis.keys("table_*")
            for k in keys:
                if k == "table_id":
                    continue
                users = self.redis.hgetall(k).keys()
                table_id = k[10:]

                for u in users:
                    if user_table_map.get(u) == table_id:
                        continue
                    logging.info(color.red("user[%s]/table[%s] is not correct,map=%s"),u,table_id,user_table_map.get(u))

            gevent.sleep(1)


    def reload_all_robots_everyday(self):
        loaded_date = datetime.now().date()

        while True:
            now = datetime.now()
            if now.date() != loaded_date and now.time().hour >= 3:
                loaded_date = now.date()
                gevent.spawn_later(1,self.redis.lpush,"robot_cmd","loadall")
            gevent.sleep(60)

    def manage_robots_console(self):
        while True:
            _,cmd = self.redis.brpop("robot_cmd")
            logging.info(color.blue("收到机器人命令：%s"),cmd)
            if cmd == "loadall":
                self.prepare_robots = {}
                row_robots = None
                session = Session()
                try :
                    row_robots = session.query(TRobot).filter(TRobot.state == 1).all()
                except:
                    traceback.print_exc()
                finally :
                    session.close()
                    session = None

                self.prepare_robots = {}

                for row_robot in row_robots:
                    self.load_prepare_robot(row_robot)

                logging.info(color.blue("=======> 机器人启动时间: %s"),self.prepare_robots)
            elif cmd.startswith("load"):
                robot_id = int(cmd[len("load"):])
                session = Session()
                row_robot = None
                try :
                    row_robot = session.query(TRobot).filter(TRobot.uid == robot_id).first()
                finally :
                    session.close()
                    session = None
                if row_robot == None or row_robot.state != 1:
                    logging.info(color.blue("robot is not exist or wrong state"))
                    continue
                self.load_prepare_robot(row_robot)
                logging.info(color.blue("done"))
            elif cmd == "stopall":
                self.prepare_robots = {}
                for _,robot in self.robots.items():
                    robot.has_quit_command = True
                logging.info(color.blue("=======> all robots[%d] quit now"),len(self.robots))
            elif cmd.startswith("stop"):
                robot_id = int(cmd[len("stop"):])
                robot = self.robots.get(robot_id)
                if robot == None:
                    logging.info(color.blue("robot is not exist"))
                    continue

                robot.has_quit_command = True
                logging.info(color.blue("done"))
            elif cmd == "shutdownall":
                self.prepare_robots = {}
                count = len(self.robots)
                for _,robot in self.robots.items():
                    robot.shutdown()
                logging.info(color.blue("=======> all robots[%d] shutdown now"),count)

            elif cmd.startswith("shutdown"):
                robot_id = int(cmd[len("shutdown"):])
                robot = self.robots.get(robot_id)
                if robot == None:
                    logging.info(color.blue("robot is not exist"))
                    continue

                robot.shutdown()
                logging.info(color.blue("done"))

    # 启动缓存中机器人
    def startup_ready_robots(self):
        loop_seconds = 15
        startup_trys = {}
        while True:
            now = datetime.now().time()
            for robot_id,start_times in self.prepare_robots.items():
                if robot_id in self.robots:
                    continue
                ready = False
                startup_round_time = None
                for t in start_times:
                    #t1 = seconds_between_times(t[0],now);
                    #t2 = seconds_between_times(t[0],now,24*3600)
                    #logging.info(color.red("check rebot %d now ... %d,%d | " + str(t[0]) + "," + str(t[1])),robot_id,t1,t2);
                    if robot_id in startup_trys:
                        startup_try = startup_trys[robot_id]
                        if startup_try[0] == dt_date.today() and startup_try[1] == t[0]:
                            continue
                    if t[0] <= now and seconds_between_times(t[0],now) < t[1]:
                        startup_round_time = t[0]
                        ready = True
                        break
                    if t[0] >= now and seconds_between_times(t[0],now , 24 * 3600) < t[1]:
                        startup_round_time = t[0]
                        ready = True
                        break
                if not ready:
                    continue
                logging.info(color.blue("启动机器人 %d"),robot_id)
                startup_trys[robot_id] = (dt_date.today(),startup_round_time)

                if random.randint(0,100) < 75: # 50% percent robots will startup
                    robot = Robot(self,robot_id,t[0],t[1])
                    robot.start()
                    self.robots[robot_id] = robot

            counters = {}
            idle_robots = []
            for robot in self.robots.values():
                if robot.table_type in counters:
                    counters[robot.table_type] += 1
                else:
                    counters[robot.table_type] = 1
                if robot.table_type < 0:
                    idle_robots.append(robot.robot_id)

            logging.info(color.blue(color.strong("[[[ There are %d robots online %s ]]] ")),len(self.robots),counters)
            logging.info(color.blue(color.strong("[[[ online idle robots %s ]]]")),str(idle_robots))

            gevent.sleep(loop_seconds)

    def get_robot_counters(self):
        counters = {}
        idle_robots = []
        for robot in self.robots.values():
            if robot.table_type in counters:
                counters[robot.table_type] += 1
            else:
                counters[robot.table_type] = 1
            if robot.table_type < 0:
                idle_robots.append(robot.robot_id)
        return idle_robots,counters

    def get_required_robot_table_type(self):
        counters = {}
        for robot in self.robots.values():
            if robot.table_type in counters:
                counters[robot.table_type] += 1
            else:
                counters[robot.table_type] = 1

        total = len(self.robots)
        for t in (TABLE_H2,TABLE_H,TABLE_M,TABLE_L):
            if t in counters:
                c = counters[t]
            else:
                c = 0
            min_c = int(total * ROBOTS_PERCENT[t] * 0.8 * 0.01)
            #max_c = int(total * ROBOTS_PERCENT[t] * 1.2 * 0.01)

            if c >= min_c:
                continue
            return t
        return -1



    def get_robot(self,robot_id):
        return self.robots.get(robot_id,None)

    def load_prepare_robot(self,row_robot):
        segs = row_robot.online_times.split(",")
        start_times = []
        for seg in segs:
            s = seg.split("|")
            robot_start_time = random_time(s[0])
            robot_duration = random_duration(s[1])
            start_times.append((robot_start_time,robot_duration,))

        start_times.sort(cmp=lambda x,y:cmp(x[0],y[0]))
        self.prepare_robots[row_robot.uid] = start_times

    def recharge_to(self,robot_id,gold):
        session = Session()
        try :
            session.begin()
            row_user = session.query(TUser).filter(TUser.id == robot_id).first()

            if row_user.gold == gold:
                return 0
            if row_user.gold < gold:
                dbhelper.provide_gold(session,type=0,gold=gold - row_user.gold,uid=robot_id)
            else:
                dbhelper.recycle_gold(session,type=0,gold=gold - row_user.gold,uid=robot_id)
            row_user.gold = gold
            session.commit()
            DataAccess(self.redis).get_user(robot_id,must_update=True)
            return row_user.gold
        except:
            traceback.print_exc()
            session.rollback()
        finally:
            session.close()
            session = None
        return -1

    def recharge(self,robot_id,gold):
        session = Session()
        try :
            session.begin()
            row_user = session.query(TUser).filter(TUser.id == robot_id).first()
            row_user.gold += gold
            dbhelper.provide_gold(session,type=0,gold=gold,uid=robot_id)
            session.commit()
            DataAccess(self.redis).get_user(robot_id,must_update=True)
            return row_user.gold
        except:
            traceback.print_exc()
            session.rollback()
        finally:
            session.close()
            session = None
        return -1

        
if __name__ == '__main__':
    
    pass
