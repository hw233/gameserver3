# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import time

from proto.bank_pb2 import *
from proto.constant_pb2 import *

from sqlalchemy import and_,desc

from db.rank_charge_top import *
from db.rank_make_money_top import *
from db.user import *
from db.rank_war_top import *
from db.rank_lottery_top import *
from db.rank_texas_top import *

from helper import datehelper
from helper import protohelper

from config.var import *
from config.rank import *


from hall.messagemanager import *


class Rank:

    # 财富榜人物上线，广播
    @staticmethod
    def gold_top_online_broadcast(redis_conn, session, user):
        user_info = session.query(TUser.id,TUser.nick,TUser.vip_exp).filter(TUser.id == user).first()

        rank = -1
        user_infos = session.query(TUser.id).order_by(desc(TUser.gold)).limit(RANK_CHARGE_TOP).all()

        for index,rank_user in enumerate(user_infos):
            if rank_user[0] == user_info.id:
                rank = index+1
                break

        if rank == -1:
            return
        count = RANK_WEALTH_TOP

        MessageManager.push_message(redis_conn, redis_conn.redis.hkeys('online'),PUSH_TYPE['rank_top'],{
            'uid':user_info.id,
            'nick':user_info.nick,
            'vip_exp':user_info.vip_exp,
            'index':rank,
            'count':count,
            'top_type':1
        })


    @staticmethod
    def charge_top_change(session, ):
        pass

    def __init__(self, service):
        self.service = service
        self.rank_type_map = {
            1: self.wealth_top,
            2: self.charge_top,
            4: self.make_money_top,
        }

    def wealth_top(self, session, rank_time):
        top = []

        uids = self.service.redis.zrange('rank_gold',0,ZRANK_GOLD_TOP)
        users = []
        for uid in uids:
            users.append(self.service.da.get_user(uid))
        for user in users:
            top.append(self.pack_top(uid=user.id,nick=user.nick,avatar=user.avatar,gold=user.gold, vip=user.vip,vip_exp=user.vip_exp, sex=user.sex))
        return top

    def pack_top(self, **kwargs):
        return {
            'uid':kwargs['uid'],
            'nick':kwargs['nick'],
            'avatar':kwargs['avatar'],
            'gold':kwargs['gold'],
            'vip':kwargs['vip'],
            'rank_reward':kwargs.get('rank_reward', ''),
            'money_maked':kwargs.get('money_maked',0),
            'charm':0,
            'vip_exp':kwargs['vip_exp'],
            'charge':kwargs.get('charge', 0),
            'war_win':kwargs.get('war_win', 0),
            'lottery_gold':kwargs.get('lottery_gold', 0),
            'lottery_create_time':kwargs.get('lottery_create_time', 0),
            'texas_gold':kwargs.get('texas_gold', 0),
            'sex':kwargs.get('sex', 0),
        }

    def charge_top(self,session, rank_time, by_index = False):
        query = session.query(TRankChargeTop, TUser).join(TUser, TRankChargeTop.uid == TUser.id)
        if rank_time == RANK_YESTERDAY:
            query = query.filter(TRankChargeTop.add_date == datehelper.get_yesterday())
        elif rank_time == RANK_TODAY:
            query = query.filter(TRankChargeTop.add_date == datehelper.get_datetime().strftime('%Y-%m-%d'))
        items = query.order_by(TRankChargeTop.charge_money.desc(), TRankChargeTop.created_time.asc()).limit(50).all()

        if by_index:
            return items

        top = []
        for item in items:
            charge_top, user = item

            top.append(self.pack_top(uid=user.id,
                                     nick=user.nick,
                                     avatar=user.avatar,
                                     gold=user.gold,
                                     vip=user.vip,
                                     vip_exp=user.vip_exp,
                                     charge=int(charge_top.charge_money * 100),
                                     sex=user.sex))

        if RANK_FAKE_CHARGE_ENABLE:
            top = self.merage_fake(top, RANK_FAKE_CHARGE)

        return top

    def make_money_top(self,session, rank_time):
        query = session.query(TRankMakeMoneyTop, TUser).join(TUser, TRankMakeMoneyTop.uid == TUser.id)
        if rank_time == RANK_LAST_WEEK:
            query = query.filter(and_(TRankMakeMoneyTop.add_year == datehelper.get_last_week().strftime('%Y'),TRankMakeMoneyTop.week_of_year == datehelper.get_last_week().strftime('%W')) )
        elif rank_time == RANK_THIS_WEEK:
            query = query.filter(and_(TRankMakeMoneyTop.add_year == datehelper.get_datetime().strftime('%Y'),TRankMakeMoneyTop.week_of_year == datehelper.get_datetime().strftime('%W')) )
        items = query.order_by(TRankMakeMoneyTop.gold.desc(),TRankMakeMoneyTop.created_time.desc()).limit(50).all()

        top = []
        for item in items:
            make_money, user = item
            top.append(self.pack_top(uid=user.id,nick=user.nick,avatar=user.avatar,gold=user.gold,money_maked=make_money.gold, vip=user.vip, vip_exp=user.vip_exp,sex=user.sex))


        if RANK_FAKE_MAKE_MONEYD_ENABLE:
            top = self.merage_fake(top, RANK_FAKE_MAKE_MONEYD)

        return top

    def war_top(self, session, rank_time):
        query = session.query(TRankWarTop, TUser).join(TUser, TRankWarTop.uid == TUser.id)
        if rank_time == RANK_YESTERDAY:
            query = query.filter(TRankWarTop.add_date == datehelper.get_yesterday())
        elif rank_time == RANK_TODAY:
            query = query.filter(TRankWarTop.add_date == datehelper.get_datetime().strftime('%Y-%m-%d'))
        items = query.order_by(TRankWarTop.total.desc(), TRankWarTop.created_time.asc()).limit(50).all()

        top = []
        for item in items:
            war_top, user = item

            top.append(self.pack_top(uid=user.id,
                                     nick=user.nick,
                                     avatar=user.avatar,
                                     gold=user.gold,
                                     vip=user.vip,
                                     vip_exp=user.vip_exp,
                                     war_win=war_top.total,
                                     sex=user.sex))
        return top

    def lottery_big_reward(self, session, rank_time):
        query = session.query(TRankLotteryTop, TUser).join(TUser, TRankLotteryTop.uid == TUser.id)
        if rank_time == RANK_YESTERDAY:
            query = query.filter(TRankLotteryTop.add_date == datehelper.get_yesterday())
        elif rank_time == RANK_TODAY:
            query = query.filter(TRankLotteryTop.add_date == datehelper.get_datetime().strftime('%Y-%m-%d'))
        items = query.order_by(TRankLotteryTop.total.desc(), TRankLotteryTop.created_time.asc()).limit(20).all()
        # print str(query)
        top = []
        for item in items:
            lottery_top, user = item

            top.append(self.pack_top(uid=user.id,
                                     nick=user.nick,
                                     avatar=user.avatar,
                                     gold=user.gold,
                                     vip=user.vip,
                                     vip_exp=user.vip_exp,
                                     lottery_gold=lottery_top.total,
                                     lottery_create_time=int(time.mktime(lottery_top.created_time.timetuple())),
                                     sex=user.sex))
        return top

    def texas_top_rank(self, session, rank_time):
        query = session.query(TRankTexasTop, TUser).join(TUser, TRankTexasTop.uid == TUser.id)
        if rank_time == RANK_YESTERDAY:
            query = query.filter(TRankTexasTop.add_date == datehelper.get_yesterday())
        elif rank_time == RANK_TODAY:
            query = query.filter(TRankTexasTop.add_date == datehelper.get_datetime().strftime('%Y-%m-%d'))
        items = query.order_by(TRankTexasTop.total.desc(), TRankTexasTop.created_time.asc()).limit(20).all()
        # print str(query)
        top = []
        for item in items:
            texas_top, user = item
            top.append(self.pack_top(uid=user.id,
                                     nick=user.nick,
                                     avatar=user.avatar,
                                     gold=user.gold,
                                     vip=user.vip,
                                     vip_exp=user.vip_exp,
                                     texas_gold=texas_top.total,
                                     sex=user.sex))
        return top

    def set_pb(self, resp, items):

        for index in range(len(items)):
            protohelper.set_top(resp.body.players.add(), items[index], index)


    def merage_fake(self, data, fake_data):
        if len(data) <= 0:
            data = fake_data
        else:
            for fake in fake_data:
                if len(data) >= RANK_FAKE_LEN:
                    break;
                data.append(fake)
        return data
    @staticmethod
    def add_charge_top(session,uid,nick,avatar,gold,vip):
        result = session.execute("INSERT INTO rank_charge_top(uid,nick,avatar,gold,add_date) VALUES (:uid,:nick,:avatar,:gold,:add_date)"
                        " ON DUPLICATE KEY UPDATE nick = :nick, avatar = :avatar, gold = gold + :gold", {
            'uid':uid,
            'nick':nick,
            'avatar':avatar,
            'gold':gold,
            'add_date':time.strftime('%Y-%m-%d'),
            'vip':vip,
        }).rowcount

    @staticmethod
    def add_make_money_top(session, uid, nick, avatar, gold, vip):
        result = session.execute("INSERT INTO rank_make_money_top(uid,nick,avatar,gold,add_year,week_of_year) VALUES (:uid,:nick,:avatar,:gold,:add_year,:week_of_year)"
                        " ON DUPLICATE KEY UPDATE nick = :nick, avatar = :avatar, gold = gold + :gold", {
            'uid':uid,
            'nick':nick,
            'avatar':avatar,
            'gold':gold,
            'add_year':time.strftime('%Y'),
            'week_of_year':time.strftime('%W'),
            'vip':vip,
        }).rowcount


