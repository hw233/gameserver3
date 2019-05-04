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

tab_rank_gold_top = Table("rank_gold_top", metadata,
                 Column("uid", Integer, primary_key=True),
                 Column("nick",String(40)),
                 Column("avatar", String(255)),
                 Column("gold",BigInteger),
                 Column("create_time",DateTime),
                 Column("vip",SMALLINT),

                 )
                 

                 
class TRankGoldTop(TableObject):
    def __init__(self):
        TableObject.__init__(self)
        
mapper_rank_gold_top = Mapper(TRankGoldTop,tab_rank_gold_top)

if __name__=="__main__":
    pass