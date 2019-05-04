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

tab_bag_gift = Table("bag_gift", metadata,
                 Column("uid",Integer,primary_key=True),
                 Column("gift_id",Integer,primary_key=True),
                 Column("countof", Integer,nullable =False),
                 )
                 

                 
class TBagGift(TableObject):
    def __init__(self):
        TableObject.__init__(self)
    
mapper_bag_gift = Mapper(TBagGift,tab_bag_gift)

if __name__=="__main__":
    pass