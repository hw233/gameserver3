# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import time
import traceback
import gevent
import json
import random
from datetime import datetime
from gevent import monkey;monkey.patch_all()
from gevent import lock
from gevent.queue import Queue

import logging
from sqlalchemy.sql import and_
from db.connect import *
from dal.core import *

from proto import struct_pb2 as pb2
from proto import war_pb2
from wartable.game import *
from wartable.gameconf import *
from wartable.eventsender import *

from hall.messagemanager import *
from db.war_player_brief import *
from db.rank_war_top import *
from config import var
from robot import seconds_between_times,Robot
from util.commonutil import *

from hall.rewardbox import war_reward_box

class Player:

    def __init__(self, uid, user,access_service, seat):
        self.uid = uid
        self.avatar = user.avatar
        self.nick = user.nick
        self.sex = user.sex
        self.vip_exp = user.vip_exp
        self.gold = user.gold
        self.diamond = user.diamond
        self.seat = seat

        self.total_games = 0    # db获取
        self.max_win_gold = 0   # db获取
        self.recent_rich_rank = 0
        self.recent_win_games = 0
        self.recent_bet_gold = 0

        self.reward_gold = 0

        self.access_service = access_service
        self.user_dal = user

        self.player_results = []
        self.bet_list = []
        self.win_list = []

        self.offline_time = 0
        self.idle_time = time.time()
        self.is_idle = False
        self.online = 0
        self.is_exit = False

        self.play_result_counter = []

    def incr_reward_box(self, play_result):
        if len(self.play_result_counter) == 0:
            self.play_result_counter.append(play_result)
        else:
            if self.play_result_counter[-1] != play_result:
                self.play_result_counter = [play_result]
            else:
                self.play_result_counter.append(play_result)

    def check_reward_box(self, service, r, play_result):
        self.incr_reward_box(play_result)

        if all([True for x in self.play_result_counter if x == play_result]):
            if play_result == 1 and len(self.play_result_counter) == 3:
                war_reward_box(service, r, self.uid)
                self.play_result_counter = []
            elif play_result == -1 and len(self.play_result_counter) == 4:
                war_reward_box(service, r, self.uid)
                self.play_result_counter = []


    def set_online(self, redis, is_online):
        redis.hset('war_online', self.uid, is_online)
        self.online = is_online

    def is_online(self, redis):
        if int(redis.hget('war_online', self.uid)) == 1:
            return True
        return False

    def delete_online(self, redis, table):
        redis.hdel('war_online', self.uid)
        del table.players[self.uid]

    def plus_gold(self, table, gold):
        # logging.info(u'plus_gold ready acquire')
        # table.lock.acquire()
        # logging.info(u'plus_gold acquire')
        try:
            session = table.get_session()
            context_session =  get_context('session')
            if context_session == None:
                set_context('session', session)
            self.user_dal = table.dal.get_user(self.uid)
            self.user_dal.gold += int(gold)
            table.dal.save_user(session, self.user_dal)
            self.gold = self.user_dal.gold
            # gold = self.user_dal.modify_gold(session, +int(gold))
            # self.user_dal.save
            # self.gold = gold
            session.flush()
        finally:
            # logging.info(u'用户+钱：%d，+之后有 %d' % (gold, self.gold))
            table.close_session(session)
            # table.lock.release()
            # logging.info(u'plus_gold release')


    def minus_gold(self, table, gold):
        # table.lock.acquire()
        try:
            session = table.get_session()
            context_session =  get_context('session')
            if context_session == None:
                set_context('session', session)

            self.user_dal = table.dal.get_user(self.uid)
            self.user_dal.gold -= gold
            # gold = self.user_dal.modify_gold(session, -int(gold))
            table.service.dal.save_user(session, self.user_dal)
            self.gold = self.user_dal.gold
            session.flush()
        finally:
            table.close_session(session)
            # table.lock.release()

    def get_gold(self):
        self.gold = self.user_dal.gold
        return self.user_dal.gold

    def add_player_result(self, player_result):
        # logging.info(u'当前玩游戏结果记录总数：%d' % len(self.player_results))
        if len(self.player_results) >= TABLE_GAME_CONF[1]:
            self.player_results.pop(0)
            # logging.info(u'被弹出的第一个：%s' % str(self.player_results.pop(0)))
            # logging.info(u'超出最大记录，弹出第一个，返回长度：%d' % len(self.player_results))

        self.player_results.append(player_result)
        # logging.info(u'压入一个，最大长度：%d' % len(self.player_results))

    def get_proto_struct(self, pb_war_player):
        if pb_war_player == None:
            pb_war_player = pb2.WarPlayer()
        pb_war_player.uid = self.uid
        pb_war_player.avatar = self.avatar
        pb_war_player.nick = self.nick.decode('utf-8')
        pb_war_player.sex = self.sex
        pb_war_player.gold = int(self.get_gold())
        pb_war_player.diamond = self.diamond
        pb_war_player.seat = self.seat
        pb_war_player.vip_exp = self.vip_exp

        pb_war_player.total_games = self.total_games
        pb_war_player.max_win_gold = self.max_win_gold
        pb_war_player.recent_rich_rank = self.recent_rich_rank
        pb_war_player.recent_win_games = self.recent_win_games
        pb_war_player.recent_bet_gold = self.recent_bet_gold

        pb_war_player.reward_gold = self.reward_gold

    def brief_log(self, table, uid):
        #table.lock.acquire()
        #logging.info(u'brief_log acquire')
        session = table.get_session()
        try:
            user = session.query(TWarPlayerBrief).filter(TWarPlayerBrief.uid == uid).first()
            if user == None:
                user = TWarPlayerBrief()
                user.uid = uid
                user.total_games = 0
                user.max_win_gold = 0
                session.add(user)
                session.flush()
            else:
                self.total_games = user.total_games
                self.max_win_gold = user.max_win_gold
        finally:
            table.close_session(session)
            #table.lock.release()
            #logging.info(u'brief_log release')


    def save_player_brief(self, table, uid, gold):
        if gold > self.max_win_gold:
            self.max_win_gold = gold
            # logging.info(u'当前用户赢钱超过自己历史最大记录：new_max_gold-%d,old_max_win_gold-%d' % (gold,self.max_win_gold))

        # table.lock.acquire()
        # logging.info(u'save_player_brief acquire')
        session = table.get_session()
        try:
            session.query(TWarPlayerBrief).filter(TWarPlayerBrief.uid == uid).update({
                TWarPlayerBrief.max_win_gold: self.max_win_gold,
                TWarPlayerBrief.total_games:TWarPlayerBrief.total_games + 1
            })
        finally:
            table.close_session(session)
            # table.lock.release()
            # logging.info(u'save_player_brief release')


    def save_player_rank(self, table, uid, win_gold):
        session = table.get_session()
        # table.lock.acquire()
        # logging.info(u'save_player_rank acquire')
        try:
            #session.query(TRankWarTop).filter(TRankWarTop.uid == uid).update({
            #    TRankWarTop.total: TRankWarTop.total + win_gold
            #})
	    session.query(TRankWarTop).filter(and_(TRankWarTop.uid == uid, TRankWarTop.add_date == time.strftime('%Y-%m-%d'))).update({
                TRankWarTop.total: TRankWarTop.total + win_gold
            })
        finally:
            table.close_session(session)
            # table.lock.release()
            # logging.info(u'save_player_rank release')


    def incr_win(self, is_win):
        if len(self.win_list) >= TABLE_GAME_CONF[1]:
            self.win_list.pop(0)
        self.win_list.append(is_win)
        self.recent_win_games = sum([1 for x in self.win_list[:TABLE_GAME_CONF[1]] if x == True])

    def save_recent(self):
        self.recent_win_games = sum([1 for x in self.player_results if x.win_gold > 0])
        self.recent_bet_gold = sum([x.bet_gold for x in self.player_results])
        # logging.info(u'刷新用户20局记录,recent_win_games=%d, recent_bet_gold=%d' %(self.recent_win_games, self.recent_bet_gold))

    def get_bet_gold(self):
        return sum(self.bet_list)

    def __repr__(self):
        return 'uid=%d,seat=%d, gold=%d, total_games=%d, max_win_gold=%d,win_games=%d,bet_gold=%d,online=%d' % (self.uid,
                                                            self.seat,
                                                            self.gold,
                                                            self.total_games,
                                                            self.max_win_gold,
                                                            self.recent_win_games,
                                                            self.recent_bet_gold,
                                                            self.online
                                                            )

