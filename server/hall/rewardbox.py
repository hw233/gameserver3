# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import random
import json

import os
import sys

sys.path.append( os.path.dirname(os.path.dirname(__file__)) )


from message.base import *
from proto.reward_pb2 import *
FAKE_GOLD_MIN = 400000
BOX_GOLD_MIN = (480000,540000)
BOX_GOLD_MAX = (540000,1000000)
BOX_MONEY = 1200
BOX_EXPIRE = 180
BOX_ID = 1001
BOX_CONFIG = {
    1001:{'BOX_ID':1001,'REAL_MONEY':1,'BOX_MONEY':1200,'FAKE_GOLD_MIN':400000,'BOX_GOLD_MIN':(480000,540000,),'BOX_GOLD_MAX':(540000,1000000,)},
    1002:{'BOX_ID':1002,'REAL_MONEY':1,'BOX_MONEY':1100,'FAKE_GOLD_MIN':350000,'BOX_GOLD_MIN':(420000,480000,),'BOX_GOLD_MAX':(480000,900000,)},
    1003:{'BOX_ID':1003,'REAL_MONEY':1,'BOX_MONEY':1000,'FAKE_GOLD_MIN':300000,'BOX_GOLD_MIN':(360000,410000,),'BOX_GOLD_MAX':(410000,800000,)},
    1004:{'BOX_ID':1004,'REAL_MONEY':1,'BOX_MONEY':900,'FAKE_GOLD_MIN':250000,'BOX_GOLD_MIN':(300000,370000,),'BOX_GOLD_MAX':(370000,700000,)},
    1005:{'BOX_ID':1005,'REAL_MONEY':1,'BOX_MONEY':800,'FAKE_GOLD_MIN':200000,'BOX_GOLD_MIN':(250000,320000,),'BOX_GOLD_MAX':(320000,600000,)},
}

class RewardBox:
    def __init__(self, service, redis_connect):
        self.service = service
        self.r = redis_connect

    def create_reward_box(self, uid):
        # if self.is_reward():
        #     return False

        conf = self.choice_conf()
        reward_gold = self.get_gold(conf)

        box = {u'box_id':conf['BOX_ID'],u'uid':uid, u'gold':reward_gold, u'diamond':0, u'money':conf['BOX_MONEY'], u'real_money':conf['REAL_MONEY'], u'name':u'神秘宝箱'}
        self.r.set('reward_box_'+str(uid), json.dumps(box))
        self.r.expire('reward_box_'+str(uid), BOX_EXPIRE)

        self.create_box_event(box, conf)

    def create_box_event(self, box, conf):
        event = create_client_event(RewardBoxEvent)
        event.body.box_id = conf['BOX_ID']
        event.body.max_gold = conf['BOX_GOLD_MAX'][-1]
        event.body.max_diamond = -1
        event.body.min_gold = conf['FAKE_GOLD_MIN']
        event.body.min_diamond = -1
        event.body.need_money = box['money']
        event_data = event.encode()

        access_service = self.service.redis.hget("online",box['uid'])
        if access_service == None:
            return
        access_service = int(access_service)
        user = int(box['uid'])
        self.service.send_client_event(access_service,user,event.header.command,event_data)

    def choice_conf(self):
        conf_index = random.randint(1, 100)
        if 1 <= conf_index <= 20:
            return BOX_CONFIG[1001]
        elif 21 <= conf_index <= 40:
            return BOX_CONFIG[1002]
        elif 41 <= conf_index <= 60:
            return BOX_CONFIG[1003]
        elif 61 <= conf_index <= 80:
            return BOX_CONFIG[1004]
        else:
            return BOX_CONFIG[1005]

    def get_gold(self, conf):
        GOLD_RANGE = [conf['BOX_GOLD_MIN'] for _ in range(65)] + [conf['BOX_GOLD_MAX'] for _ in range(35)]
        box_gold = random.randint(*random.choice(GOLD_RANGE))
        return box_gold

def reward_box(serivce, r, uid):
    r_box = RewardBox(serivce, r)
    if random.randint(1, 100) > 95:
        r_box.create_reward_box(uid)

def war_reward_box(service, r, uid):
    r_box = RewardBox(service, r)
    if random.randint(1, 100) < 50:
        r_box.create_reward_box(uid)

def texas_reward_box(service, r, uid):
    r_box = RewardBox(service, r)
    if random.randint(1, 100) < 50:
        r_box.create_reward_box(uid)

def ss(*aaa):
    pass
if __name__ == '__main__':
    import redis
    class S: pass
    s = S()
    s.redis = r = redis.Redis(password='Wgc@123456', host='10.0.1.16')

    s.send_client_event = ss
    RewardBox(s, r).create_reward_box(9999)