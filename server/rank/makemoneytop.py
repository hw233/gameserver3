# -*- coding: utf-8 -*-
__author__ = 'Administrator'
import time

from sqlalchemy import and_

from db.rank_make_money_top import *

class MakeMoneyTop:

    @staticmethod
    def save_rank(session, user, win_gold):
        user_info = session.query(TRankMakeMoneyTop).filter(and_(TRankMakeMoneyTop.uid == user
                                                                      ,TRankMakeMoneyTop.add_year == time.strftime('%Y')
                                                                      ,TRankMakeMoneyTop.week_of_year == time.strftime('%W'))).first()
        if user_info is None:
            top = TRankMakeMoneyTop()
            top.uid = user
            top.gold = win_gold
            top.add_year = time.strftime('%Y')
            top.week_of_year = time.strftime('%W')
            session.add(top)
        else:
            session.query(TRankMakeMoneyTop).filter(and_(TRankMakeMoneyTop.uid == user
                                                                      ,TRankMakeMoneyTop.add_year == time.strftime('%Y')
                                                                      ,TRankMakeMoneyTop.week_of_year == time.strftime('%W'))).update({
                TRankMakeMoneyTop.gold: TRankMakeMoneyTop.gold + win_gold
            })