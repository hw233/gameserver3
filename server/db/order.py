# -*- coding: utf-8 -*-
__author__ = "liangxiaokai@21cn.com"
__version__ = "1.0"
__date__ = "2011/04/14"
__copyright__ = "Copyright (c) 2011"
__license__ = "Python"

from db.connect import *

from sqlalchemy import Table,Column,func
from sqlalchemy.types import  *
from sqlalchemy.orm import Mapper

tab_order = Table("order", metadata,
                 Column("id",Integer,primary_key=True),
                 Column("order_sn",String(20)),
                 Column("uid",Integer),
                 Column("sdk_order_sn",String(35)),
                 Column("money",DECIMAL(18,2) ),
                 Column("charge", DECIMAL(18,2)),
                 Column("shop_id", Integer),
                 Column("status", SMALLINT),
                 Column("comment", String(255)),
                 Column("create_time",DateTime)
                 )



class TOrder(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'id=%d,order_sn=%s,uid=%d' % (self.id,self.order_sn,self.uid)

mapper_order = Mapper(TOrder,tab_order)

if __name__=="__main__":
    pass