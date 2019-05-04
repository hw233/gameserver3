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

tab_reward_user_log = Table("reward_user_log", metadata,
                 Column("uid", Integer, primary_key=True),
                 Column("task_id",Integer, primary_key=True),
                 Column("state",Integer),
                 Column("finish_date",Date),
                 Column("create_time",DateTime),
                 )
                 


class TRewardUserLog(TableObject):
    def __init__(self):
        TableObject.__init__(self)
    def __repr__(self):
        return 'uid=%d,task_id=%d,state=%d' % \
               (self.uid,self.task_id,self.state)

mapper_reward_user_log = Mapper(TRewardUserLog,tab_reward_user_log)

if __name__=="__main__":
    pass