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

tab_war_player_brief = Table("war_player_brief", metadata,
                    Column("uid", Integer, primary_key=True),
                    Column("total_games",Integer),
                    Column("max_win_gold",Integer),

                 )



class TWarPlayerBrief(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'uid=%d,total_games=%d,max_win_gold=%d' % (self.uid, self.total_games, self.max_win_gold)


mapper_war_player_brief = Mapper(TWarPlayerBrief,tab_war_player_brief)

if __name__=="__main__":
    pass