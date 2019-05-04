# -*- coding: utf-8 -*-
import random

__author__ = 'Administrator'

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import gevent
from gevent import lock
from gevent import monkey;monkey.patch_all()

import time
import math
import traceback
import logging
import collections
import itertools
import datetime

from proto import struct_pb2 as pb2
from proto.texas_pb2 import *
from message.resultdef import *
from util.commonutil import *
from db.connect import *
from db.texas import *
from db.texas_gambler import *
from db.texas_player import *
from db.rank_texas_top import *

from texasconf import *

from eventsender import GameEventSender

from sqlalchemy import and_

from helper.datehelper import microtime

class Gambler:
    def __init__(self, game, player):
        self.game = game
        if player == None:
            self.uid = -1
        else:
            self.player = player
            self.uid = player.uid

        self.pokers = []
        self.final_poker = None

        self.result = 0
        self.reward_result = 0
        self.win_gold = 0
        self.bet_win_gold = 0
        self.reward_gold = 0
        self.tax = 0

        self.action = WATCH

        self.bet_reward_gold = 0
        self.low_gold = 0
        self.add_bei_gold = 0

    def is_robot(self):
        return self.player.access_service == 5800

    def is_dealer(self):
        if self.uid == -1:
            return True
        return False

    def has_gold(self,gold):
        return self.player.has_gold(gold)

    def get_gold(self):
        return self.player.get_gold()

    def get_bet_gold(self):
        return self.low_gold + self.add_bei_gold + self.bet_reward_gold

    def do_add_bei(self, gold):
        self.action = ADD_BEI
        self.add_bei_gold = gold

        self.stake(gold)

    def do_join(self, gold, bet_reward_gold):
        self.action = BET
        self.low_gold = gold
        self.bet_reward_gold = bet_reward_gold

        self.stake(gold, bet_reward_gold)

    def do_watch(self):
        self.action = WATCH

        if self.player != None:
            self.player.incr_watch()

    def do_pass(self):
        self.action = PASS

    def do_giveup(self):
        self.action = GIVEUP

    def set_action(self, action):
        self.action = action

    def is_watch(self):
        return self.action == WATCH

    def is_giveup(self):
        return self.action == GIVEUP

    def is_bet(self):
        return self.action == BET

    def is_add_bei(self):
        return self.action == ADD_BEI

    def is_pass(self):
        return self.action == PASS

    def stake(self,gold, reward_gold = 0):
        if not self.player.has_gold(gold):
            return RESULT_FAILED_LESS_GOLD
        session = get_context("session",None)
        if session == None:
            session = Session()
            set_context("session",session)
        self.player.modify_gold(session,-(gold+reward_gold))

        return 0

    def calc_gold(self, compare_result, game):
        self.result = compare_result
        if compare_result == 1:
            lose_gold = int(self.low_gold + self.add_bei_gold)
            self.win_gold -= lose_gold

            if not self.is_robot():
                game.total_gold += lose_gold
        elif compare_result == 0:
            lose_gold = int(self.low_gold + self.bet_reward_gold)
            self.win_gold -= lose_gold
            if not self.is_robot():
                game.total_gold += lose_gold
        else:
            tax = int((self.low_gold + self.add_bei_gold) * TEXAS_TAX)
            win_gold = (self.low_gold + self.add_bei_gold) - tax
            self.win_gold += win_gold
            self.tax += tax
            self.bet_win_gold = win_gold
            if not self.is_robot():
                game.total_gold -= win_gold

    def calc_reward_gold(self, compare_result, game):
        rate = self.final_poker.get_reward_poker_rate()
        if rate > 0:
            self.reward_result = -1
            reward_gold = self.bet_reward_gold * rate
            tax = int(reward_gold * TEXAS_TAX)
            self.reward_gold += reward_gold - tax
            self.tax += tax

            self.win_gold += reward_gold - tax
            if not self.is_robot():
                game.total_gold -= reward_gold - tax
        else:
            self.reward_result = 1
            lose_gold = int(self.bet_reward_gold)
            self.win_gold -= lose_gold
            self.reward_gold -= lose_gold
            if not self.is_robot():
                game.total_gold += lose_gold

    def save_win_gold(self, session):
        result_gold = 0
        if self.result == -1:
            result_gold += self.bet_win_gold + self.low_gold + self.add_bei_gold
        if self.reward_result == -1:
            result_gold += self.reward_gold + self.bet_reward_gold

        if result_gold > 0:
            self.player.user.modify_gold(session, result_gold)

    def save_result(self, session, game_id):
        gambler = TTexasGambler()
        gambler.game_id = game_id
        gambler.uid = self.uid
        gambler.hand_pokers = str(self.pokers)
        gambler.final_pokers = str(self.final_poker.pokers) if self.final_poker != None else -1
        gambler.bet_gold = self.get_bet_gold()
        gambler.is_win = self.result
        gambler.win_gold = self.win_gold
        gambler.fee = self.tax
        gambler.create_time = time.strftime('%Y-%m-%d %H:%M:%S')
        session.add(gambler)

    def save_record(self, session):
        record = session.query(TTexasPlayer).filter(TTexasPlayer.uid == self.uid).first()
        if record:
            record.play_count += 1
            if self.result < 0:
                record.win_count += 1
            if self.win_gold > record.max_win_gold:
                record.max_win_gold = self.win_gold
            session.merge(record)
        else:
            record = TTexasPlayer()
            record.uid = self.uid
            if self.result == -1:
                record.win_count = 1
            else:
                record.win_count = 0
            record.play_count = 1
            record.max_win_gold = self.win_gold if self.win_gold > 0 else 0
            session.add(record)

    def save_rank(self, session):
        if self.win_gold <= 0:
            return

        user_rank = session.query(TRankTexasTop).filter(and_(TRankTexasTop.uid == self.uid, TRankTexasTop.add_date == time.strftime('%Y-%m-%d'))).first()
        if user_rank != None:
            session.query(TRankTexasTop).filter(and_(TRankTexasTop.uid == self.uid, TRankTexasTop.add_date == time.strftime('%Y-%m-%d'))).update({
                TRankTexasTop.total : TRankTexasTop.total + self.win_gold
            })
        else:
            top = TRankTexasTop()
            top.add_date = time.strftime('%Y-%m-%d')
            top.uid = self.uid
            top.created_time = time.strftime('%Y-%m-%d %H:%M:%S')
            top.total = self.win_gold
            session.add(top)


    def __repr__(self):
        return '<Gambler uid=%d,pokers=%s>' % (self.uid,self.final_poker.pokers)

    def get_own_proto_struct(self, pb_own):
        if pb_own == None:
            pb_own = pb2.PlayerPokers()
        pb_own.uid = self.uid
        for poker in self.pokers:
            poker.get_proto_struct(pb_own.pokers.add())

    def get_final_poker_proto_struct(self, pb_final):
        if pb_final == None:
            pb_final = TexasPlayerPokers()
        pb_final.uid = self.uid
        pb_final.poker_type = self.final_poker.poker_type
        for poker in self.final_poker.pokers:
            poker.get_proto_struct(pb_final.pokers.add())

    def get_result_proto_struct(self, pb_result):
        if pb_result == None:
            pb_result = TexasPlayerResult()
        pb_result.uid = self.uid
        pb_result.result = self.result
        pb_result.win_gold = self.win_gold
        pb_result.reward_gold = self.reward_gold
        pb_result.gold = self.player.user.get_gold()

        pb_result.bet_gold = self.low_gold + self.add_bei_gold + self.bet_reward_gold
        pb_result.add_bei_gold = self.add_bei_gold
        pb_result.is_watch = self.is_watch()
        pb_result.is_giveup = self.is_giveup()

