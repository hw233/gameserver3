# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import sys
import os
import time
import redis
import decimal
import traceback
from sqlalchemy.sql import select, update, delete, insert, and_, subquery, not_, null, func, text, exists, desc,asc

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.rank import *
from db.connect import *
from db.rank_charge_top import *
from db.user import *
from db.rank_make_money_top import *
from db.rank_war_top import *
from db.war_log import *
from db.rank_texas_top import *
from helper import datehelper
from hall.hallobject import *
from hall.messagemanager import *

RANK_REWARD = {
    # 金币，钻石，vip经验，[(道具1,数量),(道具2,数量),]
    'rank_charge_top': (10000, 1000, 1000, [(1, 12), (2, 24)],),
    'rank_gold_top': (10000, 1000, 1000, [(1, 12), (2, 24)],),
    'rank_make_money_top': (10000, 1000, 1000, [(1, 12), (2, 24)],),
}
CHARGE_REWARD = (3,2,1,0.7,0.5,0.5,0.4,0.4,0.3,0.3,)
DIAMOND_RATE = 3

MAKE_MONEY_REWARD = (300,200,100,70,50,50,40,40,30,30,)

TEXAS_REWARD = (300,200,100,70,50,50,40,40,30,30)
DAILY_KEY = 'DailyTasks'
session = Session()


class CrondServer:
    def __init__(self):
        self.redis = redis.Redis(**CROND_REDIS)

    def remove_daily_task(self):
        self.redis.delete(DAILY_KEY)

    def reward_charge_top(self):
        charge_users = self.load_rank_charge_top()

        for index, charge_user in enumerate(charge_users):
            reward_diamond = int(float(charge_user[0].charge_money) * float(CHARGE_REWARD[index]) * DIAMOND_RATE)
            if reward_diamond <= 0:
                continue
            MessageManager.send_mail(session, charge_user[1].id, 0,
                title = u'充值榜奖励',
                content = RANK_CHARGE_MAIL % (datehelper.get_yesterday().strftime('%Y-%m-%d'), index + 1, reward_diamond),
                type = 1,
                diamond = reward_diamond,
                gold = 0,
                items = '',)

        session.flush()
    def get_reward_users(self):
        top_users = session.query(TRankWarTop, TUser).join(TUser, TRankWarTop.uid == TUser.id) \
                    .filter(TRankWarTop.add_date == datehelper.get_yesterday()).order_by(desc(TRankWarTop.total)) \
                    .limit(RANK_WAR_TOP).all()
        return top_users

    def minus_reward_pool(self, reward_top_gold,last_game_log):
        session.query(TWarLog).filter(TWarLog.id == last_game_log.id).update({
            TWarLog.reward_pool:TWarLog.reward_pool - reward_top_gold
        })

    def reward_war_top(self):
        # top_users = session.query(TRankWarTop, TUser).join(TUser, TRankWarTop.uid == TUser.id) \
        #             .filter(TRankWarTop.add_date == datehelper.get_yesterday()).order_by(desc(TRankWarTop.total)) \
        #             .limit(RANK_WAR_TOP).all()
        top_users = self.get_reward_users()

        reward_pool = self.redis.hget('war_game', 'reward_pool')
        if reward_pool <= 0:
            return
        reward_top_gold = int(reward_pool) * 0.5
	# print top_users[0][0]
        win_gold_total = sum([x[0].total for x in top_users])
        for index, user in enumerate(top_users):
            win_gold_rate = float(user[0].total) / float(win_gold_total)
            award_gold = int(reward_top_gold * win_gold_rate)
            MessageManager.send_mail(session, user[0].uid, 0,
                title = u'红黑赢利榜',
                content = RANK_WAR_MAIL % (datehelper.get_yesterday().strftime('%Y-%m-%d'), index + 1, award_gold),
                type = 1,
                diamond = 0,
                gold = award_gold,
                items = '',)
	    session.flush()
        self.redis.hset('war_game', 'reward_pool', int(reward_pool) - int(reward_top_gold))





    def load_rank_charge_top(self):
        return session.query(TRankChargeTop, TUser).join(TUser, TRankChargeTop.uid == TUser.id) \
            .filter(TRankChargeTop.add_date == datehelper.get_yesterday()) \
            .order_by(desc(TRankChargeTop.charge_money),asc(TRankChargeTop.created_time)) \
            .limit(RANK_CHARGE_REWARD).all()

    def reward_make_money_top(self):
        make_money_users = self.load_make_money_top()

        for index, make_money_users in enumerate(make_money_users):
            print make_money_users[0].gold,make_money_users[1].id,index
            print MAKE_MONEY_REWARD[index]

            reward_diamond = MAKE_MONEY_REWARD[index]
            MessageManager.send_mail(session, make_money_users[1].id, 0,
                title = u'周赚金榜奖励',
                content = u'恭喜你在第 %s 周赚金排行中，获得第%d名的好成绩，获得如下奖励:%d个钻石'
                          % (datehelper.get_last_week().strftime('%W'), index + 1, reward_diamond),
                type = 1,
                diamond = reward_diamond,
                gold = 0,
                items = '',)

        session.flush()

    def load_make_money_top(self):
        return session.query(TRankMakeMoneyTop, TUser).join(TUser, TRankMakeMoneyTop.uid == TUser.id)\
            .filter(and_(TRankMakeMoneyTop.add_year == datehelper.get_last_week().strftime('%Y'),TRankMakeMoneyTop.week_of_year == datehelper.get_last_week().strftime('%W')) )\
            .order_by(desc(TRankMakeMoneyTop.gold))\
            .limit(10).all()


    def reload_gold_top(self):
        self.redis.delete('rank_gold')
        users = self.get_gold_top()
        pipe = self.redis.pipeline()
        for index, user in enumerate(users):
            pipe.zadd('rank_gold', user.id, index + 1)
        pipe.execute()

    def get_gold_top(self):
        return session.query(TUser.id).order_by(TUser.gold.desc()).limit(RANK_GOLD_TOP).all()

    def reload_charge_top(self):
        self.redis.delete('rank_charge')
        users = self.get_charge_top()
        pipe = self.redis.pipeline()
        for index, user in enumerate(users):
            pipe.zadd('rank_charge', user[0], index + 1)
        pipe.execute()

    def get_charge_top(self):
        return session.query(TUser.id).join(TRankChargeTop, TRankChargeTop.uid == TUser.id) \
            .filter(TRankChargeTop.add_date == datehelper.get_datetime().strftime('%Y-%m-%d')) \
            .order_by(TRankChargeTop.charge_money.desc(), TRankChargeTop.created_time.desc()) \
            .limit(RANK_CHARGE_TOP_INDEX).all()

    def reload_make_money_top(self):
        self.redis.delete('rank_make_money')
        users = self.get_make_money_top()
        pipe = self.redis.pipeline()
        for index, user in enumerate(users):
            pipe.zadd('rank_make_money', user[0], index + 1)
        pipe.execute()

    def get_make_money_top(self):
        return session.query(TUser.id).join(TRankMakeMoneyTop, TRankMakeMoneyTop.uid == TUser.id) \
            .filter(and_(TRankMakeMoneyTop.add_year == datehelper.get_datetime().strftime('%Y'),TRankMakeMoneyTop.week_of_year == datehelper.get_datetime().strftime('%W')) ) \
            .order_by(TRankMakeMoneyTop.gold.desc(),TRankMakeMoneyTop.created_time.desc()) \
            .limit(RANK_MAKE_MONEY_TOP_INDEX).all()

    def reward_texas(self):
        rank_texas_users = self.get_texas_users()
        if not rank_texas_users:
            return

        for index,texas_user in enumerate(rank_texas_users):
            reward_diamond = TEXAS_REWARD[index]

            MessageManager.send_mail(session, texas_user[1].id, 0,
                title = u'德州赚金榜',
                content = RANK_TEXAS_MAIL % (datehelper.get_yesterday().strftime('%Y-%m-%d'), index + 1, reward_diamond),
                type = 1,
                diamond = reward_diamond,
                gold = 0,
                items = '',)

        session.flush()

    def get_texas_users(self):
        top_users = session.query(TRankTexasTop, TUser).join(TUser, TRankTexasTop.uid == TUser.id) \
                    .filter(TRankTexasTop.add_date == datehelper.get_yesterday()).order_by(desc(TRankTexasTop.total)) \
                    .limit(RANK_TEXAS_TOP).all()
        return top_users

