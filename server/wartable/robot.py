# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import gevent
from gevent import monkey;monkey.patch_all()
from gevent import lock
from gevent.queue import Queue

import sys
import os
import random
import copy
import traceback
import time
import logging
import json
from datetime import datetime, timedelta, date as dt_date, time as dt_time
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from sqlalchemy import sql,and_

from proto import war_pb2

from db.connect import *
from dal.core import *
from db.robot_war import *
from util.commonutil import *
from wartable.gameconf import *

from hall.messagemanager import *






class RobotManager:
    def __init__(self, table):
        self.table = table
        self.robots = {}
        self.game_robots = {}
        self.game_robots_len = 0
        self.red_rate = 0
        self.black_rate = 0
        self.lucky_rate = 0
        self.lock = self.table.lock
        self.time_now = time.time()
        self.startup_trys = {}
        self.prepare_robots = {}

        self.robot_chat = RobotChat(table)

        self.result = []
        gevent.spawn_later(2, self.reload_all_robots_everyday)
        gevent.spawn_later(4, self.robots_up)
        # self.load_robots()
        self.session = None

    def get_session(self):
        if self.session == None:
            return Session()
        return self.session

    def close_session(self, session):
        if session:
            session.close()
            session = None

    def check_robot_online(self, uid):
        if self.robots[uid].run_time[0] == -1 or self.robots[uid].run_time[1] == -1:
            return False

        if self.robots[uid].status != Robot.ONLINE:
            return False

        return True

    def is_robot(self, uid):
        if uid in self.robots.keys():
            return True
        return False

    def get_user(self,uid):
        return self.table.dal.get_user(uid)

    def reload_all_robots_everyday(self):
        loaded_date = datetime.now().date()

        self.load_robots()

        while True:
            now = datetime.now()
            if now.date() != loaded_date and now.hour == 4 and now.minute == 13:
                loaded_date = now.date()
                for uid, robot in self.table.players.items():
                    if robot.access_service == -1:
                            self.leave_table(uid)
                logging.info(u'@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@')
                gevent.sleep(5)
                self.load_robots()
                self.robots_timesit()
            gevent.sleep(50)

    def load_robots(self):
        session = self.get_session()
        set_context('session', session)
        logging.debug(u'load_robots acquire')
        self.table.lock.acquire()
        try:
            robots = session.query(TRobotWar).filter(TRobotWar.state == 1).all()

            # self.robots = {}
            # self.prepare_robots = {}
            for robot in robots:
                if self.rate_robot_can_up() == False:
                    continue

                start_times = []
                for seg in robot.online_times.split(','):
                    s = seg.split('|')
                    robot_start_time = random_time(s[0])
                    robot_duration = random_duration(s[1])
                    start_times.append((robot_start_time,robot_duration,get_offline_time(robot_start_time, robot_duration)))
                start_times.sort(cmp=lambda x,y:cmp(x[0],y[0]))
                self.prepare_robots[robot.uid] = start_times

                self.robots[robot.uid] = Robot(robot.uid, robot.online_times, start_times, self)
        finally:
            self.close_session(session)
            self.table.lock.release()
            logging.debug(u'load_robots release')

    def robots_up(self):
        while True:
            self.robots_timesit()
            gevent.sleep(60)

    def robots_timesit(self):
        now_datetime = datetime.now()
        for robot in self.robots.values():
            if self.robot_can_up(robot, now_datetime) and self.in_table(robot.uid) == False:
                robot.sit()

    def robot_can_up(self, robot, now):
        for up_time, robot_duration, offline_time in robot.time_tuple:
            if up_time < now and now < offline_time:
                robot.run_time = (up_time, offline_time,)
                return True
        return False

    def in_table(self, uid):
        return uid in self.table.players.keys()

    def rate_robot_can_up(self):
        can_up = [1] * 75 + [-1] * 25
        # random.shuffle(can_up)
        if random.choice(can_up) == -1:
            return False
        return True

    def leave(self, robot):
        if self.robot_can_leave(robot, datetime.now()):
            self.robot_chat.leave_talk(self.table.players[robot.uid])
            logging.debug(u'机器人- %d 准备离开牌桌' % robot.uid)
            robot.is_playing = False
            self.leave_table(robot.uid)
            return True
        return False

    def robot_can_leave(self, robot, now):
        if robot.run_time[0] < now and robot.run_time[1] < now:
            return True
        return False

    def startup_ready_robots(self):
        loop_seconds = 15
        while True:
            try:
                now = datetime.now().time()
                now_date = datetime.now().date()
                logging.info('robot_onlines：%d' % sum([1 for x in self.table.players if x in self.robots.keys()]))
                for robot_id,start_times in self.prepare_robots.items():
                    for t in start_times:
                        if self.robots[robot_id].uid in self.table.players.keys():
                            if t[2] != now_date and midnight_seconds(t[0], t[1], now):
                                # 隔天
                                if self.startup_trys.has_key(robot_id) and type(self.startup_trys[robot_id]) == list:
                                    if t[0] == self.startup_trys[robot_id][0]:
                                        self.robots[robot_id].leave()
                                        logging.info('机器人离开牌桌 startup_trys[%d]=%s,now=%s' % (robot_id,self.startup_trys[robot_id], now))
                                        self.startup_trys.pop(robot_id)
                                        break
                            elif t[0] <= now and seconds_between_times(now, t[0]) >= t[1]:
                                # 当天
                                if self.startup_trys.has_key(robot_id) and type(self.startup_trys[robot_id]) == list:
                                    if t[0] == self.startup_trys[robot_id][0]:
                                        #print 'robot leave.......'
                                        self.robots[robot_id].leave()
                                        logging.info('机器人离开牌桌 startup_trys[%d]=%s,now=%s' % (robot_id,self.startup_trys[robot_id], now))
                                        self.startup_trys.pop(robot_id)
                                        break
                        else:
                            # 在线操作
                            if t[0] <= now and seconds_between_times(now, t[0])  <= t[1]:
                                #print 'sit now'
                                self.robots[robot_id].sit()
                                if self.startup_trys.has_key(robot_id) and type(self.startup_trys[robot_id]) == list:
                                    self.startup_trys[robot_id] += [t[0],t[1],t[2]]
                                else:
                                    self.startup_trys[robot_id] = [t[0],t[1],t[2]]
                                logging.info('机器人进入牌桌 startup_trys[%d]=%s,now=%s' % (robot_id,self.startup_trys[robot_id], now))
                                break

            except:
                traceback.print_exc()
            finally:
                # self.table.lock.release()
                # logging.debug(u'startup_ready_robots release')
                pass

            gevent.sleep(loop_seconds)


    def sit_table(self, user):
        logging.debug(u'robot sit_table acquire')
        self.table.lock.acquire()
        try:
            self.table.sit_table(user,-1)
        finally:
            self.table.lock.release()

            logging.debug(u'robot sit_table release')


    def leave_table(self,uid):
        # logging.debug(u'robot %d leave_table acquire' % uid)
        #self.table.lock.acquire()
        try:
            self.table.remove_player(uid)
        finally:
            #self.table.lock.release()
            pass

        # logging.debug(u'robot %d leave_table release' % uid)


    def bet(self, bet_golds):
        for bet in bet_golds:
            if self.table.players.has_key(bet[0]) and self.table.players[bet[0]].get_gold() >= 0:
                if self.table.players[bet[0]].get_gold() <= bet[2]:
                    continue

                # logging.debug(u'robot-%d bet-%d type-%d' % (bet[0], bet[1], bet[2]))
                self.table.game.bet(self.table.players[bet[0]], bet[1], bet[2])

    def save_result(self, winner, luck_rate):
        if len(self.result) > 7:
            self.result.pop(0)
        self.result.append( str(str(winner)+','+str(luck_rate)) )

    def get_last_results(self, last_index = 1):
        if last_index == 1:
            return [self.result[-1]]
        return self.result[-last_index:]