class Texas:

    def __init__(self, table, min_gold,max_gold,min_chip,min_reward_chip,fee_rate,round_seconds):
        self.min_gold = min_gold
        self.max_gold = max_gold
        self.min_chip = min_chip
        self.min_reward_chip = min_reward_chip
        self.fee_rate = fee_rate
        self.round_seconds = round_seconds

        self.table = table
        self.dealer = None
        self.gamblers = {}
        self.public_pokers = []
        self.start_time = -1
        self.total_gold = 0
        self.next_start = 0

        self.fapai_time = 0

        # Game对象在new Table中被创建，需要将status和剩余可投注时间初始化，只有第一次才赋值TEXAS_START后期·
        self.status = TEXAS_WAIT
        self.round_start_time = microtime()

        self.actions = set([])
        self.rounds = set([])
        self.pass2 = set([])

        self.sender = GameEventSender(table, self)
        self.poker_manager = PokerManager()

        # gevent.spawn(self.test)

    def test(self):
        while True:
            print self.round_start_time,self.status,self.table.players.keys(),self.gamblers.keys()
            gevent.sleep(0.5)

    def reset(self):
        self.dealer = None
        self.gamblers = {}
        self.public_pokers = []
        self.start_time = -1
        self.total_gold = 0
        self.next_start = 0
        self.round_start_time = microtime()

        self.actions = set([])
        self.rounds = set([])
        self.pass2 = set([])

        self.status = TEXAS_WAIT

        self.poker_manager = PokerManager()

    def is_started(self):
        return self.round_start_time > 0

    def get_remain_seconds(self, stime):
        if self.status == TEXAS_OVER:
            next_time_sec =  self.next_start - microtime()
            if next_time_sec < 0:
                return 0
            return next_time_sec

        if self.status == TEXAS_START:
            self.fapai_time = 0
        remain = (10000 + self.fapai_time * 1000) - (microtime() - stime)
        if remain >= 0:
            return remain
        return remain

    def reset_rounds(self):
        self.rounds = set([])

    def reset_remain_seconds(self):
        self.round_start_time = microtime()

    def can_start(self):
        return set(self.table.players.keys()) == self.rounds

    def can_next(self):
        return set([x.uid for x in self.gamblers.values() if not x.is_watch()]) == self.rounds

    def can_next2(self):
        return set([x.uid for x in self.gamblers.values() if x.is_pass() or x.is_add_bei() or x.is_watch()]) == (self.rounds | self.actions)

    def can_finish(self):
        for gambler in self.gamblers.values():
            if gambler.action in [PASS, BET]:
                return False
        return True

        # watch_uids = set([x.uid for x in self.watch_gamblers()])
        # return set(self.table.players.keys()) == set(self.gamblers.keys()) and set(self.gamblers.keys()) == (self.actions | watch_uids)
        # return set(self.gamblers.keys()) == (self.actions | watch_uids)

    def all_gamblers_watch(self):
        if self.status in [TEXAS_WAIT, TEXAS_START]:
            if set(self.table.players.keys()) == set(self.gamblers.keys()):
                if all([True if x.is_watch() else False for x in self.gamblers.values()]):
                    return True
        return False

    def add_bei_gamblers(self):
        return [x for x in self.gamblers.values() if x.is_add_bei()]

    def giveup_gamblers(self):
        return [x for x in self.gamblers.values() if x.is_giveup()]

    def watch_gamblers(self):
        return [x for x in self.gamblers.values() if x.is_watch()]

    def bet_gamblers(self):
        return [x for x in self.gamblers.values() if x.is_bet()]

    def pass_gamblers(self):
        return [x for x in self.gamblers.values() if x.is_pass()]

    def no_bet_players(self):
        return set(self.table.players.keys()) - (set([x.uid for x in self.watch_gamblers()]) | set([x.uid for x in self.bet_gamblers()]))

    def no_add_bei_gamblers(self):
        return [x for x in self.gamblers.values() if x.is_pass() and x.uid not in self.pass2]

    def play_gamers(self):
        gamblers = {}
        for uid, gambler in self.gamblers.items():
            if not gambler.is_watch():
                gamblers[uid] = gambler
        return gamblers

    def start_with_lock(self):
        self.table.lock.acquire()
        try:
            self.start()
        except:
            traceback.print_exc()
        finally:
            self.table.lock.release()

    def start(self):
        self.reset()
        self.table.kick_invalid_players()

        self.status = TEXAS_START
        self.round_start_time = microtime()
        self.sender.send_start()
        self.fapai_time = 0
        gevent.spawn_later(NEXT_TURN_SECONDS ,self.handle_hand_with_lock, self.round_start_time)

    def bet(self, uid, action, bet_gold = 0, bet_reward_gold = 0):
        result = -1
        print self.get_remain_seconds(self.round_start_time),microtime(),self.round_start_time
        if self.get_remain_seconds(self.round_start_time) < 0:
            return RESULT_FAILED_ALREADY_READY
        self.rounds.add(uid)

        if action == BET:
            result = self.bet_join(uid, bet_gold, bet_reward_gold)
        elif action == ADD_BEI:
            result = self.bet_bei(uid, bet_gold)
        elif action == GIVEUP:
            result = self.bet_giveup(uid)
        elif action == PASS:
            result = self.bet_pass(uid)
        elif action == WATCH:
            result = self.bet_watch(uid)

        self.next_round()

        return result

    def bet_join(self, uid, bet_gold, bet_reward_gold):

        if self.status > TEXAS_START:
            return RESULT_FAILED_ALREADY_START

        player = self.table.get_player(uid)
        if player == None:
            raise Exception("player is not exist")

        logging.info('user=%d投注bet_gold=%d,gold=%d,has_gold=%d' % (uid,bet_gold, player.get_gold(),player.get_gold()))
        if not player.has_gold(TEXAS_MIN_GOLD):
            return RESULT_FAILED_LESS_GOLD

        gambler = Gambler(self,player)
        gambler.do_join(bet_gold, bet_reward_gold)
        self.gamblers[uid] = gambler

        self.sender.send_bet_bet(uid, bet_gold, gambler )
        player = self.table.players[uid]
        player.idle_time = int(time.time())
        player.incr_watch(is_watch=False)

        return 0

    def bet_bei(self, uid, bet_gold):
        self.actions.add(uid)

        gambler = self.gamblers[uid]
        logging.info('机器人乱投倍注bet_gold=%d,gold=%d,has_gold=%s' % (bet_gold, gambler.get_gold(),gambler.has_gold(bet_gold)))
        if not gambler.has_gold(bet_gold):
            return RESULT_FAILED_LESS_GOLD


        gambler.do_add_bei(bet_gold)
        self.sender.send_bet_add(uid, gambler, bet_gold)
        return 0

    def bet_giveup(self, uid):
        self.actions.add(uid)

        gambler = self.gamblers[uid]
        gambler.do_giveup()

        self.sender.send_bet_give_up(uid)
        return 0

    def bet_pass(self, uid):
        gambler = self.gamblers[uid]
        gambler.do_pass()

        if self.status == TEXAS_PUBLIC_3:
            self.pass2.add(uid)

        self.sender.send_bet_pass(uid)
        return 0

    def bet_watch(self, uid):
        self.actions.add(uid)

        player = self.table.players.get(uid, None)
        player.idle_time = int(time.time())

        gambler = Gambler(self, player)
        gambler.do_watch()
        self.gamblers[uid] = gambler

        self.sender.send_bet_watch(uid)

        return 0

    def new_watch(self, uid):
        self.actions.add(uid)

        player = self.table.players.get(uid, None)
        player.idle_time = int(time.time())

        print '游戏开始后进来的',self
        gambler = Gambler(self, player)
        gambler.do_watch()
        self.gamblers[uid] = gambler

    def handle_hand(self, round_start_time):

        print '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~',self.round_start_time,round_start_time
        if self.round_start_time != round_start_time:
            return

        if len(self.table.players) == 0:
            return

        if self.status not in [TEXAS_WAIT, TEXAS_START]:
            return

        for uid in self.no_bet_players():
            gambler = Gambler(uid, self.table.players[uid])
            gambler.do_watch()
            self.gamblers[uid] = gambler
            self.sender.send_bet_watch(gambler.uid)

        if len(self.watch_gamblers()) == len(self.table.players):
            gevent.spawn_later(1,self.start)
            return

        print '123123~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'
        for gambler in self.bet_gamblers():
            gambler.pokers = [self.poker_manager.choice_poker(need_remove=True), self.poker_manager.choice_poker(need_remove=True)]

        self.status = TEXAS_HAND
        self.reset_rounds()
        self.sender.send_hand_poker()
        self.reset_remain_seconds()

        self.fapai_time = 0
        self.fapai_time = len(self.bet_gamblers()) * 0.5
        gevent.spawn_later(NEXT_TURN_SECONDS + self.fapai_time + 1 , self.handle_public3_with_lock)

    def handle_public_3(self):
        if self.status != TEXAS_HAND:
            return
        if len(self.public_pokers) == 3:
            return

        self.status = TEXAS_PUBLIC_3

        for gambler in self.bet_gamblers():
            gambler.do_pass()
            self.sender.send_bet_pass(gambler.uid)

        self.public_pokers += [self.poker_manager.choice_poker(need_remove=True),
                               self.poker_manager.choice_poker(need_remove=True),
                               self.poker_manager.choice_poker(need_remove=True),]

        self.sender.send_public_pokers(self.public_pokers)
        self.reset_rounds()
        self.reset_remain_seconds()
        self.fapai_time = 1
        gevent.spawn_later(NEXT_TURN_SECONDS + 1, self.handle_public5_with_lock)

    def handle_public_5(self):
        if self.status != TEXAS_PUBLIC_3:
            return
        if len(self.public_pokers) == 5:
            return

        self.status = TEXAS_PUBLIC_5

        print [x.action for x in self.gamblers.values()]
        for gambler in self.no_add_bei_gamblers():
            gambler.do_pass()
            self.sender.send_bet_pass(gambler.uid)

        # 推送剩余2张公牌
        self.public_pokers += [self.poker_manager.choice_poker(need_remove=True),
                                   self.poker_manager.choice_poker(need_remove=True),]

        self.sender.send_public_pokers(self.public_pokers[-2:])
        self.reset_rounds()
        self.reset_remain_seconds()
        self.fapai_time = 1
        gevent.spawn_later(NEXT_TURN_SECONDS + 1, self.handle_over_with_lock)# 3s客户端展现公牌动画,10s用于展现加注时间

    def handle_over(self):
        if self is not self.table.game:
            return

        if self.status != TEXAS_PUBLIC_5:
            return

        if len(self.public_pokers) == 0:
            gevent.spawn_later(0, self.send_remain_pokers_with_lock, TEXAS_PUBLIC_3)
            gevent.spawn_later(2, self.send_remain_pokers_with_lock, TEXAS_PUBLIC_5)
            gevent.spawn_later(5, self.handle_result_with_lock)
        elif len(self.public_pokers) == 3:
            gevent.spawn_later(0, self.send_remain_pokers_with_lock, TEXAS_PUBLIC_5)
            gevent.spawn_later(2, self.handle_result_with_lock)
        else:
            self.over_result()

    def over_result(self):
        self.status = TEXAS_OVER

        for gambler in [x for x in self.gamblers.values() if x.is_pass()]:
            gambler.do_giveup()
            self.sender.send_bet_give_up(gambler.uid)

        gevent.spawn_later(1, self.over_result_calc)

    def over_result_calc(self):
        for gambler in self.add_bei_gamblers():
            self.poker_manager.check_final_poker(gambler, self.public_pokers)

        self.dealer = Gambler(self, None)
        self.dealer.pokers = [self.poker_manager.choice_poker(need_remove=True),
                               self.poker_manager.choice_poker(need_remove=True)]

        self.dealer.final_poker = self.poker_manager.best_playerpoker(self.dealer.pokers+self.public_pokers)
        # self.dealer.final_poker = PlayerPokers(-1, *(self.dealer.pokers+self.public_pokers))

        self.poker_manager.choice_dealer_poker(self.table, self.dealer, self.add_bei_gamblers(), self.public_pokers)

        self.check_result()

        self.sender.send_game_over()

        self.reward_box()
        # 下一轮开始
        next_round_sec = NEXT_ROUND_BASE + NEXT_ROUND_EACH * len([x for x in self.gamblers.values() if x.is_add_bei() or x.is_giveup()])
        print 'send_over_done................................................................',next_round_sec
        self.next_start = microtime() + next_round_sec
        gevent.spawn_later(next_round_sec, self.start_with_lock)

    def reward_box(self):
        for gambler in self.gamblers.values():
            if not gambler.is_robot() and gambler.get_gold() < 2000000:
                if gambler.uid in self.table.players:
                    player = self.table.players[gambler.uid]
                    if gambler.low_gold > 0:
		        if gambler.win_gold > 0:
			    gevent.spawn_later(5, player.check_reward_box,self.table.manager.service, self.table.redis, 1)
			else:
			    gevent.spawn_later(5, player.check_reward_box,self.table.manager.service, self.table.redis, -1)

		    logging.info('宝箱，uid=%d，次数=%s' % (gambler.uid, player.play_result_counter))

    def check_result(self):
        # self.dealer.final_poker = PlayerPokers(-1, '2-6,4-4,4-3,4-1,4-2,3-9,2-12')
        # self.gamblers[0].finnal_poker = PlayerPokers(24389, '2-6,4-4,4-3,4-1,4-2,1-9,4-12')
        # self.public_pokers = [Poker(2,6),Poker(4,4),Poker(4,3),Poker(4,1),Poker(4,2),]
        for gambler in self.gamblers.values():
            if gambler.is_add_bei():

                compare_result = self.dealer.final_poker.compare(gambler.final_poker)

                gambler.calc_gold(compare_result, self)
                gambler.calc_reward_gold(compare_result, self)
                gambler.result = compare_result

                self.table.broadcast_win(gambler)
            elif gambler.is_giveup():
                print 'enter.................................',self,dir(self)
                gambler.calc_gold(0, self)
                gambler.result = 1

        self.handle_result()

    def handle_result(self):

        session = self.table.get_session()
        session.begin()
        try :
            self.calc_result(session)
            session.commit()
        except:
            traceback.print_exc()
            session.rollback()
        finally:
            self.table.close_session(session)

    def calc_result(self, session):
        game = None
        if any([False if x.is_robot() else True for x in self.gamblers.values()]):
            game = self.save_game(session)
        for gambler in [x for x in self.gamblers.values() if x.is_add_bei() or x.is_giveup()]:
            if not gambler.is_robot():
                gambler.save_result(session, game.id)
            gambler.save_win_gold(session)
            gambler.save_record(session)
            gambler.save_rank(session)

    def save_game(self, session):
        game = TTexas()
        game.dealer_hand_pokers = str(self.dealer.pokers)
        game.dealer_pokers = str(self.dealer.final_poker.pokers)
        game.public_pokers = str(self.public_pokers)
        game.countof_gamblers = len([x for x in self.gamblers.values() if not x.is_robot()])
        game.result_gold = self.total_gold
        game.create_time = time.strftime('%Y-%m-%d %H:%M:%S')
        session.add(game)
        session.flush()
        return game

    def handle_hand_with_lock(self, round_start_time):
        self.table.lock.acquire()
        try:
            self.handle_hand(round_start_time)
        except:
            traceback.print_exc()
        finally:
            self.table.lock.release()

    def handle_public3_with_lock(self):
        self.table.lock.acquire()
        try:
            self.handle_public_3()
        except:
            traceback.print_exc()
        finally:
            self.table.lock.release()

    def handle_public5_with_lock(self):
        self.table.lock.acquire()
        try:
            self.handle_public_5()
        except:
            traceback.print_exc()
        finally:
            self.table.lock.release()

    def handle_over_with_lock(self):
        self.table.lock.acquire()
        try:
            self.handle_over()
        except:
            traceback.print_exc()
        finally:
            self.table.lock.release()

    def handle_result_with_lock(self):
        self.table.lock.acquire()
        try:
            self.over_result()
        except:
            traceback.print_exc()
        finally:
            self.table.lock.release()

    def send_remain_pokers_with_lock(self, status):
        self.table.lock.acquire()
        try:
            self.send_remain_pokers(status)
        except:
            traceback.print_exc()
        finally:
            self.table.lock.release()

    def send_remain_pokers(self, status):
        self.status = status

        if status == TEXAS_PUBLIC_5:
            poker4, poker5 = self.get_no_shun_or_4tiao()
            p_4 = -1
            for i,x in enumerate(self.poker_manager.pokers):
                if x.flower == poker4.flower and x.value == poker4.value:
                    p_4 = i
                    break
            if p_4 > 0:
                self.poker_manager.pokers.pop(p_4)

            p_5 = -1
            for i,x in enumerate(self.poker_manager.pokers):
                if x.flower == poker5.flower and x.value == poker5.value:
                    p_5 = i
                    break
            if p_5 > 0:
                self.poker_manager.pokers.pop(p_5)

            self.public_pokers.append(poker4)
            self.public_pokers.append(poker5)
            self.sender.send_public_pokers([poker4,poker5])
        elif status == TEXAS_PUBLIC_3:
            self.public_pokers.append( self.poker_manager.choice_poker(need_remove=True) )
            self.public_pokers.append( self.poker_manager.choice_poker(need_remove=True) )
            self.public_pokers.append( self.poker_manager.choice_poker(need_remove=True) )
            self.sender.send_public_pokers(self.public_pokers)

    def get_no_shun_or_4tiao(self):
        poker4 = self.poker_manager.choice_poker(need_remove=False)
        poker5 = self.poker_manager.choice_poker(need_remove=False)
        if poker4.flower == poker5.flower and poker4.value == poker5.value:
            return self.get_no_shun_or_4tiao()

        pokers = self.public_pokers + [poker4,poker5]

        player_poker = PlayerPokers(-1, *(pokers))
        if player_poker.poker_type == T_SHUN or player_poker.poker_type == T_4_TIAO:
            logging.info(u'发剩余2张公牌，组成了顺子或者4条，换新的剩余2张牌')
            return self.get_no_shun_or_4tiao()
        return poker4,poker5

    def next_round(self):
        print 1
        if self.all_gamblers_watch():
            gevent.spawn_later(1, self.start_with_lock)
            print '当前状态=%d,玩家=%s,赌客=%s,观战的赌客=%s' % (self.status, self.table.players.keys(),self.gamblers.keys(),[x.uid for x in self.gamblers.values() if x.is_watch()])
            return
        print 2
        if set(self.table.players.keys()) == set(self.gamblers.keys()) and self.can_finish():
            self.status = TEXAS_PUBLIC_5
            gevent.spawn_later(1, self.handle_over_with_lock)
            print '所有用户已操作，执行结束流程',self.round_start_time
            return
        print 3
        if self.status == TEXAS_START and self.can_start():
            round_start_time = self.round_start_time
            self.round_start_time = 0
            gevent.spawn_later(1, self.handle_hand_with_lock, self.round_start_time)
            print '所有用户已投注或观战，执行手牌事件',self.round_start_time
            return
        print 4
        if self.status == TEXAS_HAND and self.can_next():
            self.round_start_time = 0
            gevent.spawn_later(1, self.handle_public3_with_lock)
            print '所有用户（赌客用户）已投倍注或观战，执行发3张公牌操作',self.round_start_time
            return
        print 5
        if self.status == TEXAS_PUBLIC_3 and self.can_next2():
            self.round_start_time = 0
            gevent.spawn_later(1, self.handle_public5_with_lock)
            print '所有用户（赌客用户）已投注或观战，执行发剩余2张公牌操作',self.round_start_time
            return

    def get_proto_struct(self, pb_table):
        remain_sec  = self.get_remain_seconds(self.round_start_time)
        logging.info('remain_micro_sec=%d, remain_sec=%d, check_remain_sec=%d' % (remain_sec,int(remain_sec/1000),0 if remain_sec < 0 else int(remain_sec / 1000)))
        # pb_table.remain_seconds = 0 if remain_sec < 0 else int(remain_sec / 1000)
        # pb_table.texas_status = TEXAS_WAIT if remain_sec < 0 else self.status
        pb_table.remain_seconds = int(remain_sec / 1000)
        pb_table.texas_status = self.status

        pb_table.table_type = self.table.table_type

        for poker in self.public_pokers:
            poker.get_proto_struct(pb_table.public_pokers.add())

        for gambler in self.gamblers.values():
            if gambler.uid in [x.uid for x in self.add_bei_gamblers()]:
                if gambler.final_poker != None:
                    gambler.get_final_poker_proto_struct(pb_table.final_player_pokers.add())
            if gambler.result != None:
                gambler.get_result_proto_struct(pb_table.player_results.add())

