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

tab_reward_task = Table("reward_task", metadata,
                    Column("id", Integer, primary_key=True),
                    Column("category", String(15)),
                    Column("is_daily", SmallInteger),
                    Column("name",String(140)),
                    Column("description", String(255)),
                    Column("params",String(200)),
                    Column("gold",Integer),
                    Column("diamond",Integer),
                    Column("items",String(255)),
                    Column("gifts",String(255)),
                    Column("create_time",DateTime),
                    Column("icon",Integer),
                    Column("action",String(255)),

                 )
                 


class TRewardTask(TableObject):
    def __init__(self):
        TableObject.__init__(self)
    def __repr__(self):
        return 'id=%d,action=%s,items=%s' % (self.id,self.action, self.items)
        # return 'category=%s,is_daily=%d,name=%s,description=%s,params=%s,gold=%d,diamond=%d,items=%s,gifts=%,action=%s' % \
        #        (self.category.encode('utf-8'),self.is_daily,self.name.encode('utf-8'),self.description.encode('utf-8'),self.params,self.gold,self.diamond,self.items,self.gifts,self.action)
    # def __repr__(self):
    #     return "brithday=%s,id=%d,mobile=%s,nick=%s,state=%d,imei=%s,imsi=%s,password=%s,create_time=%d,nick=%s,sign=%s,address=%s, sex=%d,channel=%d" % \
    #             (self.brithday,self.id,self.mobile,self.nick,self.state,self.imei,self.imsi,self.password,self.create_time,self.nick,self.sign,self.address, self.sex,self.channel)

mapper_reward_task = Mapper(TRewardTask,tab_reward_task)

if __name__=="__main__":
    pass