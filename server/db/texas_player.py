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

tab_texas_player = Table("texas_player", metadata,
                 Column("uid", Integer, primary_key=True,),
                 Column("play_count", Integer),
                 Column("win_count", Integer),
                 Column("max_win_gold", BigInteger),
                 )
                 


class TTexasPlayer(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'id=%d,imei=%s,state=%d,device_id=%s' % (self.id,self.imei,self.state,self.device_id)

    #def __repr__(self):
    #    return "brithday=%s,id=%d,mobile=%s,nick=%s,state=%d,imei=%s,imsi=%s,password=%s,create_time=%d,nick=%s,sign=%s,address=%s, sex=%d,channel=%d" % \
    #            (self.brithday,self.id,self.mobile,self.nick,self.state,self.imei,self.imsi,self.password,self.create_time,self.nick,self.sign,self.address, self.sex,self.channel)

mapper_texas_player = Mapper(TTexasPlayer,tab_texas_player)

if __name__=="__main__":
    pass