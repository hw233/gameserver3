#coding:utf-8

"""
���ݿ����ӹ���
"""

__author__ = "liangxiaokai@21cn.com"
__version__ = "1.0"
__date__ = "2011/04/14"
__copyright__ = "Copyright (c) 2011"
__license__ = "Python"

from connect import *

from sqlalchemy import Table,Column,func
from sqlalchemy.types import  *
from sqlalchemy.orm import Mapper

#������
tab_timer = Table("timer", metadata,
                 Column("id", Integer, primary_key=True),
                 Column("uid", Integer),
                 Column("object_id", BigInteger),
                 Column("object_type", SmallInteger),
                 Column("event_id", Integer),
                 Column("expired", Integer),
                 Column("param0", BigInteger),                 
                 Column("param1", BigInteger)                 
                )
  
                 
class TTimer(TableObject):
    def __init__(self):
        TableObject.__init__(self)
    
mapper_timer = Mapper(TTimer,tab_timer)       

if __name__=="__main__":
    pass