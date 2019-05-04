# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import gevent
from gevent import monkey;monkey.patch_all()
from gevent import lock
from gevent.queue import Queue

import json
from sqlalchemy.sql import and_

from db.order import *



class OrderHandler:

    def __init__(self, redis, session):
        self.redis = redis
        self.session = session

    def order_queue(self):
        while True:
            _,order_str = self.redis.brpop("order")

            self.handler( json.loads(order_str) )

    def handler(self, order_seq):
        self.session.query(TOrder).filter(and_(TOrder.order_sn == order_seq[''], TOrder.uid == order_seq[''], TOrder.status == -1)).first()

class Order:
    def __init__(self, t_order):
        self.t_order = t_order
