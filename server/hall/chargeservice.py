#coding: utf-8

import json
import logging
import traceback
import socket
import gevent
import binascii
from ctypes import *

import random,time
from datetime import datetime
from datetime import date as dt_date
from datetime import time as dt_time



from services import GameService
from message.base import *
from message.resultdef import *

from proto.constant_pb2 import *
from proto.struct_pb2 import *
from proto.hall_pb2 import *

from util.handlerutil import *

from db.connect import *
from db.order import *
from db.charge_item import *
from helper import protohelper
from dal.core import *

from hall.charge_order import *
from hall.rewardbox import BOX_CONFIG
from order.orderhandler import create_charge_order

class ChargeService(GameService):
    def setup_route(self):
        self.registe_command(CreateOrderReq,CreateOrderResp,self.handle_create_order)
        self.registe_command(QueryFirstTimeChargeReq,QueryFirstTimeChargeResp,self.handle_first_charge)
        self.registe_command(QueryChargeReq,QueryChargeResp,self.handle_charge)
        self.registe_command(QueryQuickBuyGoldReq,QueryQuickBuyGoldResp,self.handle_quick_charge)

    def init(self):
        self.redis = self.server.redis
        self.da = DataAccess(self.redis)
        self.t_order = TOrder()
        self.charge = Charge()

    @USE_TRANSACTION
    def handle_create_order(self,session,req,resp,event):
        if req.body.shop_id in BOX_CONFIG.keys():
            if not self.redis.exists('reward_box_'+str(req.header.user)):
                resp.header.result = -1
                return
        elif req.body.shop_id == 0:
            user_info = self.da.get_user(req.header.user)
            if user_info.is_charge != 0:
                resp.header.result = -1
                return

        result = create_charge_order(session, self.redis, self.da, req.header.user, req.body.shop_id, req.body.comment)
        resp.body.name = result['name']
        resp.body.money = result['money']
        resp.body.order_sn = result['order_sn']
        resp.body.callback = result['callback']
        resp.header.result = 0


        # # shop_id = 0 首充，负数代表快充场次，正数代表商品id
        # user_info = self.da.get_user(req.header.user)
        #
        # if self.charge.is_not_first_charge(user_info, req.body.shop_id):
        #     resp.header.result = RESULT_FAILED_FIRST_CHARGE
        #     return
        #
        # order = Order(session, user_info,req.body.shop_id,req.body.comment)
        # if order.check_order_sn():
        #     resp.header.result = order.resp_result
        #     return
        #
        # if order.check_order_info(self.server.redis):
        #     resp.header.result = order.resp_result
        #     return
        #
        # order.create_order()
        #
        # resp.body.name = order.name
        # # todo ...正式环境需要修改为order.money
        # # resp.body.money = order.money
        # resp.body.money = order.real_money
        # resp.body.order_sn = str(order.order_sn)
        # resp.body.callback = PAY_CALLBACK
        # resp.header.result = 0

    @USE_TRANSACTION
    def handle_first_charge(self,session,req,resp,event):
        user_info = self.da.get_user(req.header.user)
        if user_info.is_charge == 1:
            resp.header.result = RESULT_FAILED_FIRST_CHARGE
            return

        resp.body.money = FRIST_CHARGE['money']
        resp.body.diamond = FRIST_CHARGE['diamond']
        resp.body.hore = FRIST_CHARGE['hore']
        resp.body.gold = FRIST_CHARGE['gold']
        resp.body.kicking_card = FRIST_CHARGE['kicking_card']
        resp.body.vip_card = FRIST_CHARGE['vip_card']
        resp.header.result = 0

    @USE_TRANSACTION
    def handle_charge(self,session,req,resp,event):
        items = self.charge.get_charge_items(session)
        for item in items:
            protohelper.set_charge(resp.body.items.add(), item)
        resp.header.result = 0

    @USE_TRANSACTION
    def handle_quick_charge(self,session,req,resp,event):
        money,gold,name,real_money = self.charge.get_quick_charge(req.body.table_type)
        resp.body.money = money
        resp.body.gold = gold
        resp.header.result = 0