class Robot:
    ONLINE = 1;
    OFFLINE = -1;
    WAIT_OFFLINE = 0;
    def __init__(self, uid, online_times, time_tuple, manager ):
        self.uid = uid
        self.online_times = online_times
        self.win_gold = ''
        self.manager = manager
        self.user = manager.get_user(self.uid)
        self.is_bet = False

        self.run_time = (-1,-1)

        self.bet_gold = []
        self.time_tuple = time_tuple

        self.start_times = []
        self.is_playing = False
        self.status = Robot.OFFLINE

    def set_status(self, status):
        self.status = status

    def set_online(self, online):
        self.is_playing = online

    def get_play_timetuple(self):
        now_datetime = datetime.now()
        for up_time, robot_duration, offline_time in self.time_tuple:
            if up_time < now_datetime and now_datetime < offline_time:
                return up_time,offline_time
        return -1,-1


    def __repr__(self):
	    return 'uid=%d,user=%d,user_gold=%d' % (self.uid,self.user.id,self.user.gold)

    def init(self):
        for seg in self.online_times.split(','):
            s = seg.split('|')
            robot_start_time = random_time(s[0])
            robot_duration = random_duration(s[1])
            self.start_times.append((robot_start_time,robot_duration,))
        self.start_times.sort(cmp=lambda x,y:cmp(x[0],y[0]))


    def on_server_event(self,event):

        if event.header.command == war_pb2.WarGameStartEvent.ID:
            self.start(event)
        elif event.header.command == war_pb2.WarGameOverEvent.ID:
            self.over(event)
        elif event.header.command == war_pb2.WarGameActionEvent.ID:
            pass
            # print 'recive action event',event.header.user
            # self.bet()

    def over(self, event):
        # logging.debug(u'收到结束事件，处理聊天记录')
        if not self.manager.table.players.has_key(self.uid):
            return

        player = self.manager.table.players[self.uid]
        if len(player.player_results) <= 0:
            return

        if player.player_results[-1].bet_gold > 0 and player.player_results[-1].win_gold <= 0:
            if self.manager.robot_chat.lose(player, 8):
                pass
            elif self.manager.robot_chat.lose(player, 4):
                pass
        elif player.player_results[-1].bet_gold > 0 and player.player_results[-1].win_gold > 0:
            self.manager.robot_chat.win(player, 6)

        if event.body.big_winner != None and event.body.big_winner.uid == self.uid:
            self.manager.robot_chat.big_winner_talk(player)


        # self.manager.robot_chat.no_lucky(player, 10)

        # self.manager.robot_chat.human_talk(player)

        # if player.player_results[-1].reward_gold > 0:
        #     self.manager.robot_chat.reward_talk(player)



    def sit(self):
        logging.info(u'机器人 %d 进入牌桌', self.uid)
        if self.user.gold > 100000000:
            try:
                session = self.manager.get_session()
                self.user.gold = random.randint(2000000, 50000000)
                self.manager.table.dal.save_user(session, self.user)
                logging.debug(u'机器人 %d 当前金币做不1亿, 增加新的金币为 %d' % (self.uid, self.user.gold))
            finally:
                self.manager.close_session(session)
        elif self.user.gold <= 100000:
            try:
                session = self.manager.get_session()
                self.user.gold = random.randint(*(TABLE_GAME_CONF[14]))
                self.manager.table.dal.save_user(session, self.user)
                logging.debug(u'机器人 %d 当前金币不足1万，增加新的金币为 %d' % (self.uid, self.user.gold))
            finally:
                self.manager.close_session(session)
        self.set_status(Robot.ONLINE)
        self.manager.sit_table(self.user)
        self.manager.robot_chat.enter_table(self.user)

    def start(self, event):
        if self.status != Robot.ONLINE:
            return

        if event.body.table.lucky_player != None and event.body.table.lucky_player.uid == self.uid:
            self.manager.robot_chat.be_star(self.manager.table.players[self.uid])
            pass


        if self.user.gold > 200000000:
            try:
                session = self.manager.get_session()
                self.user.gold = random.randint(100000000, 200000000)
                self.manager.table.dal.save_user(session, self.user)
                logging.debug(u'机器人 %d 当前金币做不2亿, 增加新的金币为 %d' % (self.uid, self.user.gold))
            finally:
                self.manager.close_session(session)
        elif self.user.gold <= 100000:
            try:
                session = self.manager.get_session()
                self.user.gold = random.randint(*(TABLE_GAME_CONF[14]))
                self.manager.table.dal.save_user(session, self.user)
                logging.debug(u'机器人 %d 当前金币不足1万，增加新的几笔为 %d' % (self.uid, self.user.gold))
            finally:
                self.manager.close_session(session)


        later = random.randint(4, self.manager.table.game.remain_time - 2)
        # print 'later time',later,'remain_time',self.manager.table.game.remain_time
        gevent.spawn_later(later, self.robot_bet )
        # self.is_bet = False

    def robot_bet(self):

        # if self.user.gold <= TABLE_GAME_CONF[0]:
        #     try:
        #         session = self.manager.table.get_session()
        #         self.user.gold = random.randint(10000, 50000)
        #         self.manager.table.dal.save_user(session, self.user)
        #         # logging.debug(u'robot-%d gold not enough, now gold-%d' % (self.uid, self.user.gold))
        #     finally:
        #         self.manager.table.close_session(session)

        # 用户投注的金币列表
        bet_actions = []
        bet_golds = self.get_bet_gold()

        if sum(bet_golds) <= 0:
            return

        # 指定投注方概率 0.5，投注方 1:red,-1:black
        type_rate, bet_type = self.bet_type_rate()
        # 另一方投注方概率，投注方
        other_rate = 100 - int(type_rate * 100)
        other_type = -1 if bet_type == 1 else 1
        type_list = [bet_type for x in range(int(type_rate * 100))]
        type_list += [other_type for x in range(other_rate)]
        real_bet_type = random.choice(type_list)

        if len(bet_golds) > 1:
            lucky_rate = self.bet_lucky_rate()

            small_gold = min(bet_golds)
            bet_golds.remove(small_gold)
            no_lucky = 100 - int( lucky_rate * 100 )
            type_list = [0 for x in range(int(lucky_rate * 100))]
            type_list += [1 for x in range(no_lucky)]

            if  random.choice(type_list) == 0:
                # bet_actions.append((self.uid, 0, small_gold))
                if self.manager.table.game.remain_time >= 2:
                    self.manager.bet([(self.uid, 0, small_gold)])
                    gevent.sleep(1)
                else:
                    self.manager.bet([(self.uid, 0, small_gold)])
            else:
                bet_golds.append(small_gold)

        for gold in bet_golds:
            bet_actions.append((self.uid, real_bet_type, gold))
        self.manager.bet(bet_actions)



    def leave(self):
        self.manager.robot_chat.leave_talk(self.manager.table.players[self.uid])
        logging.debug(u'机器人- %d 准备离开牌桌' % self.uid)
        self.is_playing = False
        self.manager.startup_trys[self.uid][1] = -1
        self.manager.leave_table(self.uid)



    def bet_type_rate(self):
        # 机器人进入后第一局或者上一局为平局时，这一局下红或者黑的概率都为50%的概率；
        if len(self.manager.result) == 0:
            return 0.5, random.choice([1,-1])

        # 当上一局为红时，下一局下黑的概率为55%；每连续出红或者黑时，概率增加5%；最高概率不超过76%。
        # str(winner)+','+str(luck_rate)
        last_winner =  int(self.manager.get_last_results()[0].split(',')[0])
        this_time_bet = -1 if last_winner == 1 else 1
        rate = 0.55
        last_result = self.manager.get_last_results(7)
        last_result.reverse()
        for x in last_result:
            if int(x.split(',')[0]) == last_winner:
                if rate >= 0.76:
                    rate = 0.76
                    break
                else:
                    rate += 0.03
            else:
                break
        return rate, this_time_bet

    def bet_lucky_rate(self):
        if len(self.manager.result) == 0:
            return 0.3

        rate = 0.3
        last_result = self.manager.get_last_results(7)
        last_result.reverse()
        for x in last_result:
            if int(x.split(',')[1]) <= 1:
                if rate >= 0.6:
                    rate = 0.6
                    break
                else:
                    rate += 0.05
        return rate

    def get_bet_gold(self):
        bet_gold = []
        conf = ROBOT_CONF[can_bet(self.user.get_gold())]

        lis = []
        for index in range(len(conf)):
            lis += [index for x in range(conf[index][0])]

        bet_index = random.choice(lis)

        for x in conf[bet_index][1]:
            can_bet_gold = get_can_bet(self.user.gold)[x-1]
            bet_gold.append( can_bet_gold )

        return bet_gold

