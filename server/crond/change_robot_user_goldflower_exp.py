# -*- coding: utf-8 -*-
__author__ = 'Administrator'
import sys
import os
import random
import time
import redis
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.var import *
from dal.core import *
from dal.user import *
from db.connect import *
from db.rank_charge_top import *
from db.user import *
from db.user_goldflower import *
from sqlalchemy import func,and_

from hall.messagemanager import *
from helper import datehelper

ROBOT_ID_GROUP = [
    (18169,22499,),
    (14159,15130,)
]

session = Session()
r = redis.Redis(**CROND_REDIS)
da = DataAccess(r)

def update_robot_user_goldflower_exp(user, exp):
    ugf = DalUserGoldFlower(da, user)
    print 'before: %s , after: %s' % (ugf.exp, exp)
    ugf.exp = exp
    ugf.save(session)
    session.query(TUserGoldFlower).filter(TUserGoldFlower.id == user).update({
        TUserGoldFlower.exp : exp
    })

def get_user_goldflower_ids(start, end):
    ids = session.query(TUserGoldFlower.id).filter(and_(TUserGoldFlower.id <= start, TUserGoldFlower.id >= end)).all()
    return [s[0] for s in ids]

def get_random_exp():
    return random.randint(10, 250)
'''
每天凌晨2点
18169-22499内的id 玩家user_goldflower内exp随机设置为10~250
14159-15130内的id 的玩家user_goldflower内exp随机设置为10~250

请注意ID非连续。
'''

if __name__ == '__main__':
    group_ids = get_user_goldflower_ids(ROBOT_ID_GROUP[0][0], ROBOT_ID_GROUP[0][1])
    group_ids += get_user_goldflower_ids(ROBOT_ID_GROUP[1][0], ROBOT_ID_GROUP[1][1])

    for gid in group_ids:
        exp = get_random_exp()
        update_robot_user_goldflower_exp(gid, exp)
        print 'gid: %s ,exp: %d' % (gid, exp)

    print 'done....'
