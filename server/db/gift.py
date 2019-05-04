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

tab_gift = Table("gift", metadata,
                 Column("id",Integer, primary_key=True),
                 Column("icon",String(100)),
                 Column("name",String(20)),
                 Column("description",String(140)),
                 Column("gold",BigInteger),
                 Column("create_time", DateTime),
                 )

                 
class TGift(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    # def __repr__(self):
    #     return "id=%id,icon=%s,name=%s,description=%s,gold=%d" % \
    #            (self.id,self.icon,self.name,self.description,self.gold)
    
mapper_gift = Mapper(TGift,tab_gift)

if __name__=="__main__":
    pass