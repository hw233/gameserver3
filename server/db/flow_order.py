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

tab_flow_order = Table("flow_order", metadata,
                 Column("id",Integer, primary_key=True),
                 Column("flow_order_sn",String(20), unique=True),
                 Column("uid",Integer),
                 Column("phone",String(20)),
                 Column("flow_card",Integer),
                 Column("flow_item_id",Integer),
                 Column("flow_item_name",String(255)),
                 Column("status",SMALLINT),
                 Column("status_text",String(100)),
                 Column("comment",String(255)),
                 Column("callback_msg",String(255)),
                 Column("create_time", DateTime),
                 Column("callback_time", DateTime),
                 )



class TFlowOrder(TableObject):
    def __init__(self):
        TableObject.__init__(self)


    # def __repr__(self):
    #     return 'id=%d,flow_order_sn=%s,uid=%d,phone=%s,flow_card=%d,flow_item_id=%d,flow_item_name=%s' % (
    #         self.id,
    #         self.flow_order_sn,
    #         self.uid,
    #         self.phone,
    #         self.flow_card,
    #         self.flow_item_id,
    #         self.flow_item_name,
    #     )

mapper_flow_order = Mapper(TFlowOrder,tab_flow_order)

if __name__=="__main__":
    pass