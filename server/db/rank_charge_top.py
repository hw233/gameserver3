#coding:utf-8

"""
���ݿ����ӹ���
"""

__author__ = "liangxiaokai@21cn.com"
__version__ = "1.0"
__date__ = "2011/04/14"
__copyright__ = "Copyright (c) 2011"
__license__ = "Python"

from db.connect import *

from sqlalchemy import Table,Column,func
from sqlalchemy.types import  *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

tab_rank_charge_top = Table("rank_charge_top", metadata,
                 Column("uid", Integer, primary_key=True),
                 Column("gold",BigInteger),
                 Column("diamond",BigInteger),
                 Column("add_date",Date, primary_key=True),
                 Column("charge_money", DECIMAL(18,2)),
                 Column("created_time",DateTime, default=func.now()),
                 )
                 

                 
class TRankChargeTop(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'uid=%d,gold=%d,add_date=%s,charge_money=%s' % (self.uid, self.gold, str(self.add_date), str(self.charge_money))
        
mapper_rank_charge_top = Mapper(TRankChargeTop,tab_rank_charge_top)

if __name__=="__main__":
    pass