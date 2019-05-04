# -*- coding: utf-8 -*-
import random

__author__ = 'Administrator'

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import gevent
from gevent import monkey;monkey.patch_all()
from gevent import lock
from gevent.queue import Queue

import time
import logging
import traceback

from db.connect import Session
from dal.core import DataAccess

from proto import  struct_pb2 as pb2
from proto.texas_pb2 import *
from message.resultdef import *

from config.broadcast import BORADCAST_CONF
from hall.messagemanager import MessageManager
from hall.rewardbox import texas_reward_box

from texasconf import *
from texas import Texas
from eventsender import TableEventSender

class Player:
    def __init__(self, table, uid, user, access_service, seat):
        self.table = table

        self.seat = -1
        self.uid = uid
        self.user = user
        self.access_service = access_service
        self.seat = seat
        self.gold = 0
        self.is_connected = True
        self.idle_time = int(time.time())

        self.watch_max = []

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
                texas_reward_box(service, r, self.uid)
                self.play_result_counter = []
            elif play_result == -1 and len(self.play_result_counter) == 4:
                texas_reward_box(service, r, self.uid)
                self.play_result_counter = []



    def update_user_info(self):
        self.gold = self.user.get_gold()
        self.is_connected = True


    def update_by_disconnected(self):
        self.access_service = -1
        self.is_connected = False

    def modify_gold(self, session, gold):
        gold = self.user.modify_gold(session,int(gold))
        return gold

    def get_gold(self):
        self.gold = self.user.get_gold()
        return self.gold

    def has_gold(self,gold):
        return self.user.gold >= gold

    def update_by_reconnected(self,user,access_service):
        self.user = user
        # self.user_gf = self.table.manager.dal.get_user_gf(user.id)
        self.access_service = access_service
        self.nick = user.nick
        self.avatar = user.avatar
        self.gold = self.user.get_gold()
        self.is_connected = True

    def watch_max_kick(self):
        if len(self.watch_max) >= 5 and all(self.watch_max) == True:
            return True
        return False

    def get_brief_proto_struct(self, pb_brief):
        if pb_brief == None:
            pb_brief = pb2.PlayerBrief()

        print '~~~~~~~~~~~~~~~~~~~~',self.user,type(self.user)
        pb_brief.uid = self.uid
        pb_brief.avatar = self.user.avatar
        pb_brief.gold = self.user.get_gold()
        pb_brief.seat = self.seat
        pb_brief.nick = self.user.nick
        pb_brief.vip = self.user.vip
        pb_brief.vip_exp = 0 if self.user.vip_exp is None else self.user.vip_exp
        pb_brief.sex = 0 if self.user.sex == 0 else 1

        return pb_brief

    def incr_watch(self, is_watch = True):
        logging.info(u'用户=%d，次数=%s' % (self.uid, self.watch_max))
        if len(self.watch_max) >= TEXAS_WATCH_MAX:
            self.watch_max.pop(0)
        self.watch_max.append(is_watch)

    def check_watch(self):
        if len(self.watch_max) == TEXAS_WATCH_MAX and False not in self.watch_max:
            return True
        return False


