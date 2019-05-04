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

tab_friend = Table("friend", metadata,
                 Column("apply_uid",Integer, primary_key=True,nullable =False), # 申请方
                 Column("to_uid",Integer, primary_key=True,nullable =False),    # 答复方
                 Column("type",Integer,nullable =False),  # type = 0 是系统关系不允许解除,type=1,为普通关系可以解除
                 Column("create_time",DateTime,nullable =False),
                 )
                 

                 
class TFriend(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'id=%d,apply_uid=%d,to_uid=%d' % (self.id,self.apply_uid,self.to_uid)

mapper_friend = Mapper(TFriend,tab_friend)

if __name__=="__main__":
    pass