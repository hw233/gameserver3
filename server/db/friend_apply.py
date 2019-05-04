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

tab_friend_apply = Table("friend_apply", metadata,
                 Column("id",Integer, primary_key=True),
                 Column("apply_uid",Integer,nullable =False), # 申请方
                 Column("to_uid",Integer,nullable =False),    # 答复方
                 Column("gifts",String(100)),  # 格式如下:"(gift_id,count),(gift_id,count),...."
                 Column("message",String(140)),
                 Column("state",SmallInteger,nullable =False),
                 Column("apply_time",DateTime,nullable =False),
                 Column("finish_time",DateTime),
                 )
                 

                 
class TFriendApply(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'id=%d,apply_uid=%d,to_uid=%d,gifts=%s,message=%s,state=%d,apply_time=%s,finish_time=%s' % \
               (self.id,self.apply_uid,self.to_uid,self.gifts,self.message,self.state,str(self.apply_time),str(self.finish_time))
    
mapper_friend_apply = Mapper(TFriendApply,tab_friend_apply)

if __name__=="__main__":
    pass