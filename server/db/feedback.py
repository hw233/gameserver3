#coding:utf-8

"""
���ݿ����ӹ���
"""

__author__ = "liangxiaokai@21cn.com"
__version__ = "1.0"
__date__ = "2011/04/14"
__copyright__ = "Copyright (c) 2011"
__license__ = "Python"

from db.connect import *

from sqlalchemy import Table,Column,func
from sqlalchemy.types import  *
from sqlalchemy.ext.declarative import declarative_base

tab_feedback = Table("feedback", metadata,
                    Column("id", Integer, primary_key=True),
                    Column("uid",Integer),
                    Column("message",CHAR(150)),
                    Column("contact",CHAR(30)),
                    Column("create_time",DateTime),
                    Column("status",SMALLINT),
                 )
                 


class TFeedBack(TableObject):
    def __init__(self):
        TableObject.__init__(self)


mapper_feed_back = Mapper(TFeedBack,tab_feedback)

if __name__=="__main__":
    pass