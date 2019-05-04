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

tab_reward_code = Table("reward_code", metadata,
                    Column("id", Integer, primary_key=True),
                    Column("code", String(20)),
                    Column("type", SmallInteger),
                    Column("total",Integer),
                    Column("used",Integer),
                    Column("description",String(140)),
                    Column("gold",BigInteger),
                    Column("diamond",BigInteger),
                    Column("items",String(255)),
                    Column("expired_at", DateTime),
                    Column("create_time",DateTime),
                 )
                 


class TRewardCode(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'id=%d, code=%s' % (self.id, self.code)


mapper_reward_code = Mapper(TRewardCode,tab_reward_code)

if __name__=="__main__":
    pass