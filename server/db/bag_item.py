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

tab_bag_item = Table("bag_item", metadata,
                 Column("uid",Integer,primary_key=True),
                 Column("item_id",Integer,primary_key=True),
                 Column("countof", Integer,nullable =False),
                 )
                 

                 
class TBagItem(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'uid=%d,item_id=%d,countof=%d' % (self.uid,self.item_id,self.countof)
    
mapper_bag_item = Mapper(TBagItem,tab_bag_item)

if __name__=="__main__":
    pass