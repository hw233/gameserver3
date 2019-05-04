# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from config import var

class FirstCharge():
    def __init__(self, handler):
        self.handler = handler
        self.user_info = self.handler.user_info

    def create(self, uid, shop_id, comment, order_sn):

        self.uid = uid
        self.shop_id = shop_id
        self.comment = comment
        self.order_sn = order_sn
        self.handler.name = var.FRIST_CHARGE['title']
        self.money = var.FRIST_CHARGE['money'] / 100.00
        self.real_money = var.FRIST_CHARGE['real_money']
        self.handler.client_money = self.real_money
        self.handler.real_money = self.real_money

        return True, 0

    def receive(self):
        self.charge_user()
        self.gift()

    def charge_user(self):
        self.user_info.is_charge = 1
        self.user_info.gold = self.user_info.gold + var.FRIST_CHARGE['gold'] * 10000
        self.handler.gold = var.FRIST_CHARGE['gold'] * 10000
        self.user_info.diamond = self.user_info.diamond + var.FRIST_CHARGE['diamond']
        self.handler.diamond = var.FRIST_CHARGE['diamond']
        self.user_info.money = int(self.user_info.money + self.handler.order.money)

        # self.user_info.flow_card = self.user_info.flow_card + int(self.handler.order.money)

    def gift(self):
        for item in var.FRIST_CHARGE['items'].split(','):
            arr_item = item.split('-')
            self.handler.save_gift({
                'uid':self.user_info.id,
                'stuff_id':arr_item[0],
                'countof':arr_item[1]
            })

    def mail(self):
        t_mail = self.handler.get_mail()
        # item_price = (var.FRIST_CHARGE['money'] / 100)
        t_mail.content = u'首充成功%.2f元，获得%d万金币，%d个钻石，%d张喇叭卡，%d张踢人卡，%d张vip经验卡' %\
                       (self.handler.charge_money, var.FRIST_CHARGE['gold'],var.FRIST_CHARGE['diamond'], var.FRIST_CHARGE['hore'], var.FRIST_CHARGE['kicking_card'], var.FRIST_CHARGE['vip_card'])
        # t_mail.content += u'，获得%d张流量券' % int(self.handler.order.money)
        return t_mail

    def notify(self):
        self.handler.notify()