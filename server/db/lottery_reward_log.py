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

tab_lottery_reward_log = Table("lottery_reward_log", metadata,
                 Column("lottery_id", Integer, primary_key=True,),
                 Column("uid", Integer),
                 Column("create_unixtime", Integer),
                 Column("reward_gold",BigInteger),
                 )
                 


class TLotteryRewardLog(TableObject):
    def __init__(self):
        TableObject.__init__(self)


    #def __repr__(self):
    #    return "brithday=%s,id=%d,mobile=%s,nick=%s,state=%d,imei=%s,imsi=%s,password=%s,create_time=%d,nick=%s,sign=%s,address=%s, sex=%d,channel=%d" % \
    #            (self.brithday,self.id,self.mobile,self.nick,self.state,self.imei,self.imsi,self.password,self.create_time,self.nick,self.sign,self.address, self.sex,self.channel)

mapper_lottery_reward_log = Mapper(TLotteryRewardLog,tab_lottery_reward_log)

if __name__=="__main__":
    pass