# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import unittest
import os
import sys
import mock


sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from wartable.game import *

class TTable:
    def __init__(self, game, rank, reward_pool):
        self.game = game
        self.rank = rank
        self.players = {}
        self.reward_pool = reward_pool
class TGame:
    def __init__(self, real_lucky_total):
        self.real_lucky_total = 3000
        self.real_red_total = 1000
        self.real_black_total = 6000

class TRank:
    def __init__(self):
        pass

class TRewardPool:
    def __init__(self, stack):
        self.stack = stack

class PokerTest(unittest.TestCase):
    def setUp(self):
        table = TTable(TGame(1000), TRank(), TRewardPool(1200))
        self.poker_maker = PokerMaker(table)
        self.mock_poker_maker = mock.Mock(self.poker_maker)
        self.mock_poker_maker.get_new_fix_rate.return_value = 0.05

        # self.reward_pool = RewardPool(table)
        # mock_reward_pool = mock.Mock(self.reward_pool)
        # mock_reward_pool.get_new_rate.stack = 0.05

    def tearDown(self):
        pass

    # def test_get_new_rate(self):
    #     print self.poker_maker.get_new_rate(0.2)

    # @unittest.skip('skip test_creater_poker')
    # def test_creater_poker(self):
    #     self.poker_maker.create_poker()
    #     print self.poker_maker.pokers[0],self.poker_maker.pokers[0].poker_type
    #     print self.poker_maker.pokers[1],self.poker_maker.pokers[1].poker_type





