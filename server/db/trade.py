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

tab_trade = Table("trade", metadata,
                 Column("id",Integer, primary_key=True),
                 Column("seller",Integer),
                 Column("gold",BigInteger),
                 Column("fee", Integer),
                 Column("diamond",BigInteger),
                 Column("sell_time", DateTime),
                 Column("buyer",Integer),
                 Column("buy_time",DateTime),
                 Column("status",SMALLINT),
                 Column("rate",DECIMAL(11,2)),
                 )
                 

                 
class TTrade(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'id=%d' % self.id
    
mapper_trade = Mapper(TTrade,tab_trade)

if __name__=="__main__":
    pass