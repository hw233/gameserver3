#coding:utf-8

"""
���ݿ����ӹ���
"""

__author__ = "liangxiaokai@21cn.com"
__version__ = "1.0"
__date__ = "2011/04/14"
__copyright__ = "Copyright (c) 2011"
__license__ = "Python"

from connect import *

from sqlalchemy import Table,Column,func
from sqlalchemy.types import  *
from sqlalchemy.ext.declarative import declarative_base

tab_war_log = Table("war_log", metadata,
                    Column("id", Integer, primary_key=True),
                    Column("red_poker",VARCHAR(20)),
                    Column("black_poker",VARCHAR(20)),
                    Column("winner",Integer),
                    Column("winner_poker_type",Integer),
                    Column("lucky_rate",SMALLINT),
                    Column("lucky_rate",),
                    Column("red_total",BigInteger),
                    Column("black_total",BigInteger),
                    Column("lucky_total",BigInteger),
                    Column("result_gold",Integer),

                    Column("reward_pool",BigInteger),
                    Column("lucky_stack",BigInteger),
                    Column("total_award",BigInteger),
                    Column("award_winners",Integer),

                    Column("rich",VARCHAR(255)),
                    Column("star",Integer),
                    Column("create_time",DATETIME),
                 )



class TWarLog(TableObject):
    def __init__(self):
        TableObject.__init__(self)


mapper_war_log = Mapper(TWarLog,tab_war_log)

if __name__=="__main__":
    pass