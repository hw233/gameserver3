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

tab_reward_code_record = Table("reward_code_record", metadata,
                    Column("code_id", Integer, primary_key=True),
                    Column("uid", Integer, primary_key=True),
                    Column("create_time",DateTime),
                 )
                 


class TRewardCodeRecord(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    
mapper_reward_code_record = Mapper(TRewardCodeRecord,tab_reward_code_record)

if __name__=="__main__":
    pass