class RobotChat:
    def __init__(self, table):
        self.table = table


    def get_player_result(self, player, recent_size):
        return player.player_results[-recent_size:]

    def enter_table(self, user):
        # 1，进入牌桌内，  1%几率，延迟1~5秒，快捷语1  ；1%几率，延迟1~5秒，表情 13
        conf = ROBOT_TALK_CONF['enter']
        choice = self.choice_conf(conf)
        if choice != None:
            delay_time = self.get_delay_sec(*choice[1])
            type, content = choice[2].split('-')
            gevent.spawn_later(delay_time, MessageManager.war_robot_chat, *(self.table, user, self.get_talk_json(user, content, type)))
            # tbd 调用发聊天的接口，发送talk_str
            # type, content = choice[2].split('-')
            # MessageManager.war_robot_chat(self.table, user, self.get_talk_json(user, content, type))

    def lose(self, player, times):
        player_result = self.get_player_result(player, times)
        lose_round = sum([1 for x in player_result if x.bet_gold > 0 and x.win_gold == 0])
        if lose_round >= times:
            conf = ROBOT_TALK_CONF['lose_'+str(times)]
            choice = self.choice_conf(conf)
            if choice != None:
                delay_time = self.get_delay_sec(*choice[1])
                type, content = choice[2].split('-')
                gevent.spawn_later(delay_time, MessageManager.war_robot_chat, *(self.table, player.user_dal, self.get_talk_json(player.user_dal, content, type)))
                # tbd 调用发聊天的接口，发送talk_str
                # type, content = choice[2].split('-')
                # MessageManager.war_robot_chat(self.table, player.user_dal, self.get_talk_json(player.user_dal,content,type))
                return True
        return False

    def win(self, player, times = 3):
        player_result = self.get_player_result(player, times)
        win_round = sum([1 for x in player_result if x.bet_gold > 0 and x.win_gold > 0])
        if win_round >= times:
            conf = ROBOT_TALK_CONF['win_6']
            choice = self.choice_conf(conf)
            if choice != None:
                delay_time = self.get_delay_sec(*choice[1])
                type, content = choice[2].split('-')
                gevent.spawn_later(delay_time, MessageManager.war_robot_chat, *(self.table, player.user_dal, self.get_talk_json(player.user_dal, content, type)))
                # gevent.sleep(delay_time)
                # tbd 调用发聊天的接口，发送talk_str
                # type, content = choice[2].split('-')
                # MessageManager.war_robot_chat(self.table, player.user_dal, self.get_talk_json(player.user_dal,content,type))
                return True
        return False

    def no_lucky(self, player, times = 10):
        if sum( self.table.reward_pool.records[-times:] ) <= 0:
            conf = ROBOT_TALK_CONF['no_lucky_10']
            choice = self.choice_conf(conf, 1000)
            if choice != None:
                delay_time = self.get_delay_sec(*choice[1])
                gevent.sleep(delay_time)
                type, content = choice[2].split('-')
                gevent.spawn_later(delay_time, MessageManager.war_robot_chat, *(self.table, player.user_dal, self.get_talk_json(player.user_dal, content, type)))
                # tbd 调用发聊天的接口，发送talk_str
                type, content = choice[2].split('-')
                # MessageManager.war_robot_chat(self.table, player.user_dal, self.get_talk_json(player.user_dal,content,type))
                return True
        return False

    def be_star(self, player):
        conf = ROBOT_TALK_CONF['be_star']
        choice = self.choice_conf(conf)
        if choice != None:
            delay_time = self.get_delay_sec(*choice[1])
            type, content = choice[2].split('-')
            gevent.spawn_later(delay_time, MessageManager.war_robot_chat, *(self.table, player.user_dal, self.get_talk_json(player.user_dal, content, type)))
            # gevent.sleep(delay_time)
            # tbd 调用发聊天的接口，发送talk_str
            type, content = choice[2].split('-')
            # MessageManager.war_robot_chat(self.table, player.user_dal, self.get_talk_json(player.user_dal,content,type))
            return True
        return False

    def many_talk(self):
        pass

    def human_talk(self, player):
        conf = ROBOT_TALK_CONF['human_talk']
        choice = self.choice_conf(conf)
        if choice != None:
            delay_time = self.get_delay_sec(*choice[1])
            type, content = choice[2].split('-')
            gevent.spawn_later(delay_time, MessageManager.war_robot_chat, *(self.table, player.user_dal, self.get_talk_json(player.user_dal, content, type)))
            # gevent.sleep(delay_time)
            # tbd 调用发聊天的接口，发送talk_str
            type, content = choice[2].split('-')
            # MessageManager.war_robot_chat(self.table, player.user_dal, self.get_talk_json(player.user_dal,content,type))
            return True
        return False

    def reward_talk(self, player):
        conf = ROBOT_TALK_CONF['reward_talk']
        choice = self.choice_conf(conf)
        if choice != None:
            delay_time = self.get_delay_sec(*choice[1])
            type, content = choice[2].split('-')
            gevent.spawn_later(delay_time, MessageManager.war_robot_chat, *(self.table, player.user_dal, self.get_talk_json(player.user_dal, content, type)))
            # gevent.sleep(delay_time)
            # tbd 调用发聊天的接口，发送talk_str
            #type, content = choice[2].split('-')
            #MessageManager.war_robot_chat(self.table, player.user_dal, self.get_talk_json(player.user_dal,content,type))
            return True
        return False

    def leave_talk(self, player):
        conf = ROBOT_TALK_CONF['leave_talk']
        choice = self.choice_conf(conf)
        if choice != None:
            delay_time = self.get_delay_sec(*choice[1])
            type, content = choice[2].split('-')
            gevent.spawn_later(delay_time, MessageManager.war_robot_chat, *(self.table, player.user_dal, self.get_talk_json(player.user_dal, content, type)))
            #gevent.sleep(delay_time)
            # tbd 调用发聊天的接口，发送talk_str

            #MessageManager.war_robot_chat(self.table, player.user_dal, self.get_talk_json(player.user_dal,content,type))
            return True
        return False

    def big_winner_talk(self, player):
        conf = ROBOT_TALK_CONF['big_winner_talk']
        choice = self.choice_conf(conf)
        if choice != None:
            delay_time = self.get_delay_sec(*choice[1])
            type, content = choice[2].split('-')
            gevent.spawn_later(delay_time, MessageManager.war_robot_chat, *(self.table, player.user_dal, self.get_talk_json(player.user_dal, content, type)))
            #gevent.sleep(delay_time)
            # tbd 调用发聊天的接口，发送talk_str

            #MessageManager.war_robot_chat(self.table, player.user_dal, self.get_talk_json(player.user_dal,content,type))
            return True
        return False

    def sum_rate(self, rates_conf):
        return sum([x[0] for x in rates_conf])

    def choice_conf(self, rates_conf, rate_size = 100):
        choice_rate = sum([x[0] for x in rates_conf])
        other = rate_size - choice_rate

        rate_list = [[-1] for x in range(other) ]
        for i in range(len(rates_conf)):
            for _ in range(rates_conf[i][0]):
                rate_list.append( list(rates_conf[i]) )

        random.shuffle(rate_list)

        choice = random.choice(rate_list)
        if choice[0] > 0:
            return choice
        return None

    def is_bingo(self, rate_result):
        if rate_result > 0:
            return True
        return False

    def get_delay_sec(self, start_sec, end_sec):
        return random.randint(start_sec, end_sec)

    def get_talk_json(self, user, content, type):
        return json.dumps({
            'content': int(content),
            'type': int(type),
            'vip_exp': user.vip_exp,
            'uid': user.id,
            'nick': user.nick,
            'time': time.strftime('%H:%M:%S'),
            'avatar': user.avatar,
            'sex': user.sex
        })