class Table:
    def __init__(self,manager,table_id,type):
        self.id = table_id
        self.game = None
        self.table_type = type
        self.manager = manager
        self.players = {}
        self.dealer = -1

        self.deal_counter = 0
        self.deal_trigger = 0

        self.redis = manager.redis
        self.table_key = "texas_" + str(manager.service.serviceId) + "_" + str(table_id)

        self.sender = TableEventSender(self)
        self.lock = lock.Semaphore()

        self.ready_time = 0

        self.table_event_queue = Queue()
        gevent.spawn_later(1, self.real_send_event)

        logging.info(u'Table：新牌桌=%d，游戏初始化开始' % self.id)

        self.game = Texas(self,*TABLE_GAME_CONFIG[self.table_type])

    def is_ready(self):
        # return int(time.time()) > self.ready_time
        if self.game != None:
            return self.game.is_started()
        return False

    def player_reconnected(self,uid,user,access_service):
        player = self.get_player(uid)
        if player == None:
            return
        player.update_by_reconnected(user,access_service)

        self.redis.hset(self.table_key,uid,access_service)
        self.redis.hset(self.manager.room_key,uid,self.id)
        self.sender.send_player_connect(player,True)

    def player_disconnected(self,uid):
        player = self.get_player(uid)
        if player == None:
            return

        if self.game != None and self.game.is_started() and self.game.is_gambler(uid):
            player.update_by_disconnected()
            self.sender.send_player_connect(player,False)
        else:
            self.remove_player(uid)

    def add_player(self,uid,user,access_service):
        if self.is_full() or self.has_player(uid):
            return None

        used = [x.seat for x in self.players.values()]
        not_used = [x for x in xrange(MAX_TABLE_PLAYER) if x not in used]
        seat = random.choice(not_used)
        player = Player(self,uid,user,access_service,seat)
        self.players[uid] = player

        self.redis.hset(self.table_key,uid,access_service)
        self.redis.hset(self.manager.room_key,uid,self.id)
        self.sender.send_player_join(player)
        return player

    def update_player_info(self,uid):
        player = self.get_player(uid)
        if player != None:
            player.update_user_info()
            self.sender.send_player_updated(player)

    def is_gambler(self,uid):
        return self.game != None and uid in self.game.gamblers

    def other_players(self,uid):
        real_players = set([x.uid for x in self.players if x.uid > 0])
        return real_players - set([uid])

    def is_game_started(self):
        return self.game != None and self.game.is_started()

    def remove_player(self,uid, is_kicked = False):
        if self.game != None and uid in self.game.gamblers:
            self.game.gamblers.pop(uid)

        player = self.get_player(uid)
        if player == None:
            return RESULT_FAILED_INVALID_PLAYER

        self.players.pop(uid,None)

        self.redis.hdel(self.table_key,uid)
        self.redis.hdel(self.manager.room_key,uid)
        if not is_kicked:
            self.sender.send_player_leave(player)

        return 0

    def kick_player(self,uid):
        self.sender.send_player_kicked(uid)
        self.remove_player(uid,is_kicked = True)

    def has_player(self,uid):
        return uid in self.players

    def get_player(self,uid):
        return self.players.get(uid,None)

    def countof_players(self):
        return len(self.players)

    def is_empty(self):
        return len(self.players) == 0

    def is_full(self):
        return len(self.players) == MAX_TABLE_PLAYER

    def kick_invalid_players(self):
        config = TABLE_GAME_CONFIG[self.table_type]
        for player in self.players.values():
            # if not player.is_connected:
            #     logging.info(u'系统：掉线，玩家=%didle_time=%d' % (player.uid, player.idle_time))
            #     self.remove_player(player.uid)
            #     continue
            # if player.has_gold(TEXAS_MIN_GOLD) == False:
            #     logging.info(u'系统：用户=%d金币小于最低额度，马上踢掉该用户' % player.uid)
            #     self.kick_player(player.uid)
            #     continue

            if player.check_watch():
                logging.info(u'系统：观战超出次数踢人，玩家=%d观战=%d，官方=%d' % (player.uid, len(player.watch_max), TEXAS_WATCH_MAX))
                self.kick_player(player.uid)
                continue

            # if int(time.time()) - player.idle_time >= 300 :
            #     logging.info(u'系统：超时不操作，玩家=%didle_time=%d' % (player.uid, player.idle_time))
            #     self.kick_player(player.uid)
            #     continue


            # """
            # gold = player.get_gold()
            # if config[1] >= 0 and gold > config[1]:
            #     self.kick_player(-1,player.uid)
            #     continue
            # """

    def notify_event(self,event):
        event_type = event.header.command
        event_data = event.encode()
        service = self.manager.service
        for player in self.players.values():
            if player.access_service < 0:
                continue
            #service.send_client_event(player.access_service,player.uid,event_type,event_data)
            self.send_table_event(player.access_service,player.uid,event_type,event_data)

    def notify_event_player(self,event,player):
        if player.access_service < 0:
            return
        event_type = event.header.command
        event_data = event.encode()
        #service = self.manager.service
        #service.send_client_event(player.access_service,player.uid,event_type,event_data)
        self.send_table_event(player.access_service,player.uid,event_type,event_data)

    def send_table_event(self,access_service,uid,event_type,event_data):
        self.table_event_queue.put_nowait((access_service,uid,event_type,event_data,))

    def real_send_event(self):
        service = self.manager.service
        while True:
            access_service,uid,event_type,event_data = self.table_event_queue.get()
            service.send_client_event(access_service,uid,event_type,event_data)

    def __repr__(self):
        s = "Table["
        for player in self.players.values():
            s += str(player) + "|"
        s += "]\n"
        s += str(self.game)
        return s

    def get_proto_struct(self, pb_table = None):
        if pb_table == None:
            pb_table = TexasTable()
        pb_table.id = self.id

        for player in self.players.values():
            player.get_brief_proto_struct(pb_table.player_briefs.add())

        if self.game != None:
            self.game.get_proto_struct(pb_table)
        return pb_table

    def get_session(self):
        return Session()

    def close_session(self, session):
        if session:
            session.close()
            session = None

    def broadcast_win(self, gambler):
        if gambler != None and gambler.win_gold > BROADCAST_GOLD_MIN:
            MessageManager.push_texas_win(self.redis, gambler.uid, gambler.player.user.nick,gambler.player.user.vip_exp, gambler.final_poker.poker_type, gambler.win_gold)

