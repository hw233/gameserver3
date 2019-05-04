# -*- coding: utf-8 -*-
__author__ = 'Administrator'
import gevent
from gevent import monkey;monkey.patch_all()

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import traceback
import logging
import random
import redis
import collections
import itertools

from collections import Counter,namedtuple
from datetime import datetime,timedelta
from datetime import date as dt_date
from datetime import time as dt_time

from message.base import *
from util.commonutil import *

from db.connect import *
from db.robot_texas import *
from dal.core import *

from proto.access_pb2 import *
from proto.constant_pb2 import *
from proto import struct_pb2 as pb2

from proto.texas_pb2 import *
from texasconf import TABLE_GAME_CONFIG,TEXAS_MIN_GOLD
from texas import PlayerPokers,PokerManager
from message.resultdef import *

# 1k，2k，5k，1w，2w，5w，10w，20w，50w，100w，200w，500万，1000w，2000w，5000w
BET_GOLDS = [1000,2000,5000,10000,20000,50000,100000,200000,500000,1000000,2000000,5000000,10000000,20000000,50000000]

class Robot:
    PLAYING = 0
    OFFLINE = 1
    GOLD_LESS = 2
    CHANGE_TABLE = 3
    def __init__(self, manager, robot_id, start_time, duration):
        self.start_time = datetime.combine(datetime.today(),start_time)
        self.end_time = self.start_time + timedelta(seconds = duration)
        self.has_quit_command = False

        self.robot_id = robot_id

        self.manager = manager
        self.service = manager.service

        session = Session()
        try :
            self.row_robot = session.query(TRobotTexas).filter(TRobotTexas.uid == robot_id).first()
            self.row_robot_user = session.query(TUser).filter(TUser.id == robot_id).first()
        except:
            traceback.print_exc()
            session.rollback()
        finally:
            session.close()
            session = None

        # self.sex = self.row_robot_user.sex

        self.history_table_ids = []
        self.gold = self.row_robot_user.gold
        self.strategy = BetStrategy(self)

        self.reset_table()
        self.init_gold()

    def reset_table(self):
        self.room_id = -1
        self.table_id = -1
        self.table_type = -1
        self.seat = -1
        self.table = None

        self.play_count = 0
        self.play_count_rate = 30

        self.reset_game()

    def reset_game(self):
        self.wait_leave = False
        self.action = WATCH
        self.bet_low_gold = 0
        self.poker = TexasPokers()

    def sit_table(self):
        new_table_type = self.manager.get_table_type()
        if new_table_type == 1:
            new_gold = random.randint(40000, 200000)
            self.manager.recharge_to(self.robot_id, new_gold)
            self.info('重新设置金币=%d，进入低级场' % new_gold)
        elif new_table_type == 2:
            new_gold = random.randint(400000, 8000000)
            self.manager.recharge_to(self.robot_id, new_gold)
            self.info('重新设置金币=%d，进入中级场' % new_gold)
        elif new_table_type == 3:
            new_gold = random.randint(15000000, 35000000)
            self.manager.recharge_to(self.robot_id, new_gold)
            self.info('重新设置金币=%d，进入高级场' % new_gold)
        else:
            self.info('没有选择出场次不进行金币设置')

        self.info("试图坐下")
        req = create_client_event(TexasSitTableReq)
        req.header.user = self.robot_id
        req.body.table_id = -1
        for t_id in self.history_table_ids:
            req.body.not_tables.append(t_id)
        self.forward_message(req)

    def sit_table_first(self):

        self.info("试图坐下")
        req = create_client_event(TexasSitTableReq)
        req.header.user = self.robot_id
        req.body.table_id = -1
        for t_id in self.history_table_ids:
            req.body.not_tables.append(t_id)
        self.forward_message(req)

    def leave_table(self):
        self.info('选择离开')
        req = create_client_event(TexasLeaveTableReq,self.robot_id)
        req.header.route = self.room_id
        req.body.table_id = self.table_id
        self.forward_message(req)

    def bet_add(self):
        bet_gold = self.strategy.choice_start_gold(self.gold)
        self.bet_low_gold = bet_gold

        self.info('参加游戏，底注=%d，彩金=%d' % (bet_gold, bet_gold))
        self.bet(BET, TEXAS_START, bet_gold, bet_gold)

    def bet_pass(self, texas_status):
        self.info('PASS')
        self.bet(PASS, texas_status)

    def bet_watch(self):
        self.info('WATCH')
        self.bet(WATCH, TEXAS_START)

    def bet_add_bei(self, texas_status, multiple):
        self.info('ADD_BEI')
        add_bei_gold = self.bet_low_gold * multiple
        self.bet(ADD_BEI, texas_status, add_bei_gold)

    def bet_giveup(self):
        self.info('GIVEUP')
        self.bet(GIVEUP, TEXAS_PUBLIC_5)

    def bet(self, bet_type, texas_status, action_gold = 0, bet_reward_gold = 0):

        self.info('状态=%d，动作=%d，金币=%d，奖金=%d' % (texas_status, bet_type, action_gold, bet_reward_gold))
        req = create_client_event(TexasBetActionReq, self.robot_id)
        req.body.table_id = self.table_id
        req.body.bet_type = bet_type
        req.body.texas_status = texas_status
        if action_gold > 0:
            req.body.action_gold = action_gold
        if bet_reward_gold > 0:
            req.body.bet_reward_gold = bet_reward_gold

        self.forward_message(req)
        # gevent.spawn(self.forward_message,req)

    def handle_bet_event(self, event):
        if event.header.result == RESULT_FAILED_LESS_GOLD:
            self.info('钱不够了gold=%d===》',self.gold,color=color.red)
            self.check_robot_status()
        elif event.header.result != 0:
            self.info('投注发生了错误，可能服务端游戏投注状态已经变更gold=%d===》', self.gold, color=color.red)
        elif event.header.result == 0:
            self.action = event.body.bet_type
            if self.action == BET:
                self.gold = event.body.gold
                self.info('参与，阶段=%d，共投注金币=%d，动作=%d' % (event.body.texas_status, event.body.bet_gold, event.body.bet_type))
            elif self.action == ADD_BEI:
                self.gold = event.body.gold
                self.info('倍注，阶段=%d，共投注金币=%d，动作=%d' % (event.body.texas_status, event.body.bet_gold, event.body.bet_type))
        else:
            raise u"机器人=%d收到投注事件，但是没有匹配类型！" % self.robot_id

    def handle_sit_table_resp(self, resp):
        self.reset_table()

        self.room_id = resp.body.room_id
        self.table = resp.body.table
        self.table_id = resp.body.table.id
        self.wait_leave = False
        self.append_history_table(self.table_id)

        if len([x for x in resp.body.table.player_briefs if x.uid in self.manager.robots]) == 5:
            self.info('发现牌桌已经有5个机器人在了，换桌重进')
            self.wait_leave = True
            gevent.spawn_later(2, self.leave_table)
            gevent.spawn_later(4, self.sit_table)
            return

        self.info('机器人=%d进入牌桌=%d了' % (self.robot_id, self.table_id))
        if len(resp.body.table.player_briefs) == 3:
            if random.randint(1, 100) <= 20:
                self.info('机器人=%d有百分之20的概率延迟重进，牌桌=%d内已有3个人' % (self.robot_id, self.table_id))
                self.wait_leave = True
                gevent.spawn_later(random.randint(2, 10), self.leave_table)
                gevent.spawn_later(11, self.sit_table)
        elif len(resp.body.table.player_briefs) == 4:
            if random.randint(1, 100) <= 40:
                self.info('机器人=%d有百分之40的概率延迟重进，牌桌=%d内已有4个人' % (self.robot_id, self.table_id))
                self.wait_leave = True
                gevent.spawn_later(random.randint(2, 10), self.leave_table)
                gevent.spawn_later(11, self.sit_table)
        elif len(resp.body.table.player_briefs) == 5:
            if random.randint(1, 100) <= 60:
                self.info('机器人=%d有百分之60的概率延迟重进，牌桌=%d内已有5个人' % (self.robot_id, self.table_id))
                self.wait_leave = True
                gevent.spawn_later(random.randint(2, 10), self.leave_table)
                gevent.spawn_later(11, self.sit_table)
        else:
            if resp.body.table.texas_status == TEXAS_WAIT or resp.body.table.texas_status == TEXAS_START:
                if 2 < resp.body.table.remain_seconds < 8:
                    self.info('机器人半路进来，在 2 < %d < 8 时间范围内可以投注' % (resp.body.table.remain_seconds))
                    self.bet_add()

    def check_robot_status(self):
        if self.not_enough_gold():
            self.info('金币不足，退出后充值，再进入')
            sec = random.randint(1, 2)
            gevent.spawn_later(sec, self.leave_table)
            gevent.spawn_later(sec + 1, self.init_gold)
            gevent.spawn_later(sec + 12, self.sit_table)
            return True

        if self.check_play_count():
            self.info('机器人玩牌超过5局，必须退出了')
            sec = random.randint(1, 2)
            gevent.spawn_later(sec, self.leave_table)
            gevent.spawn_later(sec+12, self.sit_table)
            return True

        if self.should_quit():
            self.info('机器人超时或者收到了退出指令，必须突出')
            gevent.spawn_later(1, self.leave_table)
            return True

        return False

    def handle_start_event(self, event):
        if self.check_robot_status():
            return

        if self.wait_leave:
            return

        if self.strategy.can_do():
            gevent.spawn_later(random.randint(2, 5), self.bet_add)
        else:
            gevent.spawn_later(random.randint(2, 5), self.bet_watch)

    def handle_round_event(self, event):

        if self.action in [GIVEUP,WATCH]:
            return

        if event.body.texas_status == TEXAS_HAND:
            if hasattr(event.body, 'player_pokers'):
                self.poker.set_pokers(event.body.player_pokers)
                self.info('设置手牌=%s' % (self.poker.pokers))
                if self.strategy.can_do():
                    gevent.spawn_later(random.randint(3, 5), self.hand)
        elif event.body.texas_status == TEXAS_PUBLIC_3:
            self.poker.set_public_pokers(event.body.public_pokers)
            if self.action == PASS and self.strategy.can_do():
                gevent.spawn_later(random.randint(3, 5), self.public_3)
        elif event.body.texas_status == TEXAS_PUBLIC_5:
            self.poker.set_public_pokers(event.body.public_pokers)
            if self.action == PASS and self.strategy.can_do():
                gevent.spawn_later(random.randint(3, 5), self.public_5)
        else:
            self.info('游戏结束，此处应该不存在，有专门的结束事件处理')


    def hand(self):

        if self.poker.is_hand_dui():
            multiple = self.strategy.rate_strategy([(10,False),(40,4),(50,3),])
            if multiple:
                self.bet_add_bei(TEXAS_HAND, multiple)
            else:
                self.bet_pass(TEXAS_HAND)
        elif self.poker.is_hand_max_dan():
            multiple = self.strategy.rate_strategy([(20,4),(30,3),(50,False),])
            if multiple:
                self.bet_add_bei(TEXAS_HAND, multiple)
            else:
                self.bet_pass(TEXAS_HAND)
        else:
            multiple = self.strategy.rate_strategy([(5,3),(95,False),])
            if multiple:
                self.bet_add_bei(TEXAS_HAND, multiple)
            else:
                self.bet_pass(TEXAS_HAND)

        print 'hand',self.robot_id,self.poker

    def public_3(self):

        print 'public_3',self.robot_id,self.poker
        player_poker = None
        try:
            player_poker = PlayerPokers(-1, *(self.poker.pokers + self.poker.public_pokers))
        except Exception as e:
            print e.message
            self.info('@@@@bet_low_gold=%d@@@@@action=%d@@@@@pokers=%s,public_pokers=%s' % (self.bet_low_gold, self.action, self.poker.pokers, self.poker.public_pokers))


        if player_poker.poker_type in [T_2_DUI,T_3_TIAO,T_SHUN,T_TONGHUA,T_HULU,T_4_TIAO,T_TONGHUASHUN,T_ROYAL]:
            self.bet_add_bei(TEXAS_PUBLIC_3, 2)
        elif player_poker.poker_type == T_DUI:
            if self.poker.dui_hand_in_public_3():
                multiple = self.strategy.rate_strategy([(10,False),(90,2),])
                if multiple:
                    self.bet_add_bei(TEXAS_PUBLIC_3, multiple)
                else:
                    self.bet_pass(TEXAS_PUBLIC_3)
            else:
                self.info('2手牌+3公牌，一对中没有手牌')
                self.bet_pass(TEXAS_PUBLIC_3)
        elif self.poker.shun_4_public_3(player_poker.pokers) or self.poker.tonghua_4_public_3(player_poker.pokers):
            multiple = self.strategy.rate_strategy([(40,False),(60,2),])
            if multiple:
                self.bet_add_bei(TEXAS_PUBLIC_3, multiple)
            else:
                self.bet_pass(TEXAS_PUBLIC_3)
        else:
            multiple = self.strategy.rate_strategy([(5,2),(95,False),])
            if multiple:
                self.bet_add_bei(TEXAS_PUBLIC_3, multiple)
            else:
                self.bet_pass(TEXAS_PUBLIC_3)

        print self.poker

    def public_5(self):
        print 'public_5',self.robot_id,self.poker
        player_poker = None
        try:
            player_poker = self.manager.poker_manager.best_playerpoker(self.poker.pokers + self.poker.public_pokers)
        except Exception as e:
            print e.message
            self.info('###########bet_low_gold=%d#####action=%d######pokers=%s,public_pokers=%s' % (self.bet_low_gold, self.action, self.poker.pokers, self.poker.public_pokers))

        if player_poker.poker_type in [ T_3_TIAO,T_SHUN,T_TONGHUA,T_HULU,T_4_TIAO,T_TONGHUASHUN,T_ROYAL]:
            self.bet_add_bei(TEXAS_PUBLIC_5, 1)
        else:
            if self.poker.public_pokers_public_5(player_poker.pokers) == False:
                self.bet_giveup()
            else:
                if player_poker.poker_type == T_2_DUI:
                    if self.poker.dui2_public_5(player_poker.pokers):
                        self.bet_add_bei(TEXAS_PUBLIC_5, 1)
                    else:
                        self.bet_giveup()
                elif player_poker.poker_type == T_DUI:
                    if self.poker.dui_public_5(player_poker.pokers):
                        self.bet_add_bei(TEXAS_PUBLIC_5, 1)
                    else:
                        self.bet_giveup()
                else:
                    if self.poker.other_public_5(player_poker.pokers):
                        self.bet_add_bei(TEXAS_PUBLIC_5, 1)
                    else:
                        self.bet_giveup()

        print self.poker

    def handle_over_event(self, event):
        self.reset_game()
        for x in event.body.player_results:
            if x.uid == self.robot_id:
                self.info('同步机器人金币,原有gold=%d, 新的gold=%d' % (self.gold, x.gold))
                self.gold = x.gold
                break


        for x in event.body.player_results:
            if self.robot_id == x.uid and x.is_watch == False:
                self.incr_play_count()

    def init_gold(self):
        if self.gold < 10000:
            gold = random.randint(20000,500000)
            self.manager.recharge_to(self.robot_id,gold)
            self.gold = gold
            self.info("机器人充值了: %d",self.gold,color=color.red)
        elif self.gold > 200000000:
            gold = random.randint(20000000,100000000)
            self.manager.recharge_to(self.robot_id,gold)
            self.gold = gold
            self.info("机器人充值了: %d",self.gold,color=color.red)

    def start(self):
        self.info("启动")
        req = create_client_event(ConnectGameServerReq)
        req.header.user = self.robot_id
        req.body.session = 12121231
        self.forward_message(req)
        gevent.spawn_later(random.randint(1,3),self.sit_table_first)

    def info(self,format,*args,**kwargs):
        if kwargs == None or len(kwargs) == 0:
            logging.info("[%d/%d/%d/%d/%d/%d/%s]" + format,self.action, self.robot_id,self.table_id,self.gold,self.play_count,self.play_count_rate,self.row_robot_user.nick,*args)
        else:
            color = kwargs["color"]
            logging.info(color("[%d/%d]" + format),self.robot_id,self.table_id,*args)

    def append_history_table(self, table_id):
        if len(self.history_table_ids) > 3:
            self.history_table_ids.pop(0)
        self.history_table_ids.append(table_id)

    def incr_play_count(self):
        self.play_count += 1
        self.play_count_rate += 10

    def check_play_count(self):
        if self.play_count >= 5:
            if random.randint(1,100) <= self.play_count_rate:
                self.play_count_rate = 30
                self.play_count = 0
                return True
        return False

    def play_timeout(self):
        if self.end_time < datetime.now():
            self.has_quit_command = True
            return True
        return False

    def not_enough_gold(self):
        return self.gold < TEXAS_MIN_GOLD

    def should_quit(self):
        if self.play_timeout():
            return True

        if self.has_quit_command:
            return True

        return False

    def forward_message(self,message):
        if not self.should_quit() :
            self.service.forward_message(message.header,message.encode())
        elif self.play_timeout() or self.has_quit_command:
            self.reset_table()
            self.info('机器人超时了，需要退出')
            if self.robot_id in self.manager.robots:
                self.manager.robots.pop(self.robot_id)
            self.service.forward_message(message.header,message.encode())
        else:
            self.info("机器人应该退出，所以不能发送任何消息，%s ", message.header.command,color=color.red_bg)




    def handle_table_event(self, event):
        if event.body.event_type == PLAYER_KICKED:
            self.info('确认离开牌桌成功！！！')
            # if not self.play_timeout():
            #     if self.not_enough_gold():
            #         self.init_gold()
            #     self.info('机器人被系统T了，机器人2~3秒后重新进入牌桌')
            #     gevent.spawn_later(random.randint(2,3), self.sit_table)