ROBOT_TALK_CONF = {
    # 1，进入牌桌内，  2%几率，延迟1~10秒，快捷语1  ；1%几率，延迟1~5秒，表情13；1%几率，延迟1~5秒，表情14;1%几率，延迟1~5秒，表情6;1%几率，延迟1~5秒，表情8;1%几率，延迟1~5秒，表情1;1%几率，延迟1~5秒，表情12
    'enter':[(1,(1,10),'2-1')],

    # 2，连输4局，1%几率，延迟5~10秒，快捷语2 ； 1%几率 ，延迟5~10秒，发表情2
    'lose_4':[(1,(7,12),'2-2')],

    # 3，连输8局，2%几率，延迟5~10秒，快捷语3；25%几率，延迟1~5秒，发表情10;2%几率，延迟1~5秒，发表情11;2%几率，延迟1~5秒，发表情9
    'lose_8':[(2,(7,12),'2-3'),(2,(7,12),'1-10'),(2,(7,12),'1-11'),(2,(7,12),'1-9')],

    # 4，连赢6局，1%几率，延迟5~10秒，快捷语4；1%几率，延迟5~10秒，发表情4; 1%几率，延迟5~10秒，发表情7
    'win_6':[(1,(7,12),'2-4'),(1,(7,12),'1-4'),(1,(7,12),'1-7')],

    # 6，成为幸运星，2%概率，延迟2~6秒，发快捷语6；2%概率，延迟2~6秒，发表情3
    'be_star':[(1,(9,15),'1-3'),],

    # 10，要离开牌桌，5%概率，发表情15；5%概率，发表情5
    'leave_talk':[(1,(0,0),'1-15'),(1,(0,0),'1-5'),(1,(1,5),'1-13'),(1,(1,5),'1-14'),(1,(1,5),'1-6'),(1,(1,5),'1-8'),(1,(1,5),'1-1'),(1,(1,5),'1-12'),(1,(5,10),'1-2')],

    #11，大赢家，2%概率，延迟2~6秒发快捷7；2%的概率，延迟2~6秒发快捷5； 2%概率，发表情6
    'big_winner_talk':[(1,(9,15),'1-6'),],
}

