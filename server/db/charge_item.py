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

tab_charge_item = Table("charge_item", metadata,
                 Column("id",Integer, primary_key=True),
                 Column("diamond",Integer,default=0,nullable =False),
                 Column("type",String(10)),
                 Column("gold",Integer),
                 Column("icon",String(20)),
                 Column("name",String(20)),
                 Column("money",DECIMAL(18, 2)),
                 Column("real_money",DECIMAL(18, 2)),
                 Column("description",String(140),nullable =False),
                 Column("extra_diamond",Integer,default=0),
                 Column("extra_items",String(100),default=""), # 赠送道具列表,格式如下:"item_id-count,item_id-count....."
                 Column("create_time", DateTime,nullable =False),
                 )
                 

                 
class TChargeItem(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'id=%d,diamond=%d,descript=%s,money=%s,real_money=%s' % (self.id,self.diamond,self.description,self.money,self.real_money)
    
mapper_charge_item = Mapper(TChargeItem,tab_charge_item)

if __name__=="__main__":
    pass