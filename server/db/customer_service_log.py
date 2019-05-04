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

tab_customer_service_log = Table("customer_service_log", metadata,
                    Column("id", Integer, primary_key=True),
                    Column("from_user",Integer),
                    Column("to_user",Integer),
                    Column("content",String),
                    Column("create_time",DateTime),
                 )
                 


class TCustomerServiceLog(TableObject):
    def __init__(self):
        TableObject.__init__(self)


mapper_custmer_service_log = Mapper(TCustomerServiceLog,tab_customer_service_log)

if __name__=="__main__":
    pass