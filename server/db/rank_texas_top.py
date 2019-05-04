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

tab_rank_texas_top = Table("rank_texas_top", metadata,
                    Column("add_date", Date, primary_key=True),
                    Column("uid",Integer, primary_key=True),
                    Column("total",BigInteger),
                    Column("created_time",DateTime),
                 )
                 


class TRankTexasTop(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'add_date=%s, uid=%d, total=%d,created_time=%s' % (str(self.add_date),self.uid,self.total,str(self.created_time))

    #def __repr__(self):
    #    return "brithday=%s,id=%d,mobile=%s,nick=%s,state=%d,imei=%s,imsi=%s,password=%s,create_time=%d,nick=%s,sign=%s,address=%s, sex=%d,channel=%d" % \
    #            (self.brithday,self.id,self.mobile,self.nick,self.state,self.imei,self.imsi,self.password,self.create_time,self.nick,self.sign,self.address, self.sex,self.channel)

mapper_rank_texas_top = Mapper(TRankTexasTop,tab_rank_texas_top)

if __name__=="__main__":
    pass