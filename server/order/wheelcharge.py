# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import json

from config import var

from db.activity_user import *

class WheelCharge:
    CONF = {
        # 1011 : (u'5连抽45元',5,4500,1),
        # 1012 : (u'20连抽150元',20,15000,1),
        1011 : (u'5连抽45元',5,45,1),
        1012 : (u'20连抽150元',20,150,1),
        1013 : (u'抽1次10元',1,10,1),
    }

    def __init__(self, handler):
        self.handler = handler
        self.user_info = self.handler.user_info

        self.wheel = None

    def create(self, uid, shop_id, comment, order_sn):
        wheel = Wheel(shop_id)
        self.handler.name = wheel.name
        self.money = wheel.money 
        self.real_money = wheel.real_money

        self.uid = uid
        self.shop_id = shop_id
        self.comment = comment
        self.order_sn = order_sn
        
        self.handler.real_money = self.real_money
        self.handler.client_money = wheel.money
        return True, 0

    def receive(self):
        self.wheel = Wheel(self.handler.order.shop_id)
        self.charge_user()

    def charge_user(self):
        self.user_info.money = int(self.user_info.money + self.handler.order.money)
        # self.user_info.flow_card = self.user_info.flow_card + int(self.handler.order.money)
        self.handler.gold = 0
        self.handler.diamond = 0

        activity_user = self.handler.session.query(TActivityUser).filter(TActivityUser.uid == self.user_info.id).first()
        if activity_user == None:
            activity_user = TActivityUser()
            activity_user.uid = self.user_info.id
            activity_user.params = json.dumps(init_activity_user(self.wheel.play_count))
            self.handler.session.add(activity_user)
        else:
            user_params =  json.loads(activity_user.params)
            user_params['wheel']['play_count'] = int(user_params['wheel']['play_count']) + self.wheel.play_count
            self.handler.session.query(TActivityUser).filter(TActivityUser.uid == self.user_info.id).update({
                TActivityUser.params : json.dumps(user_params)
            })

    def mail(self):
        t_mail = self.handler.get_mail()
        # item_price = (var.FRIST_CHARGE['money'] / 100)
        t_mail.content = u'充值幸运转盘成功%s元，获得%s' % (self.handler.charge_money, self.wheel.name)
        # t_mail.content += u'，获得%d张流量券' % int(self.handler.order.money)
        return t_mail

    def notify(self):
        self.handler.notify()


class Wheel:
    def __init__(self, shop_id):
        wheel = self.init(shop_id)
        self.name = wheel[0]
        self.play_count = wheel[1]
        self.money = wheel[2]
        self.real_money = wheel[3]
        self.shop_id = shop_id

    def init(self, shop_id):
        return WheelCharge.CONF[shop_id]

def init_activity_user(play_count):
    return {'wheel':{
        'play_count':play_count
    }}