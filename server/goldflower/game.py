#coding: utf-8
import gevent
from gevent import lock

from gevent import monkey;monkey.patch_all()
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
from proto import struct_pb2 as pb2
from db.connect import *

from db.user_goldflower import *
from db.goldflower import *
from db.goldflower_gambler import *
from db.lucky import *
from db.lucky_config import *
from db.account_book import *

from util.commonutil import *

from goldflower.gameconf import *
from goldflower.eventsender import *

from task.dailytask import *
from task.achievementtask import *
from rank.makemoneytop import *

from helper import dbhelper
from config import broadcast
from hall.rewardbox import reward_box

DEFAULT_LUCKY_CONFIG_ID = 0

DEFAULT_LUCKY_CONFIG = """
[
[1,5,70,80,20,30],
[6,15,50,60,10,20],
[16,25,20,30,0,10],
[26,30,10,20,5,10],
[31,40,50,60,10,20],
[41,50,40,50,10,20],
[51,55,10,20,5,10],
[56,65,20,30,0,10],
[66,75,50,60,10,20],
[76,85,40,50,10,20],
[86,90,10,20,5,10],
[91,100,20,30,0,10],
[100,-1,30,40,0,0]
 ]
"""

NOT_CHARGE_LUCKY_CHANGES = [
    (3000000,5),(1000000,4),(300000,3),(100000,2),(0,1),
]

CHARGE_LUCKY_CHANGES = [
    (30000000,5),(10000000,4),(3000000,3),(600000,2),(0,1),
]


class Chip:
    def __init__(self,uid,gold):
        self.uid = uid
        self.gold = gold

    def get_proto_struct(self,pb_chip = None):
        if pb_chip == None:
            pb_chip = pb2.Chip()
        pb_chip.uid = self.uid
        pb_chip.gold = self.gold
        return pb_chip    

class Poker:
    def __init__(self,flower,value):
        self.flower = flower
        self.value = value   

    def __eq__(self,other):
        return self.flower == other.flower and self.value == other.value         

    def __repr__(self):
        return "%d-%d" % (self.flower,self.value,)

    def get_proto_struct(self,pb_poker = None):
        if pb_poker == None:
            pb_poker = pb2.Poker()
        pb_poker.flower = self.flower
        pb_poker.value = self.value
        return pb_poker

class PlayerPokers:
    @staticmethod
    def from_pokers_str(uid,pokers_str):
        poker_strs = pokers_str.split(",")
        pokers = []

        for poker_str in poker_strs:
            fv = poker_str.split("-")
            flower = int(fv[0])
            value = int(fv[1])
            pokers.append(Poker(flower,value))

        return PlayerPokers(uid,*pokers)


    def __init__(self,uid,poker1,poker2,poker3):
        self.uid = uid
        self.pokers = []
        self.pokers.append(poker1)
        self.pokers.append(poker2)
        self.pokers.append(poker3)
        self.pokers.sort(cmp = lambda x,y: cmp(x.value,y.value),reverse=True)

        if self.is_baozi():
            self.poker_type = P_BAOZI
        elif self.is_tonghuashun():
            self.poker_type = P_TONGHUASHUN
        elif self.is_tonghua():
            self.poker_type = P_TONGHUA
        elif self.is_shun():
            self.poker_type = P_SHUN
        elif self.is_dui():
            self.poker_type = P_DUI
        elif self.is_352():
            self.poker_type = P_352    
        else:
            self.poker_type = P_DAN

        self.poker_value = self.V()

    def to_pokers_str(self):
        pokers = self.pokers
        return "%d-%d,%d-%d,%d-%d" % (pokers[0].flower,pokers[0].value,pokers[1].flower,pokers[1].value,pokers[2].flower,pokers[2].value)

    def get_dui_value(self):
        if self.poker_type == P_DUI:
            if self.pokers[0].value == self.pokers[1].value:
                return self.pokers[0].value
            elif self.pokers[0].value == self.pokers[2].value:
                return self.pokers[0].value
            else:
                return self.pokers[1].value
        return -1

    def get_dan_value(self):
        values = (self.pokers[0].value,self.pokers[1].value,self.pokers[2].value,)
        if 1 in values:
            return 14
        else:
            return self.pokers[0].value
        """
        if self.poker_type == P_TONGHUASHUN \
                or self.poker_type == P_SHUN \
                    or self.poker_type == P_TONGHUA \
                        or self.poker_type == P_DAN:
            return self.pokers[0].value
        return -1
        """
    def __repr__(self):
        return "(%s,%s,%s)" % (str(self.pokers[0]),str(self.pokers[1]),str(self.pokers[2]),)

    def V(self):
        values = []
        for p in self.pokers:
            if p.value == 1:
                values.append(14)
            else:
                values.append(p.value)

        values.sort(reverse=True)
        values = tuple(values)

        if values == (14,3,2):
            return "030201"

        if not self.is_baozi() and self.is_dui():
            if values[0] != values[1]:
               values = (values[2],values[1],values[0],)
        return "%02d%02d%02d" % values

    def is_baozi(self):
        return self.pokers[0].value == self.pokers[1].value and self.pokers[1].value == self.pokers[2].value

    def is_tonghua(self):
        return self.pokers[0].flower == self.pokers[1].flower and self.pokers[1].flower == self.pokers[2].flower
        
    def is_shun(self):
        values = (self.pokers[0].value,self.pokers[1].value,self.pokers[2].value,)
        if values == (13,12,1):
            return True
        if values[2] - values[1] == -1 and values[1] - values[0] == -1:
            return True
        return False

    def is_tonghuashun(self):
        return self.is_tonghua() and self.is_shun()

    def is_dui(self):
        return self.pokers[0].value == self.pokers[1].value  \
                or self.pokers[1].value == self.pokers[2].value
 
    def is_dan(self):
        return self.pokers[0].value != self.pokers[1].value \
                and self.pokers[1].value != self.pokers[2].value 

    def is_352(self):
        values = (self.pokers[0].value,self.pokers[1].value,self.pokers[2].value,)
        return values == (5,3,2,)

    def compare(self,other):
        if self.poker_type == other.poker_type and self.poker_value == other.poker_value:
            return -1

        if self.poker_type == P_352 and other.poker_type == P_BAOZI:
            return 1

        if self.poker_type == P_BAOZI and other.poker_type == P_352:
            return -1   

        if self.poker_type == other.poker_type:
            return cmp(self.poker_value, other.poker_value)
        return cmp(self.poker_type, other.poker_type)

    def sort_poker(self,x,y):
        xv = x.value
        yv = y.value
        if xv == 1:
            xv = 14
        if yv == 1:
            yv = 14
        return cmp(xv,yv)

    def get_proto_struct(self,pb_pokers = None):
        if pb_pokers == None:
            pb_pokers = pb2.PlayerPokers()

        pokers = []
        pokers.extend(self.pokers)
        pokers.sort(cmp = self.sort_poker,reverse=True)

        if (pokers[0].value,pokers[1].value,pokers[2].value,) == (1,3,2):
            pokers = [pokers[1],pokers[2],pokers[0]]

        pb_pokers.uid = self.uid
        for poker in pokers:
            poker.get_proto_struct(pb_pokers.pokers.add())
        return pb_pokers

