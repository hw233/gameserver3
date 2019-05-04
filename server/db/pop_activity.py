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

tab_pop_activity = Table("pop_activity", metadata,
                 Column("id",Integer, primary_key=True),
                 Column("title",String(50)),
                 Column("description",String(255)),
                 Column("gold",Integer),
                 Column("money",DECIMAL(10,2)),
                 Column("start", DateTime),
                 Column("end", DateTime),
                 Column("status",Integer),
                 )

                 
class TPopActivity(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    # def __repr__(self):
    #     return "id=%id,icon=%s,name=%s,description=%s,gold=%d" % \
    #            (self.id,self.icon,self.name,self.description,self.gold)
    
mapper_pop_activity = Mapper(TPopActivity,tab_pop_activity)

if __name__=="__main__":
    pass