# ROBOT_TALK_CONF = {
#     # 1，进入牌桌内，  1%几率，延迟1~5秒，快捷语1  ；1%几率，延迟1~5秒，表情 13
#     'enter':[(1,(1,5),'2-1'),(1,(1,5),'1-13')],
#     # 2，连输3局，5%几率，延迟1~5秒，快捷语2 ； 3%几率 ，延迟1~5秒，发表情2
#     'lose_3':[(2,(3,5),'2-1'),(2,(3,5),'1-2')],
#     # 3，连输5局，10%几率，延迟1~5秒，快捷语3；10%几率，延迟1~5秒，发表情10
#     'lose_5':[(2,(3,5),'2-3'),(2,(3,5),'1-10')],
#     # 4，连赢3局，5%几率，延迟1~5秒，快捷语4；5%几率，延迟1~5秒，发表情4
#     'win_3':[(2,(3,8),'2-4'),(2,(3,8),'1-4')],
#     # 5，连续10把未出幸运一击，千分之一概率，延迟1~5秒，发快捷5
#     'no_lucky_10':[(2,(3,8),'2-5')],
#     # 6，成为幸运星，10%概率，发快捷语6
#     'be_star':[(2,(0,0),'2-6')],
#     # 7，10秒内连续有5人说话，1%几率，延迟1~3秒，发快捷语7；1%几率，延迟1~3秒，发快捷语8；1%几率，延迟1~3秒，发表情11
#     'many_talk_10':[(1,1,(1,3),'2-7'),
#                  (1,1,(1,3),'2-8'),
#                  (1,1,(1,3),'1-11')],
#     # 8，有非机器人说话，1%的几率延迟1~3秒 发表情1；1%几率延迟 3~5秒，发表情6
#     'human_talk':[(1,(1,3),'1-1'),(1,(3,5),'1-6')],
#     # 9，有奖池开奖时，1%，延迟5~7秒 几率发表情7
#     'reward_talk':[(1,(5,7),'1-7')],
#     # 10，要离开牌桌，20几率，发表情15
#     'leave_talk':[(20,(0,0),'1-15')],
# }