class Gambler:
    def __init__(self,game,player):
        self.game = game
        self.player = player
        self.seat = self.player.seat
        self.uid = player.uid
        self.is_fail = False
        self.is_seen = False
        self.is_given_up = False
        self.is_dealer = False
        self.is_show_hand = False
        self.bet_gold = 0
        self.action_gold = 0
        self.pokers = None

    def turn_timeout(self,turn_count):
        self.game.table.lock.acquire()
        try :
            if self.game.start_time > 0 and self.game.round.current_gambler.uid == self.uid \
                    and self.game.round.count == turn_count:
                self.game.bet(self.player.uid,GIVE_UP,0,0,True)
        finally:
            self.game.table.lock.release()

    def is_advanced(self,other):
        seats = range(self.game.dealer.seat,MAX_TABLE_PLAYER)
        seats.extend(0,self.game.dealer.seat)
        for i in seats:
            if i == self.player.seat:
                return True
        return False        

    def stake(self,gold):
        if not self.player.has_gold(gold):
            return RESULT_FAILED_LESS_GOLD
        self.action_gold = gold
        self.bet_gold += gold
        chip = Chip(self.uid, gold)
        self.game.chips.append(chip)
        self.game.total_gold += gold
        session = get_context("session",None)
        self.player.modify_gold(session,-gold)
        
        DailyTaskManager(self.game.table.redis).bet_gold(self.uid,gold)
        
        return 0

    def has_gold(self,gold):
        return self.player.has_gold(gold)    

    def get_gold(self):
        return self.player.get_gold()

    def compare_pokers(self,other):
        p_result = self.pokers.compare(other.pokers)
        if p_result == 0:
            return -1 if self.is_advanced(other) else 1
        else:
            return p_result

    def __repr__(self):
        return " Gam:(" + str(self.player.uid) +  ":" + str(self.pokers) + ":"  +  str(self.bet_gold) \
                 + ":" + str(self.player.get_gold()) + ")"
 
    def get_proto_struct(self,uid,pb_gambler):
        if pb_gambler == None:
            pb_gambler = pb2.Gambler()

        pb_gambler.uid = self.player.uid
        
        pb_gambler.seat = self.seat
        pb_gambler.gold = self.player.get_gold()

        pb_gambler.bet_gold = self.bet_gold
        pb_gambler.is_dealer = self.is_dealer
        pb_gambler.is_seen = self.is_seen
        pb_gambler.is_given_up = self.is_given_up
        pb_gambler.is_show_hand = self.is_show_hand
        pb_gambler.is_fail = self.is_fail

        if uid == self.uid and self.is_seen:
            self.pokers.get_proto_struct(pb_gambler.pokers)

        return pb_gambler

