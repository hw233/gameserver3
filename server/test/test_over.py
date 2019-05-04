# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import sys
import os
import unittest
import mock
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from wartable.table import *
from wartable.game import *
from wartable.gameconf import *
from wartable.gameconf import *
from wartable.eventsender import *

m_player = mock.Mock(Player)
m_player.uid.get.return_value = 33
print m_player.uid


if __name__ == '__main__':
    pass