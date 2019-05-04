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

tab_lottery_auto = Table("lottery_auto", metadata,
                 Column("uid", Integer, primary_key=True),
                 Column("auto_bet_count", Integer),
                 Column("auto_bet_now", Integer),
                 Column("auto_bet_pokers", String(255)),
                 Column("win_gold", BigInteger),
                 Column("status",SMALLINT), # 1=进行中，0=已完成，-1=手动取消
                 Column("create_time",DateTime),
                 )



class TLotteryAuto(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return '<TLotteryAuto uid=%d,count=%d,now=%d,pokers=%s,win_gold=%d,status=%d>' % \
               (self.uid,self.auto_bet_count,self.auto_bet_now,self.auto_bet_pokers,self.win_gold,self.status)


    #def __repr__(self):
    #    return "brithday=%s,id=%d,mobile=%s,nick=%s,state=%d,imei=%s,imsi=%s,password=%s,create_time=%d,nick=%s,sign=%s,address=%s, sex=%d,channel=%d" % \
    #            (self.brithday,self.id,self.mobile,self.nick,self.state,self.imei,self.imsi,self.password,self.create_time,self.nick,self.sign,self.address, self.sex,self.channel)

mapper_lottery_auto = Mapper(TLotteryAuto,tab_lottery_auto)

if __name__=="__main__":
    pass