class PokerManager:

    def __init__(self):
        self.public_pokers = []
        self.pokers = []
        self.init_poker()

    def init_poker(self):
        for flower in xrange(1, 5):
            for value in xrange(1, 14):
                self.pokers.append(Poker(flower, value))
        random.shuffle(self.pokers)


    def choice_dealer_poker(self, table, dealer, gamblers, public_pokers):
        # add_bei_gmablers = [x for x in gamblers.values() if x.action == ADD_BEI]
        # 机器人服务ID
        add_bei_gamblers = [x for x in gamblers if not x.is_robot()]
        if len(add_bei_gamblers) == 0:
            logging.info(u'所有真实玩家都弃牌了，只有庄家和机器人在')
            return

        add_bei_gamblers.sort(cmp=lambda x,y: x.final_poker.compare(y.final_poker))
        min_player_poker = add_bei_gamblers[0].final_poker
        min_poker_compare = dealer.final_poker.compare(min_player_poker)
        logging.info(u'当前庄家牌型=%s ，最小玩家牌型=%s' % (str(dealer.final_poker.pokers), str(min_player_poker.pokers)))
        logging.info('当前牌局真实用户人数=%s' % [x.uid for x in add_bei_gamblers])
        if min_poker_compare <= 0:
            logging.info(u'比较结果=%d' % min_poker_compare)
            logging.info(u'gamblers=%s , add_gamblers=%s' % (gamblers, add_bei_gamblers))
            if self.need_bester_poker(table, add_bei_gamblers):
                choice_poker_rs, best_poker, p1, p2 = self.get_new_best_poker(min_player_poker, public_pokers)
                if choice_poker_rs:
                    dealer.final_poker = best_poker
                    dealer.pokers = [p1, p2]
                    logging.info(u'庄家重新获得手牌后 poker=%s ,final=%s' % (str(dealer.pokers), str(dealer.final_poker.pokers)))
                else:
                    logging.info(u'重新选牌了，但是没有选出来，使用初始的庄家手牌')


    def need_bester_poker(self, table, gamblers):

        choice_again_rate = self.dealer_history_lose(table, gamblers)
        t = [True] * choice_again_rate + [False] * (100-choice_again_rate)
        choice_again = random.choice( t )
        logging.info(u'庄家重新选牌概率=%d，是否重选=%s' % (choice_again_rate, choice_again))
        return choice_again

    def get_new_best_poker(self, min_player_poker, public_pokers):
        for _ in range(10):
            poker1 = self.choice_poker(need_remove=False)
            poker2 = self.choice_poker(need_remove=False)
            if poker1.value == poker2.value or poker1.flower == poker2.flower:
                continue
            pokers = (poker1,
                      poker2,
                      public_pokers[0],
                      public_pokers[1],
                      public_pokers[2],
                      public_pokers[3],
                      public_pokers[4],)
            logging.info(u'庄家进行了重新选牌，7张牌是=%s' % (str(pokers)))
            new_best_poker = self.best_playerpoker(pokers)
            logging.info(u'庄家重选后的新牌=%s 牌型=%s' % (new_best_poker.pokers, new_best_poker.poker_type))
            if new_best_poker.compare(min_player_poker) == 1:
                logging.info(u'取得庄家比最小牌型大的牌，结束选牌')
                logging.info(u'确认庄家牌=%s 牌型=%d' % (new_best_poker.pokers,new_best_poker.poker_type))
                return True, new_best_poker, poker1,poker2
        return False,None,None,None

    def dealer_history_lose(self, table, gamblers):
        no_giveup = len(gamblers)
        rate_index = no_giveup -1

        session = table.get_session()
        try:
            log = session.query(TTexas).order_by(TTexas.id.desc()).limit(800).all()
	    logging.info('sql=%s' % session.query(TTexas).order_by(TTexas.id.desc()).limit(800))
	    logging.info('800局胜负总和=%s' % sum([x.result_gold for x in log]))
            if sum([x.result_gold for x in log]) < 0:
                logging.info('最近800局的概率，当前rate_index=%d,val=%d' % (rate_index, DEALER_CHOICE_CONF[800][rate_index]))
                return DEALER_CHOICE_CONF[800][rate_index]
            elif sum([x.result_gold for x in log[:400]]) < 0:
                logging.info('最近400局的概率，当前rate_index=%d,val=%d' % (rate_index, DEALER_CHOICE_CONF[400][rate_index]))
                return DEALER_CHOICE_CONF[400][rate_index]
            elif sum([x.result_gold for x in log[:200]]) < 0:
                logging.info('最近200局的概率，当前rate_index=%d,val=%d' % (rate_index, DEALER_CHOICE_CONF[200][rate_index]))
                return DEALER_CHOICE_CONF[200][rate_index]
            elif sum([x.result_gold for x in log[:100]]) < 0:
                logging.info('最近100局的概率，当前rate_index=%d,val=%d' % (rate_index, DEALER_CHOICE_CONF[100][rate_index]))
                return DEALER_CHOICE_CONF[100][rate_index]
            elif sum([x.result_gold for x in log[:50]]) < 0:
                logging.info('最近50局的概率，当前rate_index=%d,val=%d' % (rate_index, DEALER_CHOICE_CONF[50][rate_index]))
                return DEALER_CHOICE_CONF[50][rate_index]
            else:
                logging.info('50局内的概率，当前rate_index=%d,val=%d' % (rate_index, DEALER_CHOICE_CONF[-1][rate_index]))
                return DEALER_CHOICE_CONF[-1][rate_index]
        except:
            traceback.print_exc()
        finally:
            table.close_session(session)

    def check_final_poker(self, gambler, public_pokers):
        try:
            logging.info(u'  697,用户=%d手牌=%s，公牌=%s' %(gambler.uid, str(gambler.pokers), public_pokers))
            pokers = gambler.pokers + public_pokers
            # print 'poker:',gambler.pokers
            # print 'public_poker:',public_pokers
            # gambler.final_poker = PlayerPokers(gambler.uid, *pokers)
            gambler.final_poker = self.best_playerpoker(gambler.pokers + public_pokers)
            logging.info(u'  702,用户=%d最好的牌=%s, 牌型=%d' % (gambler.uid, str(gambler.final_poker.pokers), gambler.final_poker.poker_type))

        except:
            traceback.print_exc()
        finally:
            pass

    def choice_poker(self, need_remove = True):
        poker = random.choice(self.pokers)
        if need_remove:
            self.pokers.remove(poker)
        return poker

    def best_playerpoker(self, pokers7):
        best_pokers = []
        for pokers in itertools.combinations(pokers7, 5):
            best_pokers.append( PlayerPokers(-1, *pokers) )
        best_pokers.sort(cmp=lambda x,y: x.compare(y), reverse=True)
        return best_pokers[0]

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

    def __init__(self, uid, poker1, poker2, poker3, poker4, poker5):
        self.uid = uid
        self.pokers = []
        self.poker_type = None

        self.pokers.append(poker1)
        self.pokers.append(poker2)
        self.pokers.append(poker3)
        self.pokers.append(poker4)
        self.pokers.append(poker5)

        self.pokers.sort(cmp = self.sort_poker, reverse=True)

        self.values = [14 if x.value == 1 else x.value for x in self.pokers]
        self.flowers = [x.flower for x in self.pokers]
        self.value_counter = collections.Counter(self.values).most_common()
        self.value_counter.sort(cmp=self.sort_counter,reverse=True)
        self.flower_counter = collections.Counter(self.flowers).most_common()

        self.init_poker()

    def init_poker(self):
        if self.is_royal():
            self.poker_type = T_ROYAL
        elif self.is_tonghuashun():
            self.poker_type = T_TONGHUASHUN
        elif self.is_4tiao():
            self.poker_type = T_4_TIAO
        elif self.is_hulu():
            self.poker_type = T_HULU
        elif self.is_tonghua():
            self.poker_type = T_TONGHUA
        elif self.is_shun():
            self.poker_type = T_SHUN
        elif self.is_3tiao():
            self.poker_type = T_3_TIAO
        elif self.is_2dui():
            self.poker_type = T_2_DUI
        elif self.is_dui():
            self.poker_type = T_DUI
        else:
            if self.is_dan():
                self.poker_type = T_GAO
            else:
                raise Exception(u'必须处理：最后判断是否是单牌出现了异常=%s' % str(self.pokers))

    def to_pokers_str(self):
        pokers = self.pokers
        return "%d-%d,%d-%d,%d-%d" % (pokers[0].flower,pokers[0].value,pokers[1].flower,pokers[1].value,pokers[2].flower,pokers[2].value)

    def __repr__(self):
        return "%s" % (self.pokers)

    def sort_poker(self,x,y):
        xv = x.value
        yv = y.value
        if xv == 1:
            xv = 14
        if yv == 1:
            yv = 14
        return cmp(xv,yv)

    def sort_counter(self, x, y):
        if x[1] == y[1]:
            return cmp(x[0],y[0])
        elif x[1] > y[1]:
            return 1
        else:
            return -1

    def get_reward_poker_rate(self):
        if self.poker_type not in REWARD_POKER.keys() :
            return -1
        return REWARD_POKER[self.poker_type]

    def is_royal(self):
        if self.is_tonghua() and set(self.values) == set([10,11,12,13,14]):
            return True
        return False

    def is_tonghuashun(self):
        if self.is_tonghua() and self.is_shun():
            return True
        return False

    def is_4tiao(self):
        if self.value_counter[0][1] == 4 and self.value_counter[1][1] == 1:
            return True
        return False

    def is_hulu(self):
        if self.value_counter[0][1] == 3 and self.value_counter[1][1] == 2:
            return True
        return False

    def is_tonghua(self):
        if self.flower_counter[0][1] == 5:
            return True
        return False

    def is_shun(self):
        if max(self.values) - min(self.values) == 4 and len(set(self.values)) == 5:
            return True

        if set(self.values) == set([14,2,3,4,5]):
            return True
        return False

    def is_3tiao(self):
        if self.value_counter[0][1] == 3 and self.value_counter[1][1] == 1 and self.value_counter[2][1] == 1:
            return True
        return False

    def is_2dui(self):
        if self.value_counter[0][1] == 2 and self.value_counter[1][1] == 2 and self.value_counter[2][1] == 1:
            return True
        return False

    def is_dui(self):
        if self.value_counter[0][1] == 2 and \
                        self.value_counter[1][1] == 1 and \
                        self.value_counter[2][1] == 1 and \
                        self.value_counter[3][1] == 1:
            return True
        return False

    def is_dan(self):
        if self.value_counter[0][1] == 1 and \
                    self.value_counter[1][1] == 1 and \
                    self.value_counter[2][1] == 1 and \
                    self.value_counter[3][1] == 1 and \
                    self.value_counter[4][1] == 1:
            return True
        return False

    def compare(self, other, isend = False):
        rs = None
        if self.poker_type != other.poker_type:
            rs = self.poker_type - other.poker_type
        elif self.poker_type == T_ROYAL:
            rs = 1
        elif self.poker_type == T_TONGHUASHUN:
            max_values = max(self.values, other.values)
            if max_values == self.values:
                rs = 1
            else:
                rs = -1
        elif self.poker_type == T_4_TIAO:
            rs = cmp(self.value_counter[0][0], other.value_counter[0][0]) # 先比4张
            if rs == 0:
                rs = cmp(self.value_counter[1][0], other.value_counter[1][0]) # 4张平局，继续比剩下的1张
        elif self.poker_type == T_HULU:
            rs = cmp(self.value_counter[0][0], other.value_counter[0][0]) # 先比3张
            if rs == 0:
                rs = cmp(self.value_counter[1][0], other.value_counter[1][0]) # 3张平局，继续比剩下的2张，葫芦剩余两张牌一样，只用比一次
        elif self.poker_type == T_TONGHUA:
            max_values = max(self.values, other.values)
            if max_values == self.values:
                rs = 1
            else:
                rs = -1
        elif self.poker_type == T_SHUN:
            if set(self.values) == set([14,2,3,4,5])  and set(other.values) == set([14,2,3,4,5]):
                rs = 1
            elif set(self.values) == set([14,2,3,4,5]):
                rs = -1
            elif set(other.values) == set([14,2,3,4,5]):
                rs = 1
            else:
                max_values = max(self.values, other.values)
                if max_values == self.values:
                    rs = 1
                else:
                    rs = -1
        elif self.poker_type == T_3_TIAO:
            rs = cmp(self.value_counter[0][0], other.value_counter[0][0])
            if rs == 0:
                rs = cmp(self.value_counter[1][0], other.value_counter[1][0]) # 比剩余的第1个单张
                if rs == 0:
                    rs = cmp(self.value_counter[2][0], other.value_counter[2][0]) # 比剩余的第2个单张
        elif self.poker_type == T_2_DUI:
            rs = cmp(self.value_counter[0][0], other.value_counter[0][0])
            if rs == 0:
                rs = cmp(self.value_counter[1][0], other.value_counter[1][0]) # 比剩余的2张一样的对子
                if rs == 0:
                    rs = cmp(self.value_counter[2][0], other.value_counter[2][0]) # 比剩余的单张
        elif self.poker_type == T_DUI:
            if isend:
                print self.value_counter,other.value_counter
            rs = cmp(self.value_counter[0][0], other.value_counter[0][0])
            if rs == 0:
                rs = cmp(self.value_counter[1][0], other.value_counter[1][0]) # 比剩余的第1个单张
                if rs == 0:
                    rs = cmp(self.value_counter[2][0], other.value_counter[2][0]) # 比剩余的第2个单张
                    if rs == 0:
                        rs = cmp(self.value_counter[3][0], other.value_counter[3][0]) # 比剩余的单张
        else:
            max_values = max(self.values, other.values)
            if max_values == self.values:
                rs = 1
            else:
                rs = -1

        # 比对最后还是==0，那么返回1让庄家牌大
        if rs == 0:
            return 1
        elif rs < 0:
            return -1
        else:
            return 1

