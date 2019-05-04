# -*- coding: utf-8 -*-
__author__ = 'Administrator'
import time

from sqlalchemy import and_

from db.rank_charge_top import *

class ChargeTop:

    @staticmethod
    def save_rank(session, user, gold,diamond, charge_money):
        rank_top = session.query(TRankChargeTop).filter(and_(TRankChargeTop.uid == user
                                                                      ,TRankChargeTop.add_date == time.strftime('%Y-%m-%d'))).first()
        if rank_top is None:
            top = TRankChargeTop()
            top.uid = user
            top.gold = gold
            top.diamond = diamond
            top.add_date = time.strftime('%Y-%m-%d')
            top.charge_money = charge_money
            session.add(top)
            session.flush()
        else:
            rank_top.gold += gold
            rank_top.diamond += diamond
            rank_top.charge_money += charge_money
            session.merge(rank_top)
            session.flush()

            # session.query(TRankChargeTop).filter(and_(TRankChargeTop.uid == user
            #                                                           ,TRankChargeTop.add_date == time.strftime('%Y-%m-%d'))).update({
            #     TRankChargeTop.gold: TRankChargeTop.gold + gold,
            #     TRankChargeTop.diamond: TRankChargeTop.diamond + diamond,
            #     TRankChargeTop.charge_money:TRankChargeTop.charge_money + charge_money
            # })