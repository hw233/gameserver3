# -*- coding: utf-8 -*-

__author__ = "liangxiaokai@21cn.com"
__version__ = "1.0"
__date__ = "2011/04/14"
__copyright__ = "Copyright (c) 2011"
__license__ = "Python"

from db.connect import *

from sqlalchemy import Table,Column,func
from sqlalchemy.types import  *
from sqlalchemy.orm import Mapper

tab_activity_wheel_log = Table("activity_wheel_log", metadata,
                 Column("id",Integer,primary_key=True),
                 Column("round",Integer),
                 Column("uid",Integer),
                 Column("reward_item",String(255)),
                 Column("create_time",DateTime),
                 )



class TActivityWheelLog(TableObject):
    def __init__(self):
        TableObject.__init__(self)


mapper_activity_wheel_log = Mapper(TActivityWheelLog,tab_activity_wheel_log)

if __name__=="__main__":
    pass