class BetStrategy:
    def __init__(self, robot):
        self.robot = robot

    def can_do(self):
        return random.randint(1,100) < 99

    def rate_strategy(self, lists = None):
        n = random.randint(0,100)
        for rate, val in lists:
            if n <= rate:
                return val

    def hand_is_dui(self):
        if set(self.robot.hand_values) == 1:
            return True
        return False

    def hand_max_dan(self):
        if len(set(self.robot.hand_values) & set([13,14])) > 0:
            return True
        return

    def pokers_4_shun(self, pokers):
        shun_4 = itertools.combinations(pokers, 4)
        for pokers in  shun_4:
            vals = [x.value for x in pokers]
            if max(vals) - min(vals) == 3:
                return True
        return False

    def pokers_4_tonghua(self, pokers):
        cc = collections.Counter([x.flower for x in pokers])
        cm = cc.most_common()
        if cm[0][1] == 4:
            return True
        return False

    def choice_start_gold(self, gold):
        golds = self.can_bet_golds(gold)

        if len(golds) == 0:
            raise Exception("can't find bet gold")

        choice_golds = []
        golds.sort(reverse=True)
        for i, x in enumerate(golds):
            choice_golds += [x] * (i + 1)
        return random.choice(choice_golds)

    def can_bet_golds(self, gold):
        max_index = -1
        for i, bet_gold in enumerate(BET_GOLDS):
            if gold > bet_gold:
                max_index = i + 1

        if max_index == -1:
            return []

        can_bets = []
        if max_index < 5:
            can_bets = BET_GOLDS[:max_index]
        else:
            can_bets = BET_GOLDS[max_index-5:max_index]

        can_bets.sort(reverse=True)

        return [x for x in can_bets if x * 6 <= gold]

