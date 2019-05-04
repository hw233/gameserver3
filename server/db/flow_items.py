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

tab_flow_items = Table("flow_items", metadata,
                 Column("id",Integer, primary_key=True),
                 Column("icon",Integer),
                 Column("name",String(255)),
                 Column("sn",Integer),
                 Column("sn_name",String(255)),
                 Column("GSM",String(20)),
                 Column("description",String(140)),
                 Column("card",Integer),
                 Column("stack",Integer),
                 Column("used",Integer),
                 Column("create_time", DateTime),
                 Column("sort", Integer),
                 )
                 

                 
class TFlowItems(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'id=%d,name=%s' % (self.id, self.name)
    
mapper_flow_items = Mapper(TFlowItems,tab_flow_items)

if __name__=="__main__":
    pass