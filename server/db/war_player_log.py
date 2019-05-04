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

tab_war_player_log = Table("war_player_log", metadata,
                    Column("war_id", Integer, primary_key=True),
                    Column("uid",Integer, primary_key=True),
                    Column("bet_gold",BigInteger),
                    # Column("red_black_bet",BigInteger),
                    # Column("lucky_bet",BigInteger),
                    Column("win_gold",BigInteger),
                    # Column("red_black_bet_win",BigInteger),
                    # Column("lucky_bet_win",BigInteger),
                    # Column("real_win_gold",BigInteger),
                    Column("fee",BigInteger),
                    Column("gold",BigInteger),
                    Column("reward_gold",BigInteger),
                 )



class TWarPlayerLog(TableObject):
    def __init__(self):
        TableObject.__init__(self)


mapper_war_player_log = Mapper(TWarPlayerLog,tab_war_player_log)

if __name__=="__main__":
    pass