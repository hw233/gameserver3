# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import unittest
import os
import sys
import mock
import redis

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from db.connect import *
from dal.core import *
from wartable import table
from wartable import game
from util.commonutil import *

from proto.constant_pb2 import *

from goldflower import game as goldflower


session = Session()
set_context('session', session)

class ServiceMock:
    def __init__(self):
        self.redis = redis.Redis(host='10.0.1.16',password='Wgc@123456',db=0)
        self.dal = DataAccess(self.redis)

class TableTest(unittest.TestCase):
    def setUp(self):
        self.service = mock.Mock(ServiceMock)
        # p = goldflower.PlayerPokers(-1, game.Poker(11,12), game.Poker(11,12), game.Poker(11,1))
        self.service = ServiceMock()
        self.table = table.Table(self.service)
        self.game = game.WarGame(self.table)
        self.table.game = self.game

        self.table.players[13124] = table.Player(13124, self.table.dal.get_user(13124), -1, 1)
        self.table.players[12384] = table.Player(12384, self.table.dal.get_user(12384), 100, 2)
        self.table.players[12386] = table.Player(12386, self.table.dal.get_user(12386), -1, 3)

        self.game.real_lucky_total = 1000
        self.game.lucky_total = 2000
        self.table.reward_pool.gold = 200000001
        self.table.reward_pool.stack = 300000001

        self.table.reward_pool.init()
        self.table.poker_maker.init()

        self.table.poker_maker.poker_result.winner = 1
        self.table.poker_maker.poker_result.winner_poker = goldflower.PlayerPokers(-1, game.Poker(11,3),
                                                                                   game.Poker(11,5),
                                                                                   game.Poker(11,1))
        self.table.poker_maker.poker_result.winner_poker_type = P_TONGHUA

        self.table.poker_maker.poker_result.red_poker = self.table.poker_maker.poker_result.winner_poker
        self.table.poker_maker.poker_result.black_poker = goldflower.PlayerPokers(-1, game.Poker(11,11),
                                                                                  game.Poker(11,12),
                                                                                  game.Poker(11,12))

        self.table.poker_maker.poker_result.lucky_rate = 4
        self.table.poker_maker.poker_result.win_types = [0,1]

        # self.table.poker_maker.poker_result.win_types = [-1]
        # self.table.poker_maker.poker_result.lucky_rate = 4


        self.game.player_actions[13124] = [game.PlayerAction(0, 1000),game.PlayerAction(1, 1000)]
        self.game.player_actions[12384] = [game.PlayerAction(0, 1000),game.PlayerAction(1, 1000)]
        self.game.player_actions[12386] = [game.PlayerAction(-1, 1000),game.PlayerAction(-1, 1000)]

        self.game.player_result[13124] = game.PlayerResult(13124)
        self.game.player_result[12384] = game.PlayerResult(12384)
        self.game.player_result[12386] = game.PlayerResult(12386)

        self.table.reward_pool.init()
        print 'gold:',self.table.reward_pool.gold,'stack:',self.table.reward_pool.stack
        # self.table.poker_maker.init()
        print 'win_types:',self.table.poker_maker.poker_result.win_types
        print 'lucky_rate:',self.table.poker_maker.poker_result.lucky_rate
        print 'winner:',self.table.poker_maker.poker_result.winner, \
            self.table.poker_maker.poker_result.winner_poker, \
            self.table.poker_maker.poker_result.winner_poker_type
        print 'red:',self.table.poker_maker.poker_result.red_poker, \
            self.table.poker_maker.poker_result.red_poker.poker_type, \
            'black',self.table.poker_maker.poker_result.black_poker, \
            self.table.poker_maker.poker_result.black_poker.poker_type

        self.table.rank.init()
        # self.table.reward_pool.reward()


        print 'gold:',self.table.reward_pool.gold,'stack:',self.table.reward_pool.stack

    def tearDown(self):
        pass

    # def test_reward(self):
    #     pass
        # self.table.reward_pool.reward()

    def test_save_player(self):
        print '=========run',self.table.reward_pool.gold,self.table.reward_pool.stack
        for uid, actions in self.table.game.player_actions.items():
            print uid,self.table.players[uid]
            self.game.set_player(uid, actions)
        print '======player_result'
        for uid,result in self.table.game.player_result.items():
            print uid,result
        print '======players'
        for uid,result in self.table.players.items():
            print uid,result
        print '======big_winner'
        print self.table.game.big_winner

        print '====over',self.table.reward_pool.gold,self.table.reward_pool.stack