class GameRound:
    def __init__(self,table,game):
        self.table = table
        self.game = game
        self.count = 0
        self.turn_uids = []
        self.current_gambler = None
        self.turn_start_time = 0
        self.min_gold = self.game.required_gold
        self.is_show_hand = False
        self.show_hand_gold = 0


    def start_game(self):
        self.current_gambler = self.next_notlose_gambler(self.game.dealer.uid)
        self.game.start_time = int(time.time())

        for gambler in self.game.gamblers.values():
            if not gambler.is_fail:
                gambler.stake(self.game.required_gold)
            gambler.player.idle_time = -1

        self.game.sender.send_game_started()
        # 为了给客户端3秒的发牌动画时间
        gevent.spawn_later(3,self.start_first_turn)

    def start_first_turn(self):
        self.turn_start_time = int(time.time())
        self.game.sender.send_current_turn(self.count,self.current_gambler)
        gevent.spawn_later(self.game.round_seconds,self.current_gambler.turn_timeout,self.count)

    def finish_turn(self,uid,delay = 0):
        self.turn_uids.append(self.current_gambler.uid)
        gambler = self.next_notlose_gambler(self.current_gambler.uid)
        if gambler != None  and gambler.uid in self.turn_uids:
            self.finish_round()

        if self.game.check_result():
            return

        self.current_gambler = self.next_notlose_gambler(self.current_gambler.uid)
        if delay > 0:
            gevent.spawn_later(delay,self.start_next_turn_with_lock)
        else:
            self.start_next_turn()

    def start_next_turn_with_lock(self):
        self.game.table.lock.acquire()
        try :
            self.start_next_turn()
        finally:
            self.game.table.lock.release()

    def start_next_turn(self):
        if self.game.start_time < 0:
            return
        self.turn_start_time = int(time.time())
        self.game.sender.send_current_turn(self.count,self.current_gambler)
        if self.count <= self.game.max_round:
            gevent.spawn_later(self.game.round_seconds,self.current_gambler.turn_timeout,self.count)
        else:
            not_fails = [x for x in self.game.gamblers.values() if x.is_fail == False and x.uid != self.current_gambler.uid]
            any_one = random.choice(not_fails)
            result = self.game.bet(self.current_gambler.uid,COMPARE,0,any_one.uid,True)
            if result < 0:
                self.game.bet(self.current_gambler.uid,GIVE_UP,0,0,True)

    def finish_round(self):
        self.count += 1
        self.turn_uids = []

    def current_turn_no(self):
        return len(self.turn_uids)    

    def next_notlose_gambler(self,uid):
        next_gambler = None
        tmp_uid = uid
        while next_gambler == None:
            g = self.next_gambler(tmp_uid)
            if g.uid == uid :
                break
            if not g.is_fail:
                return g
            tmp_uid = g.uid
        return next_gambler

    def next_gambler(self,uid):
        gambler = self.game.gamblers[uid]

        first_gambler = min(self.game.gamblers.values(),key = lambda x:x.seat)
        next_gamblers = filter(lambda x: x.seat > gambler.seat,self.game.gamblers.values())
        if len(next_gamblers) == 0:
            return first_gambler
        else:
            return min(next_gamblers,key = lambda x:x.seat)

    def get_proto_struct(self,pb_round = None):
        if pb_round == None:
            pb_round = pb2.GameRound()

        pb_round.round = self.count
        if self.current_gambler != None:
            pb_round.current_gambler = self.current_gambler.uid
        else:
            pb_round.current_gambler = -1
        pb_round.turn_start_time = self.turn_start_time
        now = int(time.time())
        pb_round.turn_remain_time = self.game.round_seconds - (now - self.turn_start_time)
        return pb_round    