class RankUpper:

    def __init__(self, session):
        self.session = session
        self.before_rank = None
        self.after_rank = None

        self.before_index = -1
        self.after_index = -1

        self.index = -1

    def get_old_index(self, uid):
        self.load_before_rank()
        self.find_index(self.before_rank, uid)
        self.before_index = self.index

    def get_new_index(self, uid):
        self.load_after_rank()
        self.find_index(self.after_rank, uid)
        self.after_index = self.index

    def is_up(self):
        if self.after_index < self.before_index:
            return True
        elif self.before_index == -1 and self.after_index > 0:
            return True

    def find_index(self, ranks, uid):
        for index, rank in enumerate(ranks):
            if rank[1].id == uid:
                self.index = index +1
                return
        self.index = -1


    def load_after_rank(self):
        self.after_rank = self.get_rank()

    def load_before_rank(self):
        self.before_rank = self.get_rank()

    def get_rank(self):
        return Rank(None).charge_top(self.session, RANK_TODAY, by_index=True)
        # session.query(TRankChargeTop, TUser).filter(TRankChargeTop.uid == TUser.id)
        # if rank_time == RANK_YESTERDAY:
        #     query = query.filter(TRankChargeTop.add_date == datehelper.get_yesterday())
        # elif rank_time == RANK_TODAY:
        #     query = query.filter(TRankChargeTop.add_date == datehelper.get_datetime().strftime('%Y-%m-%d'))
        # items = query.order_by(desc(TUser.gold)).limit(RANK_CHARGE_TOP).all()


if __name__ == '__main__':
    import sys
    sys.path.append('../')
    from db.connect import *
    session = Session()
    ru = RankUpper(session)
    # print ru.before_index
    # print ru.after_index



    ru.get_old_index(11247)
    # print ru.before_index
    # ru.get_new_index(11247)
    ru.get_new_index(11247)

    # print ru.after_index