def random_time(segs_str):
    segs = segs_str.split("-")
    begin = timestr_to_seconds(segs[0])
    end = timestr_to_seconds(segs[1])

    seconds = random.randint(begin,end)
    h = seconds / 3600
    m = (seconds % 3600) / 60
    s = seconds - h * 3600 - m * 60

    nd = datetime.now().date()
    if 0 < h < 4:
        nd = nd + timedelta(days=1)
    return datetime(nd.year,nd.month, nd.day, h,m,s)

def timestr_to_seconds(timestr):
    hm_str = timestr.split(":")
    hour = int(hm_str[0])
    min = int(hm_str[1])
    return hour * 3600 + min * 60

def random_duration(segs_str):
    segs = segs_str.split("-")
    dur = random.randint(int(segs[0]),int(segs[1]))
    dur = 60 if dur < 60 else dur
    return dur

def seconds_between_times(time1,time2, offset = 0):
    seconds1 = time1.hour * 3600 +time1.minute * 60 + time1.second
    seconds2 = time2.hour * 3600 +time2.minute * 60 + time2.second
    return abs(seconds1 - seconds2 - offset)

def midnight_seconds(start_time, run_time, now_time):
    seconds1 = start_time.hour * 3600 +start_time.minute * 60 + start_time.second
    seconds2 = now_time.hour * 3600 +now_time.minute * 60 + now_time.second
    far_midnight_seconds = 86400 - seconds1
    remain_times = run_time - far_midnight_seconds
    if far_midnight_seconds + seconds2 > remain_times:
        return True
    return False