class GoldFlower:
    def __init__(self,table,required_gold,max_gold,required_round,max_round,fee_rate,round_seconds):
        self.required_gold = required_gold
        self.max_gold = max_gold
        self.required_round = required_round
        self.max_round = max_round
        
        self.fee_rate = fee_rate
        self.round_seconds = round_seconds

        self.table = table

        self.gamblers = {}
        self.chips = []
        self.round = GameRound(self.table, self)
        self.total_gold = 0
        self.winner = None
        self.game_id = -1
        self.dealer = None
        self.start_time = -1

        self.sender = GameEventSender(table, self)
        self.process_started = False


        self.last_action = None

    def is_gambler(self,uid):
        return uid in self.gamblers

    def is_started(self):
        return self.start_time > 0

    def set_ready(self,uid):
        if self.start_time > 0:
            return RESULT_FAILED_ALREADY_START

        if uid in self.gamblers:
            return RESULT_FAILED_ALREADY_READY

        player = self.table.get_player(uid)
        if player == None:
            raise Exception("player is not exist")

        table_config = TABLE_GAME_CONFIG[self.table.table_type]
        if table_config[0] > 0:
            if not player.has_gold(table_config[0]):
                return RESULT_FAILED_LESS_GOLD

        if table_config[1] > 0:
            if player.get_gold() > table_config[1]:
                return RESULT_FAILED_MORE_GOLD

        gambler = Gambler(self,player)

        self.gamblers[uid] = gambler
        self.sender.send_player_ready(uid) 

        if len(self.gamblers) >= 2 and not self.process_started:
            self.process_started = True
            gevent.spawn(self.start_game)  
        return 0

    def leave_game(self,uid):
        if self.start_time < 0:
            self.gamblers.pop(uid,None)
            return True
        else:
            gambler = self.gamblers.get(uid)
            if gambler == None:
                return
            if not gambler.is_fail:
                self.bet(uid,GIVE_UP,0,0)
        return True

    # check game is finished or not
    def check_result(self):
        is_finished = False
        try :
            if self.winner != None:
                is_finished = True
            else:
                not_fails = [x for x in self.gamblers.values() if x.is_fail == False]
                if len(not_fails) == 1:
                    is_finished = True
                    self.handle_result(not_fails[0])
                elif len(not_fails) == 2 and not_fails[0].is_show_hand and not_fails[1].is_show_hand:
                    is_finished = True
                    if not_fails[0].compare_pokers(not_fails[1]) > 0:
                        self.handle_result(not_fails[0])
                    else:
                        self.handle_result(not_fails[1])
        finally:
            if is_finished:
                if self.last_action in (COMPARE,SHOW_HAND):
                    self.table.ready_time = int(time.time()) + 8
                else:
                    self.table.ready_time = int(time.time()) + 5
                self.table.restart_game()


        return is_finished

    # if game is finished ,so handle it such as calc money and send broadcast and so on
    def handle_result(self,winner = None):
        self.winner = winner
        # the winner will be next game dealer
        self.table.dealer = winner.uid

        session = get_context("session")
        if session == None:
            session = Session()
            try :
                session.begin()
                self.calc_result(session)
                session.commit()
            except:
                traceback.print_exc()
                session.rollback()
            finally:
                session.close()
                session = None
        else:
            self.calc_result(session)

        self.start_time = -1
        self.gamblers = {}

        # 删除牌的信息
        self.table.redis.hdel("pokers",self.table.id)

    def calc_result(self,session):
        fee_gold = int((self.total_gold - self.winner.bet_gold) * self.fee_rate)
        win_gold = self.total_gold - fee_gold - self.winner.bet_gold

        lucky_type = 0
        total_lucky_gold = 0
        lucky_gold = 0

        if self.winner.pokers.is_tonghuashun():
            lucky_gold = 1000
            lucky_type = 1

        if self.winner.pokers.is_baozi():
            lucky_gold = 2000
            lucky_type = 2

        if lucky_gold != 0:
            for gambler in self.gamblers.values():
                if gambler.uid != self.winner.uid and gambler.uid in self.table.players and gambler.player.is_connected:
                    gambler_gold = gambler.player.get_gold()
                    if gambler_gold > lucky_gold:
                        gambler.player.modify_gold(session,-lucky_gold)
                        total_lucky_gold += lucky_gold
                    else:
                        gambler.player.modify_gold(session,-gambler_gold)
                        total_lucky_gold += gambler_gold


        self.winner.player.modify_gold(session,self.total_gold + total_lucky_gold - fee_gold)

        self.record_and_broadcast(session,self.winner,win_gold,fee_gold,total_lucky_gold,lucky_gold)
        self.sender.send_game_over_event(self.winner.uid,self.total_gold + total_lucky_gold,fee_gold,lucky_type,total_lucky_gold,lucky_gold)


        if self.table.table_type == TABLE_L or self.table.table_type == TABLE_M:
            # send reward box
            manager = self.table.manager
            service = manager.service
            redis = self.table.redis
            gevent.spawn_later(7, reward_box, service,redis, self.winner.uid)

    def record_and_broadcast(self,session,winner,win_gold,fee_gold,total_lucky_gold,lucky_gold):
        row_game = TGoldFlower()
        row_game.type = self.table.table_type
        row_game.winner = winner.uid
        row_game.countof_gamblers = len(self.gamblers)
        row_game.gold = win_gold
        row_game.fee = fee_gold
        row_game.create_time = datetime.now()

        session.add(row_game)
        session.flush()

        for gambler in self.gamblers.values():
            row_gambler = TGoldFlowerGambler()
            row_gambler.game_id = row_game.id
            row_gambler.uid = gambler.uid
            row_gambler.type = self.table.table_type
            row_gambler.bet_gold = gambler.bet_gold

            row_gambler.is_winner = 1 if row_gambler.uid == winner.uid else 0
            row_gambler.win_gold = win_gold if row_gambler.is_winner == 1 else -gambler.bet_gold
            row_gambler.fee_gold = fee_gold if row_gambler.is_winner == 1 else 0

            row_gambler.create_time = datetime.now()
            row_gambler.pokers = str(gambler.pokers)
            session.add(row_gambler)

            user_gf = session.query(TUserGoldFlower).filter(TUserGoldFlower.id == row_gambler.uid).first()

            if user_gf.best == None or user_gf.best.strip() == "":
                user_gf.best = gambler.pokers.to_pokers_str()
            else:
                best_pokers = PlayerPokers.from_pokers_str(user_gf,user_gf.best)
                if gambler.pokers.compare(best_pokers) > 0:
                    user_gf.best = gambler.pokers.to_pokers_str()

            user_gf.total_games += 1
            if user_gf.id == winner.uid :
                user_gf.win_games += 1
                MakeMoneyTop.save_rank(session, user_gf.id, win_gold)

            if self.table.table_type == TABLE_L:
                user_gf.exp += 2 if user_gf.id == winner.uid else 1
            elif self.table.table_type == TABLE_M:
                user_gf.exp += 4 if user_gf.id == winner.uid else 2
            elif self.table.table_type == TABLE_H:
                user_gf.exp += 8 if user_gf.id == winner.uid else 4
            else:
                user_gf.exp += 16 if user_gf.id == winner.uid else 8
            
            achievement = GameAchievement(session,user_gf.id, self.table.redis)
            achievement.finish_game(user_gf,row_gambler.win_gold, self.table.redis)

            if gambler.pokers.is_baozi():
                achievement.finish_baozi_pokers()
            if gambler.pokers.is_352() and gambler.uid == winner.uid:
                for g in self.gamblers.values():
                    if g.uid != winner.uid and g.pokers.is_baozi():
                        achievement.finish_235_win_baozi()
                        break

        dbhelper.recycle_gold(session,game_id=row_game.id,gold=fee_gold)

        DailyTaskManager(self.table.redis).finish_game(winner,[gambler.uid for gambler in self.gamblers.values()])
        broadcast.send_win_game(self.table.redis,winner.uid,winner.player.nick,self.table.table_type, \
                                    self.total_gold + total_lucky_gold, winner.player.user.vip_exp)
        broadcast.send_good_pokers(self.table.redis,winner.uid,winner.player.nick,self.table.table_type, \
                                        winner.pokers, winner.player.user.vip_exp)

    def bet(self,uid,action,gold,other,by_system = False):
        result = self.real_bet(uid,action,gold,other,by_system)
        if result == 0:
            self.last_action = action
        return result

    def real_bet(self,uid,action,gold,other,by_system = False):
        if self.start_time < 0:
            return RESULT_FAILED_GAME_NOT_STARTED

        if not by_system and self.round.count > self.max_round:
            return RESULT_FAILED_INVALID_TURN

        if action == GIVE_UP:
            result = self.bet_giveup(uid)
            if self.round.current_gambler.uid == uid:
                self.round.finish_turn(uid)
            else:  
                self.check_result()

            return result
            
        if self.round.current_gambler.uid != uid or self.round.current_gambler.is_fail:
            return RESULT_FAILED_INVALID_TURN

        result = False
        if action == FOLLOW:
            result = self.bet_follow(uid)
        elif action == ADD:
            result = self.bet_add(uid,gold)
        elif action == SHOW_HAND:
            result = self.bet_show_hand(uid)
        elif action == COMPARE:
            result = self.bet_compare(uid,other)
        
        if result < 0:
            return result
        if action == COMPARE :
            self.round.finish_turn(uid,DELAY_FOR_COMPARE)
        elif action == SHOW_HAND:
            self.round.finish_turn(uid,DELAY_FOR_SHOW_HAND)
        else:
            self.round.finish_turn(uid)
        return result

    def bet_follow(self,uid):
        if self.round.is_show_hand:
            return RESULT_FAILED_SHOW_HAND
        need_gold = 2 * self.round.min_gold if self.round.current_gambler.is_seen else self.round.min_gold
        current_gambler = self.round.current_gambler
        result = current_gambler.stake(need_gold)
        if result < 0:
            return result

        self.sender.send_bet_follow(current_gambler,uid,need_gold)
        return 0

    def bet_add(self,uid,gold):
        if self.round.is_show_hand:
            return RESULT_FAILED_SHOW_HAND
        need_gold = 2 * self.round.min_gold if self.round.current_gambler.is_seen else self.round.min_gold
        max_gold = 2 * self.max_gold if self.round.current_gambler.is_seen else self.max_gold

        if gold < need_gold or gold > max_gold:
            return RESULT_FAILED_INVALID_GOLD
        current_gambler = self.round.current_gambler
        result = current_gambler.stake(gold)
        if result < 0:
            return result

        min_gold = gold / 2 if self.round.current_gambler.is_seen else gold
        if self.round.min_gold < min_gold:
            self.round.min_gold = min_gold
            self.sender.send_bet_add(current_gambler,uid,gold)
        else:
            self.sender.send_bet_follow(current_gambler,uid,gold)
        return 0

    def bet_compare(self,uid,other):
        if self.round.count < self.required_round:
            return RESULT_FAILED_INVALID_ROUND

        if self.round.is_show_hand:
            return RESULT_FAILED_SHOW_HAND

        other_gambler = self.gamblers.get(other)
        if other_gambler.is_fail:
            return RESULT_FAILED_INVALID_GAMBLER

        current_gambler = self.round.current_gambler
        need_gold = 2 * self.round.min_gold if current_gambler.is_seen else self.round.min_gold

        result = current_gambler.stake(need_gold)
        if result < 0:
            return result

        winner = -1
        loser = -1
        if current_gambler.compare_pokers(other_gambler) > 0:
            other_gambler.is_fail = True
            loser = other_gambler.uid
            winner = current_gambler.uid
        else:
            current_gambler.is_fail = True
            loser = current_gambler.uid
            winner = other_gambler.uid

        self.sender.send_bet_compare(current_gambler,uid,other,need_gold,winner)

        if self.table.table_type == TABLE_L or self.table.table_type == TABLE_M:
            # send reward box
            manager = self.table.manager
            service = manager.service
            redis = self.table.redis
            gevent.spawn_later(5, reward_box, service,redis, loser)
        return 0

    def bet_giveup(self,uid):
        gambler = self.gamblers.get(uid)
        if gambler == None:
            raise Exception("it should not happen")

        if gambler.is_fail:
            return RESULT_FAILED_INVALID_GAMBLER

        not_fails = [x  for x in self.gamblers.values() if not x.is_fail]
        if len(not_fails) == 1:
            return RESULT_FAILED_MORE_GAMBLERS
	
        gambler.is_fail = True
        gambler.is_given_up = True
        self.sender.send_bet_give_up(uid)
        return 0

    def bet_show_hand(self,uid):
        not_fails = [x  for x in self.gamblers.values() if not x.is_fail and x.uid != self.round.current_gambler.uid]
        if len(not_fails) != 1:
            return RESULT_FAILED_MORE_GAMBLERS

        if (not not_fails[0].is_show_hand) and not_fails[0].get_gold() == 0:
            return RESULT_FAILED_INVALID_SHOW_HAND


        if self.round.count == self.max_round and self.round.current_turn_no() != 0:
            return RESULT_FAILED_INVALID_ROUND

        current_gambler = self.round.current_gambler
        other = not_fails[0]

        if not self.round.is_show_hand:

            my_gold = current_gambler.get_gold()
            other_gold = other.get_gold()

            my_gold = min(other_gold,my_gold)
            if my_gold == 0:
                return RESULT_FAILED_LESS_GOLD

        else:
            my_gold = current_gambler.get_gold()
            my_gold = min(self.round.show_hand_gold,my_gold)
            if my_gold == 0:
                return RESULT_FAILED_LESS_GOLD

        result = current_gambler.stake(my_gold)
        if result < 0:
            return result

        current_gambler.is_show_hand = True
        self.round.is_show_hand = True
        self.round.show_hand_gold = my_gold
        
        DailyTaskManager(self.table.redis).bet_show_hand(uid)

        winner = -1
        not_fails = [x for x in self.gamblers.values() if x.is_fail == False]
        if len(not_fails) == 2 and not_fails[0].is_show_hand and not_fails[1].is_show_hand:
            if not_fails[0].compare_pokers(not_fails[1]) > 0:
                winner = not_fails[0].uid
            else:
                winner = not_fails[1].uid
        
        self.sender.send_show_hand(current_gambler,uid,my_gold,winner)
        return 0

    def see_poker(self,uid):
        gambler = self.gamblers.get(uid)
        if self.round.count == 0 and uid == self.round.next_notlose_gambler(self.dealer.uid).uid \
                and uid == self.round.current_gambler:
            return None

        gambler.is_seen = True 
        self.sender.send_see_poker(uid)   
        return gambler.pokers

    def update_lucky_games(self,uids):
        session = Session()
        try:
            session.begin()
            for uid in uids:
                row_lucky = session.query(TLucky).filter(TLucky.uid == uid).first()
                if row_lucky == None:
                    row_lucky = TLucky()
                    row_lucky.uid = uid
                    row_lucky.lucky = 50
                    row_lucky.games = 1
                    row_lucky.config_id = DEFAULT_LUCKY_CONFIG_ID # 初始化
                    session.add(row_lucky)
                else:
                    row_lucky.games += 1
            session.commit()
        except:
            traceback.print_exc()
            session.rollback()
        finally:
            session.close()
            session = None

    def get_gambler_luckys(self,uids):
        session = Session()
        luckys = {}
        try:
            session.begin()
            for uid in uids:
                row = session.query(TLucky,TLuckyConfig).outerjoin(TLuckyConfig,TLucky.config_id == TLuckyConfig.id).filter(TLucky.uid == uid).first()
                if row == None:
                    row_lucky = TLucky()
                    row_lucky.uid = uid
                    row_lucky.lucky = 50
                    row_lucky.games = 1
                    row_lucky.config_id = DEFAULT_LUCKY_CONFIG_ID
                    session.add(row_lucky)
                    lucky_config_value = DEFAULT_LUCKY_CONFIG
                else:
                    row_lucky = row[0]
                    row_lucky.games += 1
                    if row[1] == None:
                        lucky_config_value = DEFAULT_LUCKY_CONFIG
                    else:
                        lucky_config_value = str(row[1].value)

                if row_lucky.config_id < 10000:
                    player = self.table.get_player(uid)
                    gold = player.user.gold
                    is_charge = player.user.is_charge != None and player.user.is_charge > 0
                    for i in xrange(1):
                        total_games = player.user_gf.total_games
                        if is_charge:
                            lst = CHARGE_LUCKY_CHANGES
                            if total_games <= 100 and gold <= 1000000:
                                break

                        else:
                            lst = NOT_CHARGE_LUCKY_CHANGES
                            if total_games <= 60 and gold <= 600000:
                                break

                        for k in lst:
                            if gold >= k[0]:
                                row_lucky.config_id = k[1]
                                break

                lucky_config = json.loads(lucky_config_value)

                for item in lucky_config:
                    if item[1] >= row_lucky.games >= item[0]:
                        var = random.randint(item[4],item[5])
                        if var > row_lucky.lucky:
                            var = row_lucky.lucky
                        row_lucky.lucky -= var
                        luckys[uid] = random.randint(item[2],item[3]) + var
                        break
                    if item[1] < 0:
                        row_lucky.games = 0
                        var = random.randint(item[4],item[5])
                        if var > row_lucky.lucky:
                            var = row_lucky.lucky
                        row_lucky.lucky -= var
                        row_lucky.lucky += 50
                        luckys[uid] = random.randint(item[2],item[3]) + var
                        break

            session.commit()
        except:
            traceback.print_exc()
            session.rollback()
        finally:
            session.close()
            session = None

        return luckys

    def deal(self):
        if self.table.deal_counter == 0:
            self.table.deal_trigger = random.randint(2,5)
        self.table.deal_counter += 1

        best_uid = -1
        data = []

        if self.table.deal_counter >= self.table.deal_trigger:
            self.table.deal_trigger = 0
            self.table.deal_counter = 0

            countof_gamblers = len(self.gamblers)
            r = random.randint(0,100)
            if countof_gamblers == 2:
                if r <= 10:
                    better,best = 4,2
                else:
                    better,best = 5,2
            elif countof_gamblers == 3:
                if r <= 10:
                    better,best = 6,2
                elif r <= 30:
                    better,best = 4,2
                else:
                    better,best = 5,2
            elif countof_gamblers == 4:
                if r <= 10:
                    better,best = 7,4
                elif r <= 30:
                    better,best = 6,3
                elif r <= 50:
                    better,best = 4,2
                else:
                    better,best = 5,2
            elif countof_gamblers == 5:
                if r <= 10:
                    better,best = 6,4
                elif r <= 30:
                    better,best = 7,4
                elif r <= 50:
                    better,best = 6,3
                elif r <= 70:
                    better,best = 4,2
                else:
                    better,best = 5,2

            choice_pokers = self.get_dealed_pokers(len(self.gamblers),better,best)
            choice_pokers.sort(cmp=lambda x,y:x.compare(y),reverse=True)

            luckys = self.get_gambler_luckys(self.gamblers.keys())
            total = sum([luckys[uid] for uid in luckys],0)
            rate = random.randint(0,total)
            lucky = 0
            for idx,uid in enumerate(self.gamblers.keys()):
                lucky += luckys[uid]
                if rate <= lucky:
                    best_uid = uid
                    break

            player_pokers = choice_pokers[0]
            player_pokers.uid = best_uid
            self.gamblers[best_uid].pokers = player_pokers
            d = {}
            d["uid"] = uid
            d["p1"] = str(player_pokers.pokers[0])
            d["p2"] = str(player_pokers.pokers[1])
            d["p3"] = str(player_pokers.pokers[2])
            data.append(d)
            choice_pokers.pop(0)
        else:
            self.update_lucky_games(self.gamblers.keys())
            choice_pokers = self.get_dealed_pokers(len(self.gamblers),0,0)

        random.shuffle(choice_pokers)

        for _,uid in enumerate(self.gamblers.keys()):
            if uid == best_uid:
                continue
            player_pokers = choice_pokers.pop(0)
            player_pokers.uid = uid
            self.gamblers[uid].pokers = player_pokers
            d = {}
            d["uid"] = uid
            d["p1"] = str(player_pokers.pokers[0])
            d["p2"] = str(player_pokers.pokers[1])
            d["p3"] = str(player_pokers.pokers[2])
            data.append(d)

        json_data = json.dumps(data)
        self.table.redis.hset("pokers",self.table.id,json_data)


    def get_dealed_pokers(self,count_pokers,better_pokers,best_pokers):
        pokers = []
        for flower in xrange(1,5):
            for value in xrange(1,14):
                pokers.append(Poker(flower,value))

        all_pokers = []
        while len(pokers) >= 3:
            poker1 = random.choice(pokers)
            pokers.remove(poker1)
            poker2 = random.choice(pokers)
            pokers.remove(poker2)
            poker3 = random.choice(pokers)
            pokers.remove(poker3)
            p = PlayerPokers(-1,poker1, poker2, poker3)
            all_pokers.append(p)

        all_pokers.sort(cmp=lambda x,y:x.compare(y),reverse=True)
        choice_pokers = []

        if better_pokers != 0:
            for x in xrange(best_pokers):
                idx = random.randint(0,better_pokers - x)
                choice_pokers.append(all_pokers[idx])
                all_pokers.pop(idx)

        if count_pokers != best_pokers:
            for _ in xrange(count_pokers - best_pokers):
                idx = random.randint(0,len(all_pokers) - 1)
                choice_pokers.append(all_pokers[idx])
                all_pokers.pop(idx)

        return choice_pokers

    def deal_better(self):
        pokers = []
        for flower in xrange(1,5):
            for value in xrange(1,14):
                pokers.append(Poker(flower,value))

        all_pokers = []
        while len(pokers) >= 3:
            poker1 = random.choice(pokers)
            pokers.remove(poker1)
            poker2 = random.choice(pokers)
            pokers.remove(poker2)
            poker3 = random.choice(pokers)
            pokers.remove(poker3)
            p = PlayerPokers(-1,poker1, poker2, poker3)
            all_pokers.append(p)

        all_pokers.sort(cmp=lambda x,y:x.compare(y),reverse=True)

        choice_pokers = []
        idx = random.randint(0,4)
        choice_pokers.append(all_pokers[idx])
        all_pokers.pop(idx)
        idx = random.randint(0,3)
        choice_pokers.append(all_pokers[idx])
        all_pokers.pop(idx)

        for _ in xrange(len(self.gamblers) - 2):
            idx = random.randint(0,len(all_pokers) - 1)
            choice_pokers.append(all_pokers[idx])
            all_pokers.pop(idx)

        random.shuffle(choice_pokers)

        data = []
        for idx,uid in enumerate(self.gamblers.keys()):
            player_pokers = choice_pokers[idx]
            player_pokers.uid = uid
            self.gamblers[uid].pokers = player_pokers
            d = {}
            d["uid"] = uid
            d["p1"] = str(player_pokers.pokers[0])
            d["p2"] = str(player_pokers.pokers[1])
            d["p3"] = str(player_pokers.pokers[2])
            data.append(d)

        json_data = json.dumps(data)
        #self.table.redis.hdel("pokers",self.table.id)
        self.table.redis.hset("pokers",self.table.id,json_data)


    def deal_good(self):
        pokers = []
        for flower in xrange(1,5):
            for value in xrange(1,14):
                pokers.append(Poker(flower,value))

        all_pokers = []
        while len(pokers) >= 3:
            poker1 = random.choice(pokers)
            pokers.remove(poker1)
            poker2 = random.choice(pokers)
            pokers.remove(poker2)
            poker3 = random.choice(pokers)
            pokers.remove(poker3)
            p = PlayerPokers(-1,poker1, poker2, poker3)
            all_pokers.append(p)

        all_pokers.sort(cmp=lambda x,y:x.compare(y),reverse=True)

        choice_pokers = []
        choice_pokers.append(all_pokers[0])
        choice_pokers.append(all_pokers[1])
        all_pokers.pop(0)
        all_pokers.pop(0)

        for _ in xrange(len(self.gamblers) - 2):
            idx = random.randint(0,len(all_pokers) - 1)
            choice_pokers.append(all_pokers[idx])
            all_pokers.pop(idx)

        random.shuffle(choice_pokers)

        data = []
        for idx,uid in enumerate(self.gamblers.keys()):
            player_pokers = choice_pokers[idx]
            player_pokers.uid = uid
            self.gamblers[uid].pokers = player_pokers
            d = {}
            d["uid"] = uid
            d["p1"] = str(player_pokers.pokers[0])
            d["p2"] = str(player_pokers.pokers[1])
            d["p3"] = str(player_pokers.pokers[2])
            data.append(d)

        json_data = json.dumps(data)
        #self.table.redis.hdel("pokers",self.table.id)
        self.table.redis.hset("pokers",self.table.id,json_data)

    def deal_random(self):
        pokers = []
        for flower in xrange(1,5):
            for value in xrange(1,14):
                pokers.append(Poker(flower,value))

        data = []

        for uid in self.gamblers.keys():
            d = {}
            poker1 = random.choice(pokers)
            pokers.remove(poker1)
            poker2 = random.choice(pokers)
            pokers.remove(poker2)
            poker3 = random.choice(pokers)
            pokers.remove(poker3)
            self.gamblers[uid].pokers = PlayerPokers(uid,poker1, poker2, poker3)
            d["uid"] = uid
            d["p1"] = str(poker1)
            d["p2"] = str(poker2)
            d["p3"] = str(poker3)
            data.append(d)

        json_data = json.dumps(data)
        #self.table.redis.hdel("pokers",self.table.id)
        self.table.redis.hset("pokers",self.table.id,json_data)

    def start_game(self):
        self.sender.send_game_ready(WAIT_SECONDS)
        
        for i in xrange(WAIT_SECONDS):
            self.table.lock.acquire()
            try :
                if len(self.gamblers) == self.table.countof_players() and len(self.gamblers) >= 2:
                    break
            finally:
                self.table.lock.release()
            gevent.sleep(1)
        
        self.table.lock.acquire()
        try :
            if len(self.gamblers) < 2:
                self.sender.send_game_cancel()
                self.process_started = False
                return
            if self.table.dealer > 0 and self.table.dealer in self.gamblers:
            	self.dealer = self.gamblers[self.table.dealer]
            else:
            	self.dealer = random.choice(self.gamblers.values())
            		
            self.dealer.is_dealer = True
            self.deal()
            self.round.start_game()
        finally:
            self.table.lock.release()


    def __repr__(self):
        s = "GoldFlower[" + str(self.total_gold) + ":"
        for gambler in self.gamblers.values():
            s += str(gambler) + "|"
        s += "]\n"
        return s


    def get_proto_struct(self,uid,pb_table = None):
        if pb_table == None:
            pb_table = pb2.Table()

        pb_table.id = self.table.id

        pb_game = pb_table.goldflower
        pb_game.start_time = self.start_time
        self.round.get_proto_struct(pb_game.round)
        for gambler in self.gamblers.values():
            gambler.get_proto_struct(uid,pb_game.gamblers.add())
        for chip in self.chips:
            chip.get_proto_struct(pb_game.chips.add())    
        pb_game.required_gold = self.required_gold
        pb_game.max_gold = self.max_gold
        pb_game.required_round = self.required_round
        pb_game.max_round = self.max_round
        pb_game.round_seconds = self.round_seconds
        return pb_table
if __name__ == '__main__':
    pass