class Poker:
    def __init__(self,flower,value):
        self.flower = flower
        self.value = value

    def __eq__(self,other):
        return self.flower == other.flower and self.value == other.value

    def compare(self, other):
        if self.value == 1:
            return 1
        if other.value == 1:
            return -1
        if self.value > other.value:
            return 1
        elif self.value < other.value:
            return -1
        else:
            return 0

    def __repr__(self):
        return "%d-%d" % (self.flower,self.value,)

    def get_proto_struct(self,pb_poker = None):
        if pb_poker == None:
            pb_poker = pb2.Poker()
        pb_poker.flower = self.flower
        pb_poker.value = self.value
        return pb_poker


if __name__ == '__main__':
    start = time.time()
    # pm = PokerManager()
    #
    # p1 = pm.best_playerpoker([
    #     Poker(flower=4,value=5),
    # Poker(flower=2,value=2),
    # Poker(flower=3,value=5),
    # Poker(flower=1,value=11),
    #
    # Poker(flower=3,value=2),
    # Poker(flower=2,value=5),
    # Poker(flower=4,value=12),])
    #
    # p2 = pm.best_playerpoker([Poker(flower=4,value=4),
    # Poker(flower=4,value=4),
    # Poker(flower=3,value=5),
    # Poker(flower=1,value=11),
    #
    # Poker(flower=3,value=2),
    # Poker(flower=2,value=5),
    # Poker(flower=4,value=12),])
    #
    # # for x in bests1:
    # #     print x,x.poker_type
    # # for x in bests2:
    # #     print x,x.poker_type
    # # print bests2
    # print p1.pokers
    # print p2.pokers
    # print p1.compare(p2)
    # end = time.time()
    # print 'start:',start,'end:',end,'time:',end - start

    pm = PokerManager()
    p1 = pm.best_playerpoker([
        Poker(flower=4,value=13),
        Poker(flower=4,value=11),
        Poker(flower=2,value=10),
        Poker(flower=4,value=12),

        Poker(flower=3,value=10),
        Poker(flower=4,value=10),
        Poker(flower=4,value=1),])

    print p1,p1.poker_type
    print p1.value_counter
    # p = PlayerPokers.from_pokers_str(-1, '2-1,1-2,1-3,1-4,1-5')
    # print p.is_shun(),p.pokers,p.poker_type



