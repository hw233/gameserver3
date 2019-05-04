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

tab_lucky_config = Table("lucky_config", metadata,
                 Column("id",Integer, primary_key=True),
                 Column("value", String(1500)),
             	 )

                 
class TLuckyConfig(TableObject):
    def __init__(self):
        TableObject.__init__(self)


    
mapper_lucky = Mapper(TLuckyConfig,tab_lucky_config)

if __name__=="__main__":
    pass