class Table:

    def __init__(self, service):

        self.service = service
        self.robot_manager = None
        self.redis = self.service.redis
        self.dal = self.service.dal
        self.lock = lock.Semaphore()
        self.session = None
        self.game = None
        self.players = {}

        self.rank = Rank(self)
        self.reward_pool = RewardPool(self)
        self.game_log = GameLog(self)
        self.poker_maker = PokerMaker(self)

        self.sender = TableEventSender(self)
        gevent.spawn_later(1, self.restart_game)
        gevent.spawn_later(5, self.real_send_event)
        gevent.spawn_later(20, self.scan_idle_player)

        gevent.spawn_later(2, self.reload_user_info)
        self.table_event_queue = Queue()

        self.continuous_lucky_round = 0

        self.trans_round_num = -1
        self.run_round_num = 0

    def get_continuous_lucky_round(self):
        if self.continuous_lucky_round > 8:
            return {'gt_dui8':60,'shun':40}
        elif self.continuous_lucky_round == 8:
            return {'gt_dui8':60,'shun':40}
        elif self.continuous_lucky_round == 7:
            return {'gt_dui8':50,'shun':30}
        elif self.continuous_lucky_round == 6:
            return {'gt_dui8':40,'shun':20}
        elif self.continuous_lucky_round == 5:
            return {'gt_dui8':30,'shun':10}
        else:
            return  {}

    def is_continuous_unlucky(self):
        if self.continuous_lucky_round >= 5:
            return True
        return False

    def incr_continuous_unlucky(self):
        self.continuous_lucky_round += 1


    def get_session(self):
        if self.session == None:
            return Session()
        return self.session

    def close_session(self, session):
        if session:
            session.close()
            session = None

    def reload_user_info(self):
        while True:
            _,str_user_update = self.redis.brpop("war_user_update")
            user_update = json.loads(str_user_update)
            self.lock.acquire()
            logging.info(u'reload_user_info lock')
            try:
                if self.players.has_key(user_update['uid']):
                    user_info = self.dal.get_user(int(user_update['uid']))
                    self.players[user_update['uid']].user_dal = user_info
                    self.players[user_update['uid']].gold = user_info.gold

                    # self.players[user_update['uid']].user_dal.diamond = user_update['diamond']
                    self.players[user_update['uid']].diamond = user_info.diamond
                    self.players[user_update['uid']].vip_exp = user_info.vip_exp
                    # if user_update.has_key('vip_exp'):
                    #     self.players[user_update['uid']].user_dal.vip_exp = user_update['vip_exp']
                    #     self.players[user_update['uid']].vip_exp = user_update['vip_exp']

                    # if user_update.has_key('money'):
                    #     self.players[user_update['uid']].user_dal.money = user_update['money']

                    self.service.dal.save_user(self.get_session(), self.players[user_update['uid']].user_dal)

                    self.game.player_result[user_update['uid']].gold = user_info.gold
                    self.game.player_result[user_update['uid']].diamond = user_info.diamond
            finally:
                self.lock.release()
                logging.info(u'reload_user_info release')

    def is_online_robot(self,uid):
        if self.robot_manager != None and uid in self.robot_manager.robots:
            robot = self.robot_manager.robots[uid]

            if robot.status == robot.WAIT_OFFLINE:
                if self.rank.is_lucky(robot.uid) or self.rank.is_rich(robot.uid):
                    logging.info(u'机器人(%d)超过上线时间 %d，但是上榜了，等待下次删除' % (uid, robot.status))
                    robot.run_time = (-1, -1)
                    return True
                else:
                    logging.info(u'机器人(%d)超过上线时间 %d，删除机器人' % (uid, robot.status))
                    return False

            if robot.run_time[0] == -1 or robot.run_time[1] == -1:
                return False

            if self.robot_manager.robot_can_leave(robot, datetime.now()):
                logging.info(u'机器人(%d)超过上线时间 %d，下一局删除机器人' % (uid, robot.status))
                robot.set_status(robot.WAIT_OFFLINE)
            else:
                start_time,end_time = robot.get_play_timetuple()
                logging.info(u'机器人(%d)在线中 %d，不做操作，开始时间：%s ,结束时间：%s' % (uid, robot.status, start_time, end_time))
                # logging.info(u'机器人(%d)在线中 %d，online_times:%s' % (robot.uid, robot.status, robot.time_tuple))
                # print u'%d)机器人(%d)在线中 %d，online_times:%s' % (len(self.robot_manager.robots), robot.uid, robot.status, robot.time_tuple)
        return True

    def check_round_rate(self):
        logging.info(u'胜负比例：total:%d,round:%d'%(self.trans_round_num,self.run_round_num))
        if self.trans_round_num == -1:
            self.trans_round_num = random.randint(5,9)
            self.run_round_num = 1
            return False
        elif self.run_round_num >= self.trans_round_num:
            logging.info(u'互换, round:%d ,total:%d' % (self.run_round_num, self.trans_round_num))
            self.trans_round_num = -1
            return True
        else:
            self.run_round_num += 1
            return False


    def sit_table(self,user, access_service):
        if user.id <= 0:
            return None
        if self.players.has_key(user.id) and self.players[user.id].access_service != -1:
            self.players[user.id].offline_time = 0
            self.players[user.id].set_online(self.redis, 1)
            self.players[user.id].gold = user.gold
            self.players[user.id].diamond = user.diamond
            self.players[user.id].user_dal = user
            self.players[user.id].vip_exp = user.vip_exp
            if not self.game.player_result.has_key(user.id):
                self.game.player_result[user.id] = PlayerResult(user.id)
                self.game.player_result[user.id].gold = self.players[user.id].get_gold()
            return self.players[user.id]
        player = Player(user.id, user, access_service, -1)
        player.set_online(self.redis, 1)
        player.brief_log(self, user.id)
        self.init_rank_record(user.id)
        self.players[user.id] = player
        self.game.player_result[user.id] = PlayerResult(user.id)
        self.game.player_result[user.id].gold = player.get_gold()
        return player

    def init_rank_record(self, uid):
        session = self.get_session()
        try:
            user_rank = session.query(TRankWarTop).filter(and_(TRankWarTop.uid == uid, TRankWarTop.add_date == time.strftime('%Y-%m-%d'))).first()
            if user_rank == None and uid > 0:
                user_rank = TRankWarTop()
                user_rank.add_date = time.strftime('%Y-%m-%d')
                user_rank.uid = uid
                user_rank.created_time = time.strftime('%Y-%m-%d %H:%M:%S')
                user_rank.total = 0
                session.add(user_rank)
                session.flush()
        finally:
            self.close_session(session)

    def remove_player(self,uid):
        player = self.players.get(uid)
        if player == None:
            return False
        player.set_online(self.redis, 0)
        return len(self.players) == 0

    def restart_game(self):
        logging.info(u'初始化开始。。。')
        logging.info(u'奖池金币：%d' % self.reward_pool.gold)
        self.init_game()
        while True:
            self.recheck()
            logging.info('restart_game...')
            logging.info(u'在线用户=%d，奖池=%d，库存=%d' % (len(self.players.keys()), self.reward_pool.gold, self.reward_pool.stack))
            self.game = WarGame(self)
            self.game.start()
            self.game.action()
            self.game.over()
            logging.debug(u'all event done!!!')
            gevent.sleep(RESTART_TIME)

    def recheck(self):
        # session = self.get_session()
        # try:
            # war_log = session.query(TWarLog).order_by(TWarLog.id.desc()).first()
        # finally:
        #     self.close_session(session)
        # self.lock.acquire()

        self.lock.acquire()
        try:
            logging.info(u'recheck acquire')
            if self.redis.exists('war_game'):
                war_game = self.redis.hgetall('war_game')
                self.reward_pool.gold = int(war_game['reward_pool']) if war_game.has_key('reward_pool') and int(war_game['reward_pool']) > 0 else 0
                self.reward_pool.stack = int(war_game['lucky_stack']) if war_game.has_key('lucky_stack') and int(war_game['lucky_stack']) > 0 else 0
        except:
            traceback.print_exc()
        finally:
            self.lock.release()
            logging.info(u'recheck release')
        logging.debug(u'重新加载，奖池金币：%d，库存金币：%d' % (self.reward_pool.gold,self.reward_pool.stack))

        if len(self.game_log.ways) > 150:
            self.game_log.ways = self.game_log.ways[-75:]

    def init_game(self):
        self.lock.acquire()
        try:
            logging.info(u'init_game acquire')
            if not self.redis.exists('war_game'):
                self.redis.hset('war_game','reward_pool', 0)
                self.redis.hset('war_game','lucky_stack', 0)
            logging.debug(u'获得最近20局的记录：%d' % len(self.game_log.data_brief))
            self.game_log.data_brief = self.game_log.get_war_brief(20, self)
        except:
            traceback.print_exc()
        finally:
            self.lock.release()
            logging.info(u'init_game release')

    def get_user_countof(self):
        robot_count = 0
        users = self.redis.hgetall('war_online')
        war_users = set([uid for uid,is_online in users.items() if int(is_online) == 1])

        users = self.redis.hgetall('online')
        online_users = set([uid for uid,access_service in users.items() if int(access_service) == 100])

        in_war_users = war_users & online_users
        robot_count = len(war_users) - robot_count

        cache_count = robot_count + len(in_war_users)
        mem_count = len([1 for x in self.players.values() if x.access_service == -1])
        logging.info(u'cache_count: %d, mem_count: %d' % (cache_count, mem_count))
        return cache_count
        # return len([1 for x in self.players.values() if x.access_service == -1])


    def get_proto_struct(self, pb_table, history = True):
        if pb_table == None:
            pb_table = pb2.WarTable()

        lucky = self.rank.lucky_player
        if lucky != 0:
            lucky.get_proto_struct(pb_table.lucky_player)

        for player in self.rank.rich_players[:TABLE_GAME_CONF[3]]:
            player.get_proto_struct(pb_table.rich_players.add())

        pb_table.reward_pool = int(self.reward_pool.gold)
        pb_table.countof_players = self.get_user_countof() * 3 + 1
        if history:
            for log in self.game_log.data_brief[-TABLE_GAME_CONF[1]:]:
                log.get_proto_struct(pb_table.history.add())
        pb_table.remain_time = int(self.game.remain_time * 1000)
        # 状态：0:进行中(游戏中途进入游戏)，1：结算中,如果是0，则chips字段为桌面筹码数据，如果是1，result为结算数据
        pb_table.state = self.game.state
        if pb_table.state == 0:
            self.game.get_chips_proto_struct(pb_table)
        return pb_table

    def broadcast_war_award(self, user, gold):
        MessageManager.broadcast_type(self.redis, var.PUSH_TYPE['war_top1'], {
            'uid':user.id,
            'nick':user.nick,
            'vip_exp':user.vip_exp,
            'gold':gold
        })

    def broadcast_change_rich(self, user):
        if type(user) == tuple:
            print user
        uid = user.id if hasattr(user,'id') else user.uid
        MessageManager.broadcast_type(self.redis, var.PUSH_TYPE['war_change_rich'], {
            'uid':uid,
            'nick':user[0].nick,
            'vip_exp':user[0].vip_exp
        })
        

    def notify_event(self,event):
        event_type = event.header.command
        event_data = event.encode()
        try:
            for player in self.players.values():
                if player.access_service == -1:
                    if self.robot_manager == None:
                        # print 'robot_manager is None ',self.robot_manager
                        continue

                    if player.uid in self.robot_manager.robots:
                        self.robot_manager.robots[player.uid].on_server_event(event)
                else:
                    if player.is_online(self.redis):
                        self.send_table_event(player.access_service,player.uid,event_type,event_data)
                #service.send_client_event(player.access_service,player.uid,event_type,event_data)
        except:
            traceback.print_exc()
        finally:
            pass

    def send_table_event(self,access_service,uid,event_type,event_data):
        self.table_event_queue.put_nowait((access_service,uid,event_type,event_data,))

    def real_send_event(self):
        service = self.service
        while True:
            access_service,uid,event_type,event_data = self.table_event_queue.get()
            service.send_client_event(access_service,uid,event_type,event_data)

    def notify_one(self,event,player):
        event_type = event.header.command
        event_data = event.encode()
        try:
            if player.access_service == -1:
                if self.robot_manager == None:
                    return

                if player.uid in self.robot_manager.robots:
                    self.robot_manager.robots[player.uid].on_server_event(event)
            else:
                if player.is_online(self.redis):
                    self.send_table_event(player.access_service,player.uid,event_type,event_data)
        except:
            traceback.print_exc()
        finally:
            pass

        # self.send_table_event(player.access_service,player.uid,event_type,event_data)

    def scan_idle_player(self):
        while True:
            logging.info('scan_idle_player')
            now = time.time()
            self.lock.acquire()
            logging.info(u'scan_idle_player lock')
            try :
                for player in self.players.values():
                    if player.access_service == -1:
                        continue
                    if player.is_idle:
                        continue

                    if player.idle_time > 0 and now - player.idle_time > TABLE_GAME_CONF[7]:
                        self.sender.kick_player(player.uid)
                        player.set_online(self.redis, 0)
                        player.is_idle = True
                        logging.info("Player %d/on table is idle too long, so kick it out",player.uid)
            finally:
                self.lock.release()
                logging.info(u'scan_idle_player release')

            gevent.sleep(30)

