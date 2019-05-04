# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from config import var

from db.charge_item import *

class ShopCharge:
    def __init__(self, handler):
        self.handler = handler
        self.user_info = self.handler.user_info

    def create(self, uid, shop_id, comment, order_sn):

        self.uid = uid
        self.shop_id = shop_id
        self.comment = comment
        self.order_sn = order_sn

        self.shop_item = self.get_item(shop_id)
        self.money = self.shop_item.money
        self.handler.client_money = int(self.money * 100)
        self.handler.real_money = int(self.shop_item.real_money * 100)
        self.handler.name = self.shop_item.name
        return True, 0

    def receive(self):
        self.shop_item = self.get_item()
        self.charge_user()

    def charge_user(self):
        self.user_info.gold = self.user_info.gold + self.shop_item.gold
        self.handler.gold = self.shop_item.gold
        self.user_info.diamond = self.user_info.diamond + self.shop_item.diamond + self.shop_item.extra_diamond
        self.handler.diamond = self.shop_item.diamond + self.shop_item.extra_diamond
        self.user_info.money = int(self.user_info.money + self.handler.order.money)
        # self.user_info.flow_card = self.user_info.flow_card + int(self.handler.order.money)

    def mail(self):
        # item_price = int(self.shop_item.money)
        t_mail = self.handler.get_mail()

        t_mail.content = u'成功充值%.2f元' % (self.handler.charge_money)
        if self.shop_item.type is not None and self.shop_item.type == 'gold':
            t_mail.content += u'，购买%d金币' % (self.shop_item.gold)
        if self.shop_item.type is not None and self.shop_item.type == 'diamond':
            t_mail.content += u'，购买%d个钻石' % (self.shop_item.diamond)
        if self.shop_item.extra_diamond is not None and self.shop_item.extra_diamond > 0:
            t_mail.content += u'，赠送%d个钻石' % self.shop_item.extra_diamond
        # t_mail.content += u'，获得%d张流量券' % int(self.handler.order.money)

        return t_mail

    def get_item(self, shop_id = None):
        if shop_id == None:
            return self.handler.session.query(TChargeItem).filter(TChargeItem.id == self.handler.order.shop_id).first()
        else:
            return self.handler.session.query(TChargeItem).filter(TChargeItem.id == shop_id).first()

    def notify(self):
        self.handler.notify()