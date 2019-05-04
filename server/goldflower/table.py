#coding: utf-8
import gevent
from gevent import monkey;monkey.patch_all()
from gevent import lock
from gevent.queue import Queue


import json
import logging
import traceback
from sqlalchemy.sql import select, update, delete, insert, and_,or_, subquery, not_, null, func, text,exists
from sqlalchemy import desc

import random,time

from collections import Counter
from datetime import datetime
from datetime import date as dt_date
from datetime import time as dt_time

from proto.constant_pb2 import *

from message.base import *
from message.resultdef import *

from goldflower.game import *
from goldflower.gameconf import *
from goldflower.eventsender import *

from proto import struct_pb2 as pb2
from db.connect import *

from dal.core import *

class Player:
    def __init__(self,table,uid,user,access_service,seat):
        self.table = table
        self.uid = uid
        self.user = user
        self.user_gf = table.manager.dal.get_user_gf(uid)
        self.access_service = access_service
        self.seat = seat
        self.gold = 10000
        self.is_connected = True
        self.nick = user.nick
        self.avatar = user.avatar
        self.idle_time = time.time()

    def reload_user_gf(self):
        self.user_gf = self.table.manager.dal.get_user_gf(self.uid,True)

    def update_by_reconnected(self,user,access_service):
        self.user = user
        self.user_gf = self.table.manager.dal.get_user_gf(user.id)
        self.access_service = access_service
        self.nick = user.nick
        self.avatar = user.avatar
        self.gold = self.user.get_gold()
        self.is_connected = True

    def update_user_info(self):
        new_user = self.user.load_from_redis()
        self.nick = new_user.get('nick')
        self.user.nick = new_user.get('nick')
        self.avatar = new_user.get('avatar')
        self.user.avatar = new_user.get('avatar')
        self.gold = self.user.get_gold()
        self.user_gf = self.table.manager.dal.get_user_gf(self.uid, True)
        self.is_connected = True
        self.vip_exp = new_user.get('vip_exp')


    def update_by_disconnected(self):
        self.access_service = -1
        self.is_connected = False

    def has_gold(self,gold):
        return self.user.gold >= gold

    def get_gold(self):
        self.gold = self.user.get_gold()
        return self.gold

    def modify_gold(self,session,gold):
        gold = self.user.modify_gold(session,gold)
        return gold
    

    def __repr__(self):
        return "Player[%d/%d]" % (self.uid,self.seat)
         
    def get_brief_proto_struct(self,pb_brief = None):
        if pb_brief == None:
            pb_brief = pb2.PlayerBrief()

        pb_brief.uid = self.uid
        pb_brief.avatar = self.user.avatar
        pb_brief.gold = self.user.gold
        pb_brief.seat = self.seat
        pb_brief.nick = self.user.nick
        pb_brief.vip = self.user.vip
        if hasattr(self, 'vip_exp'):
            pb_brief.vip_exp = self.vip_exp
        else:
            pb_brief.vip_exp = 0 if self.user.vip_exp is None else self.user.vip_exp
        pb_brief.sex = 0 if self.user.sex == 0 else 1
        pb_brief.exp = self.user_gf.exp

        return pb_brief


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

        self.restart_game()
        self.redis = manager.redis
        self.table_key = "table_" + str(manager.service.serviceId) + "_" + str(table_id)

        self.sender = TableEventSender(self)
        self.lock = lock.Semaphore()

        self.ready_time = 0

        self.table_event_queue = Queue()
        gevent.spawn_later(1,self.real_send_event)

    def is_ready(self):
        return int(time.time()) > self.ready_time

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
        return self.game != None and self.game.is_started() and uid in self.game.gamblers


    def is_game_started(self):
        return self.game != None and self.game.is_started()

    def remove_player(self,uid, is_kicked = False):
        if uid == self.dealer:
            self.dealer = -1
    	
        player = self.get_player(uid)
        if player == None:
            return False

        self.players.pop(uid,None)

        if self.game != None:
            self.game.leave_game(uid)

        self.redis.hdel(self.table_key,uid)
        self.redis.hdel(self.manager.room_key,uid)
        if not is_kicked:
            self.sender.send_player_leave(player)
        return len(self.players) == 0 

    def kick_player(self,kicker,uid):
        player = self.get_player(uid)

        self.remove_player(uid,is_kicked = True)
        self.sender.send_player_kicked(kicker,player)

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
        
    
    def restart_game(self):
        config = TABLE_GAME_CONFIG[self.table_type]
        for player in self.players.values():
            if player.idle_time < 0:
                player.idle_time = time.time()

        for player in self.players.values():
            player.reload_user_gf()

        self.game = GoldFlower(self,config[2],config[3],config[4],config[5],config[6],config[7])
        gevent.spawn_later(3,self.kick_invalid_players())


    def kick_invalid_players(self):
        config = TABLE_GAME_CONFIG[self.table_type]
        for player in self.players.values():
            if not player.is_connected:
                self.remove_player(player.uid)
                continue
            """
            gold = player.get_gold()
            if config[1] >= 0 and gold > config[1]:
                self.kick_player(-1,player.uid)
                continue
            """

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

    def get_proto_struct(self,uid,pb_table = None):
        if pb_table == None:
            pb_table = pb2.Table()

        pb_table.table_type = self.table_type

        for player in self.players.values():
            player.get_brief_proto_struct(pb_table.players.add())

        if self.game != None:
            self.game.get_proto_struct(uid,pb_table)
        return pb_table    

