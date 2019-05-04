# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import unittest


from wartable.robot import *
from wartable.game import *
from wartable.table import *


class RotbotTalkTest(unittest.TestCase):
    def setUp(self):
        print 'setUp...'

    def tearDown(self):
        print 'tearDown...'

    def test_run(self):
        print 'run...'

if __name__ == '__main__':
    t = RotbotTalkTest()
