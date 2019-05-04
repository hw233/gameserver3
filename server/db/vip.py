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

tab_vip = Table("vip", metadata,
                    Column("level", Integer, primary_key=True),
                    Column("description",String(140)),
                    Column("need_money",Integer),
                    Column("daily_gold",BigInteger),
                    Column("daily_diamond",BigInteger),
                    Column("gold",BigInteger),
                    Column("diamond",BigInteger),
                    Column("max_bank",BigInteger),
                    Column("max_friend",Integer),
                 )
                 


class TVip(TableObject):
    def __init__(self):
        TableObject.__init__(self)


mapper_vip = Mapper(TVip,tab_vip)

if __name__=="__main__":
    pass