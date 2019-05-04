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

tab_war_poker_path = Table("war_poker_path", metadata,
                    Column("id", Integer, primary_key=True),
                    Column("winner",SMALLINT),
                    Column("continuous",SMALLINT),

                 )



class TWarPokerPath(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'id=%d,winner=%d,continuous=%d' % (self.id, self.winner, self.continuous)


mapper_war_poker_path = Mapper(TWarPokerPath,tab_war_poker_path)

if __name__=="__main__":
    pass