# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from db.connect import *

from sqlalchemy import Table,Column,func
from sqlalchemy.types import  *
from sqlalchemy.orm import Mapper

tab_order_params = Table("order_params", metadata,
                 Column("order_id",Integer, primary_key=True),
                 Column("params",String(255)),
                 )


class TOrderParams(TableObject):
    def __init__(self):
        TableObject.__init__(self)

    # def __repr__(self):
    #     return "id=%id,icon=%s,name=%s,description=%s,gold=%d" % \
    #            (self.id,self.icon,self.name,self.description,self.gold)

mapper_order_params = Mapper(TOrderParams,tab_order_params)

if __name__=="__main__":
    pass