#coding:utf-8

"""
\u6570\u636E\u5E93\u8FDE\u63A5\u7BA1\u7406
"""

__author__ = "liangxiaokai@21cn.com"
__version__ = "1.0"
__date__ = "2011/04/14"
__copyright__ = "Copyright (c) 2011"
__license__ = "Python"

from connect import *

from sqlalchemy import Table,Column,func
from sqlalchemy.types import  *
from sqlalchemy.orm import Mapper

tab_rank = Table("rank", metadata,
                 Column("type",Integer,primary_key=True),
                 Column("rank",Integer,primary_key=True),
                 Column("period_type",Integer,primary_key=True),
                 Column("period",Integer,primary_key=True),
                 Column("uid",Integer),
                 Column("rank_value",Integer,default=-1),
                 )
                 

                 
class TRank(TableObject):
    def __init__(self):
        TableObject.__init__(self)
    
mapper_rank = Mapper(TRank,tab_rank)

if __name__=="__main__":
    pass