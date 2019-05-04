#coding: utf-8

from proto.constant_pb2 import *

MAX_TABLE_PLAYER = 5

DELAY_FOR_COMPARE = 5
DELAY_FOR_SHOW_HAND = 3


WAIT_SECONDS = 5

#min_gold,max_gold,min_chip,max_chip,required_round,max_round,fee_rate,round_seconds

TABLE_GAME_CONFIG = {
    TABLE_L : (3000     ,200000,	200        ,3000     ,2,19,0.01,   20),
    TABLE_M : (50000   ,1600000,	2000       ,20000    ,2,19,0.02,20),
    TABLE_H : (300000  ,-1,	10000      ,100000   ,4,29,0.05,25),
    TABLE_H2: (2000000	,-1		,   50000	   ,500000	 ,4,87,0.05,30),
}
