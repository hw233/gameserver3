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

tab_account = Table("account", metadata,
                 Column("id", Integer, primary_key=True,),
                 Column("mobile", String(20)),
                 Column("state", Integer,nullable =False),
                 Column("imei",String(45)),
                 Column("imsi",String(45)),
                 Column("password",String(11)),
                 Column("channel", String(50)),
                 Column("device_id",String(50),nullable =False),
                 )
                 


class TAccount(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'id=%d,imei=%s,state=%d,device_id=%s' % (self.id,self.imei,self.state,self.device_id)

    #def __repr__(self):
    #    return "brithday=%s,id=%d,mobile=%s,nick=%s,state=%d,imei=%s,imsi=%s,password=%s,create_time=%d,nick=%s,sign=%s,address=%s, sex=%d,channel=%d" % \
    #            (self.brithday,self.id,self.mobile,self.nick,self.state,self.imei,self.imsi,self.password,self.create_time,self.nick,self.sign,self.address, self.sex,self.channel)

mapper_account = Mapper(TAccount,tab_account)

if __name__=="__main__":
    pass