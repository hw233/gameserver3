# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import time
import random
import decimal
import json

from config.var import *
from helper import datehelper
from proto import hall_pb2
from proto import struct_pb2

from db.order import *
from db.charge_item import *
from db.item import *
from db.pop_activity import *
from db.pop_activity_user import *

from sqlalchemy import and_

class Order:
    def __init__(self, session, user_info, shop_id, comment):
        self.session = session
        self.user_info = user_info
        self.order_sn = 0
        self.resp_result = 0
        self.shop_id = shop_id
        self.comment = comment

        self.money = 0
        self.real_money = 0
        self.name = ''

    def check_order_info(self, r):
        if self.shop_id > 0 and self.shop_id < 1000:
            self.load_charge_item()
        elif self.shop_id == 1001:
            self.load_reward_box_item(r)
        elif self.shop_id >= 2000:
            self.load_date_item()
        elif self.shop_id == 0:
            self.load_first_charge()
        else:
            self.load_quick_charge()
        if self.resp_result == -1:
            return True

    def load_reward_box_item(self, r):
        box = r.get('reward_box_'+str(self.user_info.id))
        if box == None:
            self.resp_result = -1
            return
        dict_box = json.loads(box)
        self.money = dict_box['money']
        self.real_money = dict_box['real_money']
        self.name = dict_box['name']
        r.delete('reward_box_'+str(self.user_info.id))

    def load_charge_item(self):
        charge_item = self.session.query(TChargeItem).filter(TChargeItem.id == self.shop_id).first()
        if charge_item == None:
            self.resp_result = -1
            return

        self.money = charge_item.money
        self.real_money = int(decimal.Decimal(charge_item.real_money) * 100)
        self.name = charge_item.name

    def load_date_item(self):
        charge_item = self.session.query(TPopActivity).filter(TPopActivity.id == self.shop_id).first()
        if charge_item == None:
            self.resp_result = RESULT_FAILED_NO_ACTIVITY
            return

        used_activity = self.session.query(TPopActivityUser).filter(and_(TPopActivityUser.uid == self.user_info.id, TPopActivityUser.activity_id == charge_item.id)).first()
        if used_activity != None:
            self.resp_result = RESULT_FAILED_ACTIVITY
            return

        self.money = decimal.Decimal(charge_item.money)
        self.real_money = int(decimal.Decimal(charge_item.money) * 100)
        self.name = charge_item.title

    def load_first_charge(self):
        if self.user_info.is_charge:
            self.resp_result = -1
            return
        self.money = decimal.Decimal(FRIST_CHARGE['money']) / 100
        self.real_money = FRIST_CHARGE['real_money']
        self.name = FRIST_CHARGE['title']

    def load_quick_charge(self):
        try:
            money,gold_w,name,real_money = QUICK_CHARGE[abs(self.shop_id)-1]
            self.money = decimal.Decimal(money) / 100
            self.real_money = real_money
            self.name = name
        except Exception as e:
            self.resp_result = -1
            # print e.message
            return

    def create_order(self):
        order = TOrder()
        order.order_sn = self.order_sn
        order.uid = self.user_info.id
        order.money = self.money
        order.shop_id = self.shop_id
        order.status = -1
        order.comment = self.comment
        order.create_time = datehelper.get_today_str()
        self.session.add(order)

    def check_order_sn(self):
        order_sn = self.get_order_sn(self.user_info.id)
        order =  self.session.query(TOrder).filter(TOrder.order_sn == order_sn).first()
        if order is not None:
            order_sn = self.get_order_sn(self.user_info.id)
            order =  self.session.query(TOrder).filter(TOrder.order_sn == order_sn).first()
            if order is not None:
                self.resp_result = -1
                return True
        else:
            self.order_sn = order_sn

    def get_order_sn(self, uid):
        return time.strftime('%Y%m%d')+str(random.randint(10000,99999))+str(uid)

    def __repr__(self):
        return 'order_sn=%s,shop_id=%d,money=%d,real_money=%d,name=%s' % (self.order_sn, self.shop_id, self.money, self.real_money, self.name)

class Charge:
    def __init__(self):
        self.money = 0
        self.name = 0
        self.real_money = 0
        self.gold = 0
        self.diamond = 0
        self.hore = 0
        self.gold = 0
        self.kicking_card = 0
        self.vip_card = 0

    def is_not_first_charge(self, user_info, shop_id):
        if shop_id == 0 and user_info.is_charge == 1:
            return True
        return False

    def get_charge_items(self, session):
        return session.query(TChargeItem).filter(TChargeItem.type == 'diamond').all()

    def get_quick_charge(self, table_type):
        return QUICK_CHARGE[abs(table_type)-1]

class OrderHandle:
    def __init__(self, session):
        self.session = session
        self.order = None

    def get_order(self, order_sn, user):
        self.order = self.session.query(TOrder).filter(and_(TOrder.order_sn == order_sn, TOrder.uid == user, TOrder.status == -1)).first()

    def order_is_none(self):
        if self.order is None:
            return True
        return False

    def update_order_status(self, order_sn,sdk_order_sn, charge_money, status):
        self.session.query(TOrder).filter(TOrder.order_sn == order_sn).update({
            TOrder.sdk_order_sn:sdk_order_sn,
            TOrder.charge:charge_money,
            TOrder.status:status
        })

