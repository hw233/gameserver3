# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from config import var


class QuickCharge:
    def __init__(self, handler):
        self.handler = handler

        self.user_info = self.handler.user_info

    def create(self, uid, shop_id, comment, order_sn):

        self.uid = uid
        self.shop_id = shop_id
        self.comment = comment
        self.order_sn = order_sn
        self.handler.name = u'快充'+self.get_quick(shop_id)[2]
        self.money = self.get_quick(shop_id)[0] / 100.00
        self.real_money = self.get_quick(shop_id)[3]
        self.handler.real_money = self.get_quick(shop_id)[3]
        self.handler.client_money = self.get_quick(shop_id)[0]
        return True, 0

    def receive(self):
        self.charge_user()

    def charge_user(self):
        self.user_info.gold = self.user_info.gold + self.get_quick_gold()
        self.handler.gold = self.get_quick_gold()
        self.user_info.money = int(self.user_info.money + self.handler.order.money)
        self.handler.diamond = 0
        # self.user_info.flow_card = self.user_info.flow_card + int(self.handler.order.money)

    def get_quick_gold(self):
        return self.get_quick()[1] * 10000

    def get_quick_money(self):
        return self.get_quick()[0] / 100.00

    def get_quick(self, shop_id = None):
        if shop_id == None:
            return var.QUICK_CHARGE[abs(self.handler.order.shop_id)-1]
        return var.QUICK_CHARGE[abs(shop_id)-1]

    def mail(self):
        t_mail = self.handler.get_mail()
        # item_price = self.get_quick_money()
        t_mail.content = u'快充成功%.2f元，获得%d万金币' % (self.handler.charge_money , self.get_quick_gold() / 10000 )
        # t_mail.content += u'，获得%d张流量券' % int(self.handler.order.money)
        return t_mail

    def __repr__(self):
        return 'money=%s,real_money=%s' % (self.money, self.real_money)

    def notify(self):
        self.handler.notify()