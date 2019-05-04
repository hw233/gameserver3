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

tab_user_goldflower = Table("user_goldflower", metadata,
                 Column("id", Integer, primary_key=True),
                 Column("channel",String(10),default="test",nullable =False),
                 Column("exp",Integer,default=0,nullable =False),
                 Column("win_games",Integer,default=0,nullable =False),
                 Column("total_games",Integer,default=0,nullable =False),
                 Column("best",String(255),default="",nullable =False),

                 Column("wealth_rank", Integer,default=-1),
                 Column("win_rank",Integer,default=-1),
                 Column("charm_rank",Integer,default=-1),
                 Column("charge_rank",Integer,default=-1),

                 Column("create_time", DateTime,nullable =False),
                 Column("max_bank", Integer,default=10,nullable =False),       # 银行账户上限
                 Column("max_items", Integer,default=20,nullable =False),      # 背包中最大的道具数
                 Column("max_gifts", Integer,default=20,nullable =False),      # 背包中最大的礼物数
                 Column("signin_days",SmallInteger,default=0,nullable =False), # 连续签到天数
                 Column("last_signin_day",Date), # 上次签到的日期
                 Column("online_time",Integer),  # 在线时长
                 Column("login_times",Integer),  # 登录次数
                 Column("change_nick",SmallInteger,)
                 )
                 

                 
class TUserGoldFlower(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'id=%d,signin_days=%d,last_signin_day=%s' % (self.id,self.signin_days,self.last_signin_day)

mapper_user_goldflower = Mapper(TUserGoldFlower,tab_user_goldflower)



if __name__=="__main__":
    pass