def get_can_bet(gold):
    if gold > 100000000:                        # 当玩家的金币超过1亿时，可下注1千万，2千万，5千万
        return 10000000,20000000,50000000
    elif gold > 50000000 and gold < 100000000: # 当玩家的金币超过5千万时，可下注2百万，5百万，2千万
        return 2000000,5000000,20000000
    elif gold > 10000000 and gold < 50000000:  # 当玩家的金币超过1千万时，可下注1百万，2百万，5百万
        return 1000000,2000000,5000000
    elif gold > 5000000 and gold < 10000000:   # 当玩家的金币超过5百万时，可下注20万，50万，2百万
        return 200000,500000,2000000
    elif gold > 1000000 and gold < 5000000:    # 当玩家的金币超过1百万时，可下注10万，20万，50万
        return 100000,200000,500000
    elif gold > 500000 and gold < 1000000:     # 当玩家的金币超过50万时，可下注2万，5万，20万
        return 20000,50000,200000
    elif gold > 100000 and gold < 500000:       # 当玩家的金币超过10万时，可下注1万，2万，5万
        return 10000,20000,50000
    elif gold > 50000 and gold < 100000:        # 当玩家的金币超过5万时，可下注2千，5千，2万
        return 2000,5000,20000
    elif gold > 10000 and gold < 50000:        # 当玩家的金币超过1万时，可下注1千，2千，5千
        return 1000,2000,5000
    else:
        return 0,0,0

