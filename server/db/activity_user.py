# -*- coding: utf-8 -*-
__author__ = 'Administrator'


__author__ = "liangxiaokai@21cn.com"
__version__ = "1.0"
__date__ = "2011/04/14"
__copyright__ = "Copyright (c) 2011"
__license__ = "Python"

from db.connect import *

from sqlalchemy import Table,Column,func
from sqlalchemy.types import  *
from sqlalchemy.orm import Mapper

tab_activity_user = Table("activity_user", metadata,
                 Column("uid",Integer,primary_key=True),
                 Column("params",String(255)),
                 )



class TActivityUser(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    def __repr__(self):
        return 'uid=%d,params=%s' % (self.uid,self.params)

mapper_activity_user = Mapper(TActivityUser,tab_activity_user)

if __name__=="__main__":
    pass