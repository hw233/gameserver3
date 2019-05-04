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

tab_texas_gambler = Table("texas_gambler", metadata,
                 Column("game_id", Integer, primary_key=True,),
                 Column("uid", Integer, primary_key=True,),
                 Column("hand_pokers", String(40)),
                 Column("final_pokers",String(40)),
                 Column("bet_gold",BigInteger),
                 Column("is_win",SMALLINT),
                 Column("win_gold",BigInteger),
                 Column("fee", BigInteger),
                 Column("create_time",DateTime),
                 )
                 


class TTexasGambler(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        # return 'game_id=%d,uid=%d,hand_pokers=%s,final_pokers=%s,is_win=%d,win_gold=%d,bet_gold=%d,fee=%d,back_gold=%d' % \
        #        (self.game_id,self.uid,str(self.hand_pokers),str(self.final_pokers),self.is_win,self.win_gold,self.bet_gold,self.fee,self.back_gold)
        return 'game_id=%d' % (self.game_id)
    #def __repr__(self):
    #    return "brithday=%s,id=%d,mobile=%s,nick=%s,state=%d,imei=%s,imsi=%s,password=%s,create_time=%d,nick=%s,sign=%s,address=%s, sex=%d,channel=%d" % \
    #            (self.brithday,self.id,self.mobile,self.nick,self.state,self.imei,self.imsi,self.password,self.create_time,self.nick,self.sign,self.address, self.sex,self.channel)

mapper_texas_gambler = Mapper(TTexasGambler,tab_texas_gambler)

if __name__=="__main__":
    pass