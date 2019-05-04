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

tab_rank_make_money_top = Table("rank_make_money_top", metadata,
                 Column("uid", Integer, primary_key=True),
                 Column("gold",BigInteger),
                 Column("add_year",Integer, primary_key=True),
                 Column("week_of_year",SMALLINT, primary_key=True),
                 Column("created_time",DateTime, default=func.now()),
                 )
                 

                 
class TRankMakeMoneyTop(TableObject):
    def __init__(self):
        TableObject.__init__(self)
        
mapper_rank_make_money_top = Mapper(TRankMakeMoneyTop,tab_rank_make_money_top)

if __name__=="__main__":
    pass