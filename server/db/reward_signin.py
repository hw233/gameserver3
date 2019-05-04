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

tab_reward_signin = Table("reward_signin", metadata,
                    Column("day", Integer, primary_key=True),
                    Column("description",String(140)),
                    Column("gold",Integer,default=0),
                    Column("diamond",Integer,default=1),
                    Column("items",String(255)),
                    Column("gifts",String(255)),
                 )
                 


class TRewardSignin(TableObject):
    def __init__(self):
        TableObject.__init__(self)
    def __repr__(self):
        return 'day=%d,description=%s,gold=%d,diamond=%d' % \
               (self.day,self.description,self.gold,self.diamond)

mapper_reward_signin = Mapper(TRewardSignin,tab_reward_signin)

if __name__=="__main__":
    pass