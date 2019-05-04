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

tab_shop_item = Table("shop_item", metadata,
                 Column("id",Integer, primary_key=True),
                 Column("type",SmallInteger),
                 Column("shop_gold",BigInteger),
                 Column("item_id",Integer),
                 Column("countof",Integer),
                 Column("diamond",BigInteger,default=0),
                 Column("gold",BigInteger,default=0),
                 Column("extra_gold",BigInteger,default=0),
                 Column("extra_items",String(100),default=""), # 赠送道具列表,格式如下:"(item_id,count),(item_id,count)....."
                 Column("create_time", DateTime),
                 )
                 

                 
class TShopItem(TableObject):
    def __init__(self):
        TableObject.__init__(self)
    def __repr__(self):
        return 'id=%d,type=%d,shop_gold=%d,item_id=%d,diamond=%d,gold=%d,extra_gold=%d,extra_items=%s' % \
               (self.id,self.type,self.shop_gold,self.item_id,self.diamond,self.gold,self.extra_gold,self.extra_items)
    
mapper_shop_item = Mapper(TShopItem,tab_shop_item)

if __name__=="__main__":
    pass