if __name__ == '__main__':
    cs = CrondServer()
    funcs = {
        'reload_gold_top':cs.reload_gold_top,   # 每小时刷新
        'reload_charge_top':cs.reload_charge_top,  # 每小时刷新
        'reload_make_money_top':cs.reload_make_money_top, # 每周刷新
        'remove_daily_task':cs.remove_daily_task, # 每日删除
        'reward_charge_top':cs.reward_charge_top, # 每日刷新
        'reward_war_top':cs.reward_war_top, # 每日刷新
        'reward_make_money_top':cs.reward_make_money_top, # 每周奖励
        'reward_texas':cs.reward_texas, # 每日德州
    }

    funcs[sys.argv[1]]()


    # if sys.argv[1] == 'load_rank_gold':
    #     CrondServer().reload_gold_top()
    # elif sys.argv[1] == 'remove_daily_task':
    #     CrondServer().remove_daily_task()
    # elif sys.argv[1] == 'reward_charge_top':
    #     CrondServer().reward_charge_top()
    # elif sys.argv[1] == 'reward_make_money_top':
    #     CrondServer().reward_make_money_top()

        # crond = CrondServer()
        # if len(sys.argv) > 3:
        #     func_name = sys.argv[1]
        #     param_name = sys.argv[2]
        #     getattr(crond, func_name)(param_name)
        # else:
        #     func_name = sys.argv[1]
        #     getattr(crond, func_name)()


        # python -m crond.rank run rank_charge_top
        # python -m crond.rank run rank_make_money_top
        # python -m crond.rank remove_daily_task
        # python -m crond.rank reload_gold_top
