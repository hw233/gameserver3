# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import random
import datetime
from proto import constant_pb2

FIX = False
FIX_USERS = []

BROADCAST_MIN_GOLD = 20000000
BET_MAX = 5000000

GAMECONF = {
    'timeout':20,
    'bet_time':15,
    'over_time':5,
    'poker_type_history_len':13,
    'bet_min':50000,
    'tax':0.02,
    'reward_gold_rate':0.2,
    'poker_multiple':{
        constant_pb2.P_DAN:2,
        constant_pb2.P_DUI:3,
        constant_pb2.P_SHUN:4,
        constant_pb2.P_TONGHUA:5,
        constant_pb2.P_TONGHUASHUN:10,
        # constant_pb2.P_BAOZI:0.2 # 彩金池的20%，已经进行特殊处理，其他牌型为倍数关系
    },
    'hour_time':[
        (0.7,0,1),
        (0.6,1,6),
        (0.7,6,12),
        (0.8,12,14),
        (0.7,14,17),
        (0.8,17,19),
        (  1,19,21),
        (0.9,21,23),
        (0.8,23,24),
    ]
}

def get_hour_rate(change_rate):
    now = datetime.datetime.now()
    now_sec = now.hour * 3600 + now.minute * 60

    for rate, s, e in GAMECONF['hour_time']:
        start_sec = s * 3600
        end_sec = e * 3600
	
        if start_sec <= now_sec <= end_sec:
            return int(rate * change_rate)
        elif start_sec <= now_sec and e == 0:
            rate = rate * GAMECONF['hour_time'][-1][0]
        if rate < 0:
            return int(rate * 100)

def get_hour_rate1(change_rate):
    now = datetime.datetime.now()
    # now = datetime.datetime.strptime('2017-10-18 18:00:00', '%Y-%m-%d %H:%M:%S')
    now_sec = now.hour * 3600 + now.minute * 60
    cc = {}
    cc['hour_time'] = [
        (0.7,0,1),
        (0.6,1,6),
        (0.7,6,12),
        (0.8,12,14),
        (0.7,14,17),
        (0.8,17,19),
        (  1,19,21),
        (0.9,21,23),
        (0.8,23,0),
    ]
    for rate, s, e in GAMECONF['hour_time']:
        start_sec = s * 3600
        end_sec = e * 3600
    # s = 19
    # e = 21
    # start_sec = s * 3600
    # end_sec = e * 3600
    # rate = 0.8
        if start_sec < now_sec < end_sec:
            return int(rate * change_rate)
        elif start_sec < now_sec and e == 0:
            return int(rate * cc['hour_time'][-1][0])


def get_robots_not_online(r, robots_uid):
    all_onlines = set(r.hgetall('online')) | set(r.hgetall('war_online'))
    return robots_uid - all_onlines


def get_win_poker_type():

    pokers_rate = [constant_pb2.P_DAN] * 32 \
                  + [constant_pb2.P_DUI] * 24 \
                  + [constant_pb2.P_SHUN] * 19 \
                  + [constant_pb2.P_TONGHUA] * 16 \
                  + [constant_pb2.P_TONGHUASHUN] * 9

    random.shuffle(pokers_rate)
    return random.choice(pokers_rate)

def get_win_gold(bet_gold, poker_type, reward_gold_pool):
    if poker_type == constant_pb2.P_BAOZI:
        return int(GAMECONF['poker_multiple'][poker_type] * reward_gold_pool)
    else:
        return int(GAMECONF['poker_multiple'][poker_type] * bet_gold)

def make_bet(reward_gold_pool):
    baozi_gold = 0
    if reward_gold_pool > 800000000:
        baozi_gold = get_bet_num(get_hour_rate(80)) * 50000 + get_hour_rate(random.randint(5, 19)) * 2000
    elif 600000000 < reward_gold_pool < 800000000:
        baozi_gold = get_bet_num(get_hour_rate(60)) * 50000 +get_hour_rate( random.randint(3, 13)) * 2000
    elif 400000000 < reward_gold_pool < 600000000:
        baozi_gold = get_bet_num(get_hour_rate(40)) * 50000 +get_hour_rate( random.randint(2, 9)) * 2000
    elif 200000000 < reward_gold_pool < 400000000:
        baozi_gold = get_bet_num(get_hour_rate(30)) * 50000 +get_hour_rate( random.randint(1, 5)) * 2000
    elif 100000000 < reward_gold_pool < 200000000:
        baozi_gold = get_bet_num(get_hour_rate(20)) * 50000 + get_hour_rate( random.randint(1, 3)) * 2000
    elif reward_gold_pool < 100000000:
        baozi_gold = get_bet_num(get_hour_rate(10)) * 50000 + get_bet_num(get_hour_rate(90)) * 2000

    return {
        constant_pb2.P_DAN:get_bet_num(get_hour_rate(7)) * 5000000 + get_bet_num(get_hour_rate(25)) * 500000 + get_hour_rate(random.randint(19, 37)) * 50000 + get_hour_rate(random.randint(11, 24)) * 2000,
        constant_pb2.P_DUI:get_bet_num(get_hour_rate(6)) * 5000000 + get_bet_num(get_hour_rate(20)) * 500000 + get_hour_rate(random.randint(13, 31)) * 50000 + get_hour_rate(random.randint(11, 24)) * 2000,
        constant_pb2.P_SHUN:get_bet_num(get_hour_rate(5)) * 5000000 + get_bet_num(get_hour_rate(15)) * 500000 + get_hour_rate(random.randint(9, 23)) * 50000 + get_hour_rate(random.randint(11, 24)) * 2000,
        constant_pb2.P_TONGHUA:get_bet_num(get_hour_rate(4)) * 5000000 + get_bet_num(get_hour_rate(10)) * 500000 + get_hour_rate(random.randint(7, 15)) * 50000 + get_hour_rate(random.randint(11, 24)) * 2000,
        constant_pb2.P_TONGHUASHUN:get_bet_num(get_hour_rate(2)) * 5000000 + get_bet_num(get_hour_rate(5)) * 500000 + get_hour_rate(random.randint(5, 9))* 50000 + get_hour_rate(random.randint(11, 24)) * 2000,
        constant_pb2.P_BAOZI:baozi_gold
    }

def get_bet_num(yes_rate):
    no_rate = 100 - yes_rate
    rate = ([1] * yes_rate + [0] * no_rate)
    random.shuffle(rate)
    return random.choice(rate)


if __name__ == '__main__':
    pass
    # print get_hour_rate1(60)
    # print make_bet(500000000)
    # for x in range(10):
    #     print get_hour_rate(60)