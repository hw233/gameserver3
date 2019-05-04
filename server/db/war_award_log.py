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
from sqlalchemy.ext.declarative import declarative_base

tab_war_award_log = Table("war_award_log", metadata,
                    Column("war_id", Integer, primary_key=True),
                    Column("award",Integer, primary_key=True),
                    Column("is_top1",SMALLINT),
                    Column("uid",Integer),
                    Column("create_time",Integer),
                 )



class TWarAwardLog(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'war_id=%d,award=%d,uid=%d,is_top1=%d' % (self.war_id, self.award, self.uid, self.is_top1)


mapper_war_award_log = Mapper(TWarAwardLog,tab_war_award_log)

if __name__=="__main__":
    pass