class TableManager:

    def __init__(self, service):
        self.service = service
        if service != None:
            self.redis = service.server.redis
            self.room_id = service.serviceId
        else:
            self.redis = None

        self.tables = {}


        self.session = Session()
        self.dal = DataAccess(self.redis)

        if self.redis != None:
            self.room_key = "texas_room_users_" + str(self.room_id)
            self.redis.delete(self.room_key)
            self.redis.hset(self.room_key,"info","")

            keys = self.redis.keys("texas_" + str(service.serviceId) + "*")
            for k in keys:
                self.redis.delete(k)
        self.lock = lock.Semaphore()
        gevent.spawn_later(5,self.scan_idle_player)

    def scan_idle_player(self):
        while True:
            now = time.time()
            real_count = 0
            for _,t in self.tables.items():
                real_count += len([x.uid for x in t.game.gamblers.values() if not x.is_robot()])
            self.redis.hset('texas_online', 'real_total', real_count)
            gevent.sleep(30)

    def get_table(self,table_id):
        return self.tables.get(table_id)

    def new_table(self,table_type):
        table_id = self.redis.incr("texas_table_id")
        table = Table(self, table_id, table_type)
        self.tables[table_id] = table
        return table

    def get_player_table(self,uid):
        for table in self.tables.values():
            if table.has_player(uid):
                return table
        return None

    def get_players_by_access_services(self,access_services):
        players = []
        for table in self.tables.values():
            for player in table.players.values():
                if player.access_service in access_services:
                    players.append(player)
        return players

    def check_table_type(self,table_type,gold):
        config = TABLE_GAME_CONFIG[table_type]
        if config[0] >= 0 and gold < config[0]:
            return RESULT_FAILED_LESS_GOLD
        if config[1] >= 0 and gold > config[1]:
            return RESULT_FAILED_MORE_GOLD
        return 0

    def find_suitable_table_type(self,gold):
        table_type = -1
        for k,v in TABLE_GAME_CONFIG.items():
            if v[0] >=0 and gold < v[0]:
                continue
            if v[1] >=0 and gold > v[1]:
                continue
            table_type = k
        return table_type

    def reconnect_table_player(self,table,uid,user,access_service):
        if table == None:
            return
        table.lock.acquire()
        try:
            table.player_reconnected(uid,user,access_service)
        finally:
            table.lock.release()

    def remove_table_player(self,table,uid):
        if table == None:
            return
        table.lock.acquire()
        try:
            table.remove_player(uid)
        finally:
            table.lock.release()

    def sort_table(self,t1,t2):
        is_t1_started = t1.is_game_started()
        is_t2_started = t2.is_game_started()
        if is_t1_started == is_t2_started:
            return cmp(len(t1.players),len(t2.players))
        if is_t1_started:
            return 1
        else:
            return -1

    def sit_table(self,target_table_id,uid,access_service, not_table_ids):
        user = self.dal.get_user(uid)
        if user == None:
            return RESULT_FAILED_INVALID_USER,None

        table_type = self.find_suitable_table_type(user.gold)
        if table_type < 0:
            return RESULT_FAILED_LESS_GOLD,None
        table = None

        old_table = self.get_player_table(uid)
        if old_table != None and old_table.id in not_table_ids:
            old_table = None
        if target_table_id < 0:
            if old_table != None:
                logging.info(u'玩家=%d断网重连，old_table=%d' % (uid,old_table.id))
                self.reconnect_table_player(old_table,uid,user,access_service)
                return 0, old_table

            all_tables = [t for t in self.tables.values() \
                          if t.table_type == table_type and not t.is_full() and t.id not in not_table_ids and t.game.status != TEXAS_OVER]
            all_tables.sort(cmp=self.sort_table,reverse = True)
            for t in all_tables:
                if t.is_gambler(uid):
                    # if user is gambler of this table,it means that he quit this game before ,so didnot arrange this table
                    logging.info('if user is gambler of this table,it means that he quit this game before ,so didnot arrange this table')
                    continue
                table = t
                break
            if table == None:
                table = self.new_table(table_type)
                logging.info(u'开启了新牌局=%d' % table.id)
        else:
            if old_table != None and target_table_id == old_table.id:
                logging.info(u'用户=%d指定了断网重连的牌桌=%d' % (uid, old_table.id))
                self.reconnect_table_player(old_table,uid,user,access_service)
                return 0,old_table

            self.remove_table_player(old_table,uid)
            table = self.get_table(target_table_id)
            if table == None or table.is_full():
                logging.info(u'用户=%d指定了老牌桌ID，但是找不到老牌桌=%d，返回异常码' % (uid, target_table_id))
                return RESULT_FAILED_INVALID_TABLE,None
        table.lock.acquire()
        try :
            check_result = self.check_table_type(table.table_type,user.gold)
            if check_result < 0:
                return check_result,None
            logging.info(u'table_id=%d，有用户=%d进来了,round_start_time=%s' % (table.id, uid, table.game.round_start_time))
            player = table.add_player(uid,user,access_service)
            if len(table.players) == 1:
                gevent.spawn_later(1, table.game.start)
            if player == None:
                return RESULT_FAILED_TABLE_IS_FULL,None
        finally:
            table.lock.release()
        return 0,table

if __name__ == '__main__':

    tm = TableManager(None)
    print tm.find_suitable_table_type(2000)