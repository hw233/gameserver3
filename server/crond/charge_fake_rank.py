# -*- coding: utf-8 -*-
import redis

__author__ = 'Administrator'
import sys
import os
import random
import time

import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.connect import *
from db.rank_charge_top import *
from db.user import *
from sqlalchemy import func,and_

from hall.messagemanager import *
from config.var import *
from helper import datehelper

session = Session()
r = redis.Redis(**CROND_REDIS)

def get_random_user_id():
    limit_user = random.randint(1,10)
    ids = session.query(TUser.id).filter(and_(TUser.id >= 11253,TUser.id <= 22510)).all()
    ids = session.query(TUser.id).filter(and_(TUser.id >= 23000,TUser.id <= 24387)).all()
    ids = session.query(TUser.id).filter(and_(TUser.id >= 25000,TUser.id <= 25714)).all()
    ids += session.query(TUser.id).filter(and_(TUser.id >= 30000,TUser.id <= 31400)).all()
    ids += session.query(TUser.id).filter(and_(TUser.id >= 35800,TUser.id <= 36000)).all()
    id_lis = [sid[0] for sid in ids]
    random.shuffle(id_lis)

    random_user_id = []
    for uid in id_lis:
        if not r.hexists('war_online', uid):
            random_user_id.append(uid)
            if len(random_user_id) >= limit_user:
                return random_user_id

def weight_choice(weight):
    """
    根据概率分布
    :param weight: list对应的权重序列
    :return:选取的值在原列表里的索引
    """
    t = random.randint(0, sum(weight) - 1)
    for i, val in enumerate(weight):
        t -= val
        if t < 0:
            return i

'''
每小时随机生成1~3条充值数据。已充值过的id，叠加充值金额。
id区间：11253-22510，请注意id非连续
充值金额，18% 充值3元，15%充值5元， 12%充值6元，10%充值9元，10%充值10元, 10%充值12元，10%充值15元，8%充值20元，5%充值50元，2%充值100元。
充值排序，同样的金额，先充值的排在前面
[18,15,12,10,10,10,10,8,5,2]
[3,5,6,9,10,12,15,20,50,100]
'''

CHARGE_MONEY_RATE = [10,20,15,5,6,4,10,8,2,6,2,1,4,3,2,1,1]
CHARGE_MONEY_LIST = [5,3,9,10,14,15,16,11,20,21,25,32,46,39,89,169,190]

if __name__ == '__main__':
    user_ids = get_random_user_id()
    session.begin()
    for user_id in user_ids:
        charge_money = CHARGE_MONEY_LIST[weight_choice(CHARGE_MONEY_RATE)]
        session.execute("INSERT INTO `rank_charge_top`(add_date,uid,gold,charge_money,diamond,created_time) VALUES (:add_date,:uid,:gold,:charge_money,:diamond,:created_time)"
                        " ON DUPLICATE KEY UPDATE charge_money = charge_money + :charge_money", {
            'charge_money':charge_money,
            'add_date':datehelper.get_date_str(),
            'uid':user_id,
            'gold':-1,
            'diamond':-1,
            'created_time':datehelper.get_today_str()
        })
        session.execute("UPDATE `user` SET vip_exp = vip_exp + :vip_exp,money = money + :money WHERE id = :id",{
            'vip_exp':charge_money,
            'id':user_id,
            'money':charge_money,
        })
    session.commit()
