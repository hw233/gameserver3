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

tab_bank_account = Table("bank_account", metadata,
                 Column("uid",Integer, primary_key=True),
                 Column("gold",Integer,default=0,nullable =False),
                 Column("diamond",Integer,default=0,nullable =False),
                 Column("update_time", DateTime,nullable =False),
                 Column("create_time", DateTime,nullable =False),
                 )
                 

                 
class TBankAccount(TableObject):
    def __init__(self):
        TableObject.__init__(self)
    
mapper_bank_account = Mapper(TBankAccount,tab_bank_account)

if __name__=="__main__":
    pass