def can_bet(gold):
    """
    用户最大能投注的最大金币 * 10倍数
    :param gold: 用户金币
    :return: 投注规则
    """
    if gold >= 50000000 * 6:
        return 'gt_bet'
    elif gold >= 20000000 * 6:
        return 'gt_bet'
    elif gold >= 5000000 * 6:
        return 'gt_bet'
    elif gold >= 2000000 * 6:
        return 'gt_bet'
    elif gold >= 500000 * 6:
        return 'gt_bet'
    elif gold >= 200000 * 6:
        return 'gt_bet'
    elif gold >= 50000 * 6:
        return 'gt_bet'
    elif gold >= 20000 * 6:
        return 'gt_bet'
    elif gold >= 5000 * 6:
        return 'lt_bet'
    else:
        return 'lt_bet'

def get_offline_time(start_time, robot_duration):
    start_unix_time = int(time.mktime(start_time.timetuple()))
    end_unix_time = start_unix_time + robot_duration

    end_datetime = datetime.fromtimestamp(end_unix_time)
    return end_datetime



ROBOT_CONF = {
    'charge_gold':(100000,1000000),
    'gt_bet':[
        (20,(1,)),
        (20,(2,)),
        (15,(1,2,)),  #
        (10,(3,)),
        (10,(1,3,)), #
        (10,(2,2,)), #
        (5,(2,3,)),
        (2,(1,2,3,)), #
        (2,(2,2,2,)), #
        (2,(2,2,2,2,)), #
        (2,(2,2,2,2,2,)), #
        (2,(3,3,)) #
    ],
    'lt_bet':[
        (60,(1,)),
        (30,(2,)),
        (10,(1,2,)),
    ]
}


class Test:
    def __init__(self, foo):
        self.lock = foo
        self.players = []
        self.dal = Dal()

class Dal:
    def get_user(self,id):
        return User(id)

class User:
    def __init__(self,uid):
        self.id = uid
        self.gold = random.randint(1,100)

class Foo:
    def __init__(self):
        pass

    def acquire(self):
        pass

    def release(self):
        pass
if __name__ == '__main__':
    # r = Robot(11,'')
    # r.get_bet_gold()
    # print r.bet_gold
    # now_time = datetime.now().time()
    # for uid, times in RobotManager(None).prepare_robots.items():
        # pass
        # print uid,times,seconds_between_times(times[0][0], now_time),now_time
        # seconds_between_times(times[0][0], now_time)



    rm = RobotManager(Test(Foo()))
    for uid, timetuple in rm.prepare_robots.items():
        print uid,timetuple
    # print rm.robots[30631].online_times
    # gevent.sleep(5)
    print 'done'
