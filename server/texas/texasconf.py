# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from proto.texas_pb2 import *

FIX = False
FIX_USERS = [49509]

WAIT_SECONDS = 10
RESTART_GAME_SECONDS = 3
NEXT_TURN_SECONDS = 10
NEXT_ROUND_BASE = 7
NEXT_ROUND_EACH = 2
MAX_TABLE_PLAYER = 5
TEXAS_TAX = 0.02
TEXAS_WATCH_MAX = 5
BROADCAST_GOLD_MIN = 20000000
REWARD_POKER = {
    T_ROYAL:100,
    T_3_TIAO:3,
    T_SHUN:4,
    T_TONGHUA:5,
    T_TONGHUASHUN:60,
    T_HULU:8,
    T_4_TIAO:40,
}

TEXAS_MIN_GOLD = 6000
TEXAS_MAX_GOLD = -1
#min_gold,max_gold,min_chip,min_reward_chip,fee_rate,round_seconds
TABLE_GAME_CONFIG = {
    TEXAS_L:(TEXAS_MIN_GOLD, 300000,1000,1000,0.02,10,),
    TEXAS_M:(300001, 12000000,1000,1000,0.02,10,),
    TEXAS_H:(12000001, TEXAS_MAX_GOLD,1000,1000,0.02,10,),
}

DEALER_CHOICE_CONF = {
    800:(35, 45, 55, 65, 75,),
    400:(30, 40, 50, 60, 70,),
    200:(25, 35, 45, 55, 65,),
    100:(20, 30, 40, 50, 60,),
    50:(15, 25, 35, 45, 55,),
    -1:(10, 20, 30, 40, 50,),
}