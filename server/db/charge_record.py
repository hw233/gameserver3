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

tab_charge_record = Table("charge_record", metadata,
                    Column("id",Integer, primary_key=True),
                    Column("uid",Integer),
                    Column("is_first",SmallInteger,default=0), # 0为非首充
                    Column("charge_item_id",Integer),
                    Column("money",Integer,default=0),
                    Column("diamond",Integer,default=0),
                    Column("pay_mode",Integer), #0 微信, 1:支付宝,2:网银 3:短信
                    Column("create_time", DateTime),
                 )
                 

                 
class TChargeRecord(TableObject):
    def __init__(self):
        TableObject.__init__(self)
    
mapper_charge_record = Mapper(TChargeRecord,tab_charge_record)

if __name__=="__main__":
    pass