class RobotManager:
    def __init__(self, service):
        self.service = service
        if service != None:
            self.redis = service.server.redis
        else:
            self.redis = None

        self.robots = {}
        self.prepare_robots = {}
        self.redis.delete("texas_online_robots")
        self.poker_manager = PokerManager()

        gevent.spawn_later(1,self.redis.lpush,"texas_robot_cmd","loadall") # 启动时加载所有robot
        gevent.spawn(self.startup_ready_robots) # 启动符合条件的robot，每隔30秒检查一次
        gevent.spawn_later(10,self.reload_all_robots_everyday) # 每天3点开始重新加载更新所有robot配置


        gevent.spawn(self.manage_robots_console) # 提供在线接口，可以在线进行ruteobot的加载或者停止
        # MRobot = namedtuple('MRobot', 'uid online_times type win_gold state create_time')
        # s1 = str(datetime.now().hour)+':'+str(datetime.now().minute)
        # e1 = str(datetime.now().hour)+':'+str(int(datetime.now().minute) + 1)
        #
        # s2 = str(datetime.now().hour)+':'+str(datetime.now().minute + 1)
        # e2 = str(datetime.now().hour)+':'+str(int(datetime.now().minute) + 2)
        #
        # s3 = str(datetime.now().hour)+':'+str(datetime.now().minute + 2)
        # e3 = str(datetime.now().hour)+':'+str(int(datetime.now().minute) + 3)
        #
        # s4 = str(datetime.now().hour)+':'+str(datetime.now().minute + 3)
        # e4 = str(datetime.now().hour)+':'+str(int(datetime.now().minute) + 4)
        #
        # s5 = str(datetime.now().hour)+':'+str(datetime.now().minute + 4)
        # e5 = str(datetime.now().hour)+':'+str(int(datetime.now().minute) + 5)
        #
        # m1 = MRobot(uid=12362, online_times ='00:01-06:00|2400-4800,%s-%s|100-200' % (s1,e2),type=2,win_gold=-63211938,state=1,create_time='2017-04-07 00:00:0')
        # m2 = MRobot(uid=12367, online_times ='00:01-06:00|2400-4800,%s-%s|100-200' % (s2,e2),type=2,win_gold=-63211938,state=1,create_time='2017-04-07 00:00:0')
        # m3 = MRobot(uid=12370, online_times ='00:01-06:00|2400-4800,%s-%s|100-200' % (s3,e3),type=2,win_gold=-63211938,state=1,create_time='2017-04-07 00:00:0')
        # m4 = MRobot(uid=12379, online_times ='00:01-06:00|2400-4800,%s-%s|100-200' % (s4,e4),type=2,win_gold=-63211938,state=1,create_time='2017-04-07 00:00:0')
        # m5 = MRobot(uid=12386, online_times ='00:01-06:00|2400-4800,%s-%s|100-200' % (s5,e5),type=2,win_gold=-63211938,state=1,create_time='2017-04-07 00:00:0')
        # self.load_prepare_robot(m1)
        # self.load_prepare_robot(m2)
        # self.load_prepare_robot(m3)
        # self.load_prepare_robot(m4)
        # self.load_prepare_robot(m5)
        print self.prepare_robots

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

                # if random.randint(0,100) < 75: # 50% percent robots will startup
                robot = Robot(self,robot_id,t[0],t[1])
                # self.suit_table_type(robot)
                robot.start()
                self.robots[robot_id] = robot

            counters = {}
            idle_robots = []
            for robot in self.robots.values():
                if robot.table == None:
                    idle_robots.append(robot.robot_id)
                elif robot.table.table_type in counters:
                    counters[robot.table.table_type] += 1
                else:
                    counters[robot.table.table_type] = 1

            logging.info(color.blue(color.strong("[[[ There are %d robots online %s ]]] ")),len(counters),counters)
            logging.info(color.blue(color.strong("[[[ online idle robots %s ]]]")),str(idle_robots))
            self.redis.hset('texas_online', 'robot_online', len(counters))
            self.redis.hset('texas_online', 'robot_idle_total', len(idle_robots))
            if 1 in counters:
                self.redis.hset('texas_online', '1', counters[1])
            else:
                self.redis.hset('texas_online', '1', 0)
            if 2 in counters:
                self.redis.hset('texas_online', '2', counters[2])
            else:
                self.redis.hset('texas_online', '2', 0)
            if 3 in counters:
                self.redis.hset('texas_online', '3', counters[3])
            else:
                self.redis.hset('texas_online', '3', 0)



            gevent.sleep(loop_seconds)

    def reload_all_robots_everyday(self):
        loaded_date = datetime.now().date()

        while True:
            now = datetime.now()
            if now.date() != loaded_date and now.time().hour >= 3 and now.time().minute >= 1:
                loaded_date = now.date()
                gevent.spawn_later(1,self.redis.lpush,"texas_robot_cmd","loadall")
            gevent.sleep(60)

    def manage_robots_console(self):
        while True:
            _,cmd = self.redis.brpop("texas_robot_cmd")
            logging.info(color.blue("收到机器人命令：%s"),cmd)
            if cmd == "loadall":
                self.prepare_robots = {}
                row_robots = None
                session = Session()
                try :
                    row_robots = session.query(TRobotTexas).filter(TRobotTexas.state == 1).all()
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
                    row_robot = session.query(TRobotTexas).filter(TRobotTexas.uid == robot_id).first()
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

    def handle_user_online(self, session, uid):
        pass

    def get_robot(self, uid):
        return self.robots.get(uid, None)

    def suit_table_type(self):
        pass


    def recharge_to(self,robot_id,gold):
        session = Session()
        try :
            session.begin()
            row_user = session.query(TUser).filter(TUser.id == robot_id).first()

            if row_user.gold == gold:
                return 0

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

    def get_table_type(self):
        table_types = {}

        for r in self.robots.values():
            if r.table is None:
                continue

            if r.table.table_type in table_types.keys():
                table_types[r.table.table_type] += 1
            else:
                table_types[r.table.table_type] = 1

        if 3 not in table_types.keys():
            table_types[3] = 0

        robot_count = sum(table_types.values())
        for table_type, robot_num in table_types.items():
            if table_type == 1:
                if robot_num / float(robot_count) < 0.5:

                    return 1

            if table_type == 2:
                if robot_num / float(robot_count) < 0.35:

                    return 2

            if table_type == 3:
                if robot_num / float(robot_count) < 0.15:

                    return 3



class GamblerPlayer:
    def __init__(self, uid, table_id, room_id):
        self.uid = uid
        self.table_id = table_id
        self.room_id = room_id

class TexasPokers:
    def __init__(self):
        self.pokers = []
        self.public_pokers = []

    def set_pokers(self, pokers):
        for p in pokers:
            self.pokers.append(Poker(p.flower, p.value))

    def set_public_pokers(self, public_pokers):
        for p in public_pokers:
            self.public_pokers.append(Poker(p.flower, p.value))

    def is_hand_dui(self):
        return self.pokers[0].value == self.pokers[1].value

    def is_hand_max_dan(self):
        if self.pokers[0].value == 1 or self.pokers[0].value == 13:
            return True
        elif self.pokers[1].value == 1 or self.pokers[1].value == 13:
            return True
        else:
            return False

    def hand_public_3(self):
        player_poker = PlayerPokers(-1, *(self.pokers + self.public_pokers[0:3]))

        return player_poker

    def dui_hand_in_public_3(self):
        for p in self.pokers:
            for p3 in self.public_pokers:
                if p.equals(p3):
                    return True
        return False

    def shun_4_public_3(self, pokers):
        shun_4 = itertools.combinations(pokers, 4)
        for pokers in  shun_4:
            vals = [x.value for x in pokers]
            if max(vals) - min(vals) == 3:
                return True
        return False

    def tonghua_4_public_3(self, pokers):
        cc = collections.Counter([x.flower for x in pokers])
        cm = cc.most_common()
        if cm[0][1] == 4:
            return True
        return False

    def public_pokers_public_5(self, pokers):
        for p in self.pokers:
            for p5 in pokers:
                if p.equals(p5):
                    return True
        return False

    def dui2_public_5(self, pokers):
        values_counter = collections.Counter([x.value for x in pokers])
        mc = values_counter.most_common()
        if mc[0][1] != 2 and mc[1][1] != 2:
            raise Exception("两对牌型有误",mc)
        dui_2_vals = [mc[0][0],mc[1][0]]

        for p in self.pokers:
            if p.value in dui_2_vals:
                return True

        dan_val = mc[2][0]

        if dan_val in [p.value for p in self.pokers]:
            if random.randint(1,2) > 1:
                return True
            else:
                return False

    def dui_public_5(self, pokers):
        values_counter = collections.Counter([x.value for x in pokers])
        mc = values_counter.most_common()
        if mc[0][1] != 2:
            raise Exception("一对牌型有误",mc)
        dui_val = mc[0][0]

        for p in self.pokers:
            if p.value == dui_val:
                return True

        p_vals = [p.value for p in self.pokers]
        if 1 in p_vals or 13 in p_vals:
            return True

        if 12 in p_vals or 11 in p_vals or 10 in p_vals:
            if random.randint(1, 10) <= 6:
                return True
            else:
                return False

        if 10 > max(p_vals):
            return False

        raise u"异常，对子"

    def other_public_5(self, pokers):
        p_vals = [p.value for p in self.pokers]
        for p in p_vals:
            if 12 >= p:
                if random.randint(1, 100) <= 70:
                    return True
                else:
                    return False

        if 12 < max(p_vals):
            return False

        raise u"异常，单张"


    def __repr__(self):
        return '<Hand %s>,[Public %s]' % (self.pokers, self.public_pokers)

class Poker:
    def __init__(self, flower, value):
        self.flower = flower
        self.value = value

    def __repr__(self):
        return '<Poker flower=%d,value=%d>' % (self.flower,self.value)

    def equals(self, other):
        if self.value == other.value and self.flower == other.flower:
            return True
        return False

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

if __name__ == '__main__':
    # r = redis.Redis(password='Wgc@123456', db=0, host='39.')
    # namedtuple('cache','name')
    # rm = RobotManager(None)
    # rm.manage_robots_console()

    st = BetStrategy()
    print st.choice_bet_gold(3000)