class TableManager:
    def __init__(self,service):
        self.service = service
        if service != None:
            self.redis = service.server.redis
        else:
            self.redis = None

        self.tables = {}
        self.room_id = service.serviceId

        self.session = Session()
        self.dal = DataAccess(self.redis)

        if self.redis != None:
            self.room_key = "room_users_" + str(self.room_id)
            self.redis.delete(self.room_key)
            self.redis.hset(self.room_key,"info","")

            keys = self.redis.keys("table_" + str(service.serviceId) + "*")
            for k in keys:
                self.redis.delete(k)
        self.lock = lock.Semaphore()
        gevent.spawn_later(5,self.scan_idle_player)


    def scan_idle_player(self):
        while True:
            now = time.time()
            for _,t in self.tables.items():
                t.lock.acquire()
                try :
                    for _,player in t.players.items():
                        if player.idle_time > 0 and now - player.idle_time > 180:
                            t.kick_player(-2,player.uid)
                            logging.info("Player %d/on table %d is idle too long, so kick it out",player.uid,t.id)
                finally:
                    t.lock.release()

            gevent.sleep(30)


    def get_table(self,table_id):
        return self.tables.get(table_id)

    def new_table(self,table_type):
        table_id = self.redis.incr("table_id")
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


    def sit_table(self,target_table_id,uid,access_service,not_table_ids,table_type):
        user = self.dal.get_user(uid)
        if user == None:
            return RESULT_FAILED_INVALID_USER,None

        if table_type < 0:
            table_type = self.find_suitable_table_type(user.gold)
            if table_type < 0:
                return RESULT_FAILED_LESS_GOLD,None
        table = None

        old_table = self.get_player_table(uid)
        if target_table_id < 0:
            if old_table != None:
                self.reconnect_table_player(old_table,uid,user,access_service)
                return 0, old_table

            all_tables = [t for t in self.tables.values() \
                          if t.id not in not_table_ids and t.table_type == table_type and not t.is_full() and t.is_ready()]
            all_tables.sort(cmp=self.sort_table,reverse = True)
            for t in all_tables:
                if t.is_gambler(uid):
                    # if user is gambler of this table,it means that he quit this game before ,so didnot arrange this table
                    continue
                table = t
                break
            if table == None:
                table = self.new_table(table_type)
        else:
            if old_table != None and target_table_id == old_table.id:
                #self.reconnect_table_player(old_table,uid,user,access_service)
                return 0,old_table

            self.remove_table_player(old_table,uid)
            table = self.get_table(target_table_id)
            if table == None or table.is_full():
                return RESULT_FAILED_INVALID_TABLE,None

        table.lock.acquire()
        try :
            check_result = self.check_table_type(table.table_type,user.gold)
            if check_result < 0:
                return check_result,None
                
            player = table.add_player(uid,user,access_service)
            if player == None:
                return RESULT_FAILED_TABLE_IS_FULL,None
        finally:
            table.lock.release()
        return 0,table
    

if __name__ == '__main__':
    
    manager = TableManager(None)

    manager.sit_table(1, 1, [], TABLE_L)
    manager.sit_table(2, 1, [], TABLE_L)
    table = manager.sit_table(3, 1, [], TABLE_L)

    print(table)

    table.game.set_ready(1)
    table.game.set_ready(2)
    table.game.set_ready(3)

    gevent.sleep(1)

