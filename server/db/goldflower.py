#coding:utf-8

"""
\u6570\u636E\u5E93\u8FDE\u63A5\u7BA1\u7406
"""

__author__ = "liangxiaokai@21cn.com"
__version__ = "1.0"
__date__ = "2011/04/14"
__copyright__ = "Copyright (c) 2011"
__license__ = "Python"

from db.connect import *

from sqlalchemy import Table,Column,func
from sqlalchemy.types import  *
from sqlalchemy.orm import Mapper

tab_goldflower = Table("goldflower", metadata,
                    Column("id",Integer, primary_key=True),
                    Column("type",Integer),
                    Column("countof_gamblers",SmallInteger), # 玩家数量
                    Column("winner",Integer,default=-1),
                    Column("gold",BigInteger,default=0),
                    Column("fee",BigInteger,default=0),
                    Column("create_time", DateTime),
                 )
                 

                 
class TGoldFlower(TableObject):
    def __init__(self):
        TableObject.__init__(self)
    
mapper_goldflower = Mapper(TGoldFlower,tab_goldflower)

if __name__=="__main__":
    pass