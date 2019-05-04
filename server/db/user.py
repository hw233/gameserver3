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

tab_user = Table("user", metadata,
                 Column("id", Integer, primary_key=True),
                 Column("nick",String(40),default="guest"),
                 Column("avatar", String(255),nullable =False),
                 Column("gold",BigInteger,default=0,nullable =False),
                 Column("diamond",BigInteger,default=0,nullable =False),
                 Column("vip", Integer,default=0,nullable =False),
                 Column("money",Integer,default=0,nullable =False),
                 Column("type",SmallInteger,default=0),
                 Column("charm", Integer,default=0,nullable =False),
                 Column("birthday",Date),
                 Column("sign",String(140)),
                 Column("sex",Integer),
                 Column("address",String(140)),
                 Column("channel",String(10),default="test"),
                 Column("create_time",DateTime,nullable =False),
                 Column("vip_exp",Integer,default=0),
                 Column("is_charge", SMALLINT),
                 Column("flow_card", Integer),
                 )
                 

                 
class TUser(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'id=%d,nick=%s' % (self.id, self.nick)

mapper_user = Mapper(TUser,tab_user)       

if __name__=="__main__":
    pass