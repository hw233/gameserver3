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

tab_rank_war_top = Table("rank_war_top", metadata,
                    Column("add_date", Date, primary_key=True),
                    Column("uid",Integer, primary_key=True),
                    Column("total",BigInteger),
                    Column("created_time",DATETIME),
                 )



class TRankWarTop(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'add_date=%s,uid=%d,total=%d' % (str(self.add_date), self.uid, self.total)


mapper_rank_war_top = Mapper(TRankWarTop,tab_rank_war_top)

if __name__=="__main__":
    pass