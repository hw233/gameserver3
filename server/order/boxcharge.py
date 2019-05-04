# -*- coding: utf-8 -*-
import json

__author__ = 'Administrator'

from db.order_params import *
from config import broadcast

class BoxCharge:
    def __init__(self, handler):
        self.handler = handler
        self.user_info = self.handler.user_info

    def create(self, uid, shop_id, comment, order_sn):
        box = self.handler.redis.get('reward_box_'+str(uid))

        if box == None:
            return False, -2

        dict_box = json.loads(box)

        self.gold = dict_box['gold']
        self.diamond = dict_box['diamond']
        self.money = dict_box['money'] / 100
        self.real_money = dict_box['real_money']
        self.handler.name = dict_box['name']
        self.handler.redis.delete('reward_box_'+str(uid))
        self.handler.real_money = self.real_money
        self.handler.client_money = dict_box['money']
        self.params = {
            'reward_box':{
                'gold':self.gold,
                'diamond':self.diamond
            }
        }

        self.uid = uid
        self.shop_id = shop_id
        self.comment = comment
        self.order_sn = order_sn
        self.handler.notify_param1 = 1
        return True, 0


    def receive(self):
        order_setting = self.handler.get_order_params()
        params = json.loads(order_setting.params)
        self.gold = params['reward_box']['gold']
        self.handler.gold = self.gold
        self.diamond = params['reward_box']['diamond']
        self.handler.diamond = self.diamond
        self.charge_user()

    def charge_user(self):
        self.user_info.gold = self.user_info.gold + self.gold
        self.user_info.diamond = self.user_info.diamond + self.diamond
        self.user_info.money = int(self.user_info.money + self.handler.order.money)
        # self.user_info.flow_card = self.user_info.flow_card + int(self.handler.order.money)


    def mail(self):
        t_mail = self.handler.get_mail()
        t_mail.content = u'幸运宝箱充值成功%.2f元' % self.handler.charge_money
        t_mail.content += u'，获得%d金币' % (self.gold)
        # t_mail.content += u'，获得%d金币，获得%d张流量券' % (self.gold, int(self.handler.order.money))
        return t_mail

    def notify(self):
        message = broadcast.BORADCAST_CONF['reward_box'] % (self.user_info.nick, self.gold)
        self.handler.notify(param1=1)
        self.handler.broadcast(message)
