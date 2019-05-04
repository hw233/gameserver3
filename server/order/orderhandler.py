# -*- coding: utf-8 -*-
import random
import time

__author__ = 'Administrator'


import decimal
import json
import logging
import traceback

# import os
# import sys
# sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# test_message     普通商品购买 1-1000
# first_recharge   首充      0
# action_charge    活动，已废弃
# quick_recharge   快充     -1（初级快充）,-2（普通快充）,-3（高级快充）,-4（大师快充）,-5(红黑快充)
# reward_box       幸运宝箱 1001
# wheel_chrage     h5网页幸运转盘 1011

from sqlalchemy import and_

from db.order import *
from db.user import *
from db.lucky import *

from config import var
from config import broadcast

from hall import uservip
from hall.messagemanager import *
from hall.rank import *
from task.achievementtask import *
from rank.chargetop import ChargeTop

from order.firstcharge import *
from order.shopcharge import *
from order.quickcharge import *
from order.boxcharge import *
from order.wheelcharge import *


class OrderFactory:
    type = {
            'first_recharge':FirstCharge,
            'test_message':ShopCharge,
            'quick_recharge':QuickCharge,
            'reward_box':BoxCharge,
            'wheel_recharge':WheelCharge,
        }

    @staticmethod
    def receive_order(orderhandler):
        orderhandler.init_order()

        if orderhandler.order == None:
            return False


        if orderhandler.order.comment in OrderFactory.type:
            handler = OrderFactory.type[orderhandler.order.comment]
            order = handler(orderhandler)

            try:
                orderhandler.session.begin()

                order.receive()
                orderhandler.send_mail(order.mail())
                orderhandler.load_old_rank()
                orderhandler.change_order_status()
                orderhandler.change_vip_exp()
                orderhandler.change_lucky()
                orderhandler.save_rank()
                orderhandler.load_new_rank()
                orderhandler.charge_top_up()
                orderhandler.end()

                orderhandler.session.commit()
                order.notify()
                return True
            except Exception as e:
                traceback.print_exc()
                orderhandler.session.rollback()
                return False

    @staticmethod
    def create_order(orderhandler, uid, shop_id, comment):
        """
        订单�?
        1-1000：普通商品id
        1001：幸运宝�?
        101x：网页活�?幸运转盘(1次抽10元，5连抽45元，20连抽150)
            1011:1次抽10�?
            1012:5次抽45�?
            1013:20次抽150�?
        >2000：日期活动，一分钱充值活动，以前使用过但是运营效果不好，之后就不用了
        0：首冲订�?
        负数(-1,-2,-3,-4,-5)：初级场，中级场，高级场，大师场，红黑大�?
        :param orderhandler:
        :param uid:
        :param shop_id:
        :param comment:
        :return:
        """
        try:
            if comment in OrderFactory.type:
                handler = OrderFactory.type[comment]

                result, order_sn = orderhandler.create_sn(uid)
                if result == False:
                    return False

                order = handler(orderhandler)

                result, _ = order.create(uid, shop_id, comment, order_sn)

                if result == False:
                    return False

                orderhandler.save_order(order)
                orderhandler.session.flush()
                return True
        except Exception as e:
            traceback.print_exc()
            logging.info(u'用户(%d)购买商品(%d)创建订单失败 %s' % (uid,shop_id,e.message))
            # print u'用户(%d)购买商品(%d)创建订单失败 %s' % (uid,shop_id,e.message)
            return False


class OrderHandler(object):

    def __init__(self, session, redis, dal, callback_json = ''):
        self.session = session
        self.redis = redis
        self.dal = dal
        self.callback_json = callback_json
        if self.callback_json != '':
            if isinstance(self.callback_json['private'], unicode) or isinstance(self.callback_json['private'], str):
                self.callback_json['private'] = json.loads(callback_json['private'])

        self.old_rank = None
        self.new_rank = None
        self.old_rank_index = -1
        self.new_rank_index = -1
        self.order = None

        self.gold = 0
        self.diamond = 0
        self.charge_money = 0
        self.user_info = None

        self.callback_url = var.PAY_CALLBACK_NEW
        self.name = None
        self.notify_param1 = 0

    def end(self):
        try:
            if isinstance(self.user_info.sign, str):
                self.user_info.sign = self.user_info.sign.decode('utf-8')
            if isinstance(self.user_info.nick, str):
                self.user_info.nick = self.user_info.nick.decode('utf-8')
        finally:
            self.dal.save_user(self.session, self.user_info)

        # 强制更新至缓�?
        self.dal.get_user(self.user_info.id, True)


        # 更新用户信息队列
        self.redis.lpush('war_user_update',json.dumps({'uid':self.user_info.id}))

    # 创建订单时使�?
    def save_order(self, order):
        t_order = TOrder()
        t_order.order_sn = order.order_sn
        t_order.uid = order.uid
        t_order.money = order.money
        t_order.shop_id = order.shop_id
        t_order.status = -1
        t_order.comment = order.comment
        t_order.create_time = time.strftime('%Y-%m-%d %H:%M:%S')
        self.session.add(t_order)
        self.session.flush()

        if hasattr(order, 'params') and order.params != None:
            t_order_params = TOrderParams()
            t_order_params.order_id = t_order.id
            t_order_params.params = json.dumps(order.params)
            self.session.add(t_order_params)

        self.order = t_order

    def create_sn(self, uid):
        order_sn = self.get_order_sn(uid)
        order =  self.session.query(TOrder).filter(TOrder.order_sn == order_sn).first()
        if order is not None:
            return False, -1,
        return True, order_sn

    def get_order_sn(self, uid):
        return time.strftime('%Y%m%d')+str(random.randint(10000,99999))+str(uid)

    # 接收第三方订单回调时使用
    def init_order(self):
        # print 'init_order==================================>'
        # print self.callback_json,type(self.callback_json)

        self.charge_money = decimal.Decimal(self.callback_json['money'])
        self.order = self.session.query(TOrder).filter(and_(TOrder.order_sn == self.callback_json['private']['order'],
                                                                    TOrder.uid == self.callback_json['private']['other'],
                                                                    TOrder.status == -1)).first()

        self.user_info = self.dal.get_user(self.callback_json['private']['other'])

    def check_order(self):
        if self.order == None:
            return False
        return True

    def change_order_status(self):
        self.session.query(TOrder).filter(TOrder.order_sn == self.callback_json['private']['order']).update({
            TOrder.sdk_order_sn : self.callback_json['order_sn'],
            TOrder.charge : self.charge_money,
            TOrder.status : 1 if decimal.Decimal(self.order.money) != self.charge_money else 0
        })

    def send_mail(self, mail):
        if mail != None:
            self.session.add(mail)

    def change_vip_exp(self):
        old_vip_exp = 0 if self.user_info.vip_exp <= 0 else self.user_info.vip_exp
        old_vip_level = uservip.get_vip(old_vip_exp)
        new_vip_exp = int(old_vip_exp + self.order.money)
        self.user_info.vip_exp = new_vip_exp
        new_vip_level = uservip.get_vip( self.user_info.vip_exp)
        if old_vip_exp < new_vip_exp:
            diff_level = new_vip_level - old_vip_level
            if diff_level > 0:
                MessageManager.broadcast_change_vip(self.redis, self.user_info.id, self.user_info.nick, self.user_info.vip_exp)
                SystemAchievement(self.session,self.user_info.id).finish_upgrade_vip(new_vip_level)

    def notify(self, param1 = 0, param2 ='' ):
        MessageManager.push_notify_charge(self.redis, self.user_info.id, param1, param2)

    def broadcast(self, message):
        MessageManager.push_notify_broadcast(self.redis, message)

    def charge_top_up(self):
        if self.old_rank_index > self.new_rank_index:
            MessageManager.broadcast_charge_rank(self.redis, {'message':broadcast.BORADCAST_CONF['charge_top'] % (self.user_info.nick, self.new_rank_index)})
        elif self.old_rank_index == -1 and self.new_rank_index > 0:
            MessageManager.broadcast_charge_rank(self.redis, {'message':broadcast.BORADCAST_CONF['charge_top'] % (self.user_info.nick, self.new_rank_index)})

    def load_new_rank(self):
        self.new_rank = self.load_rank()

        self.new_rank_index = self.find_index(self.new_rank, self.user_info.id)

    def load_old_rank(self):
        self.old_rank = self.load_rank()

        self.old_rank_index = self.find_index(self.old_rank, self.user_info.id)

    def load_rank(self):
        return Rank(None).charge_top(self.session, var.RANK_TODAY, by_index=True)

    def find_index(self, ranks, uid):
        rank_index = -1

        if ranks == None:
            return rank_index

        for index, rank in enumerate(ranks):
            if rank[1].id == uid:
                return index +1
        return rank_index

    def change_lucky(self):
        self.session.query(TLucky).filter(TLucky.uid == self.user_info.id).update({
            TLucky.lucky: TLucky.lucky + (self.charge_money * 10)
        })

    def save_rank(self):
        ChargeTop.save_rank(self.session, self.order.uid, self.gold, self.diamond, self.charge_money)

    def save_gift(self, fields):
        insert_stmt = "INSERT INTO bag_item(uid,item_id,countof) VALUES (:col_1,:col_2,:col_3) ON DUPLICATE KEY UPDATE countof = countof + :col_3;"
        self.session.execute(insert_stmt, {
            'col_1':fields['uid'],
            'col_2':fields['stuff_id'],
            'col_3':fields['countof']
        })

    def get_mail(self):
        mail = TMail()
        mail.from_user = 10000
        mail.to_user = self.user_info.id
        mail.sent_time = time.time()
        mail.title = u'充值'

        mail.type = 0
        mail.diamond = 0
        mail.gold = 0
        mail.state = 1
        return mail

    def get_order_params(self):
        return self.session.query(TOrderParams).filter(TOrderParams.order_id == self.order.id).first()

def create_charge_order(session, r, dal, uid, shop_id, comment):
    handler = OrderHandler(session, r, dal)
    OrderFactory.create_order(handler, uid, shop_id, comment)
    return {'money':handler.real_money, 'name':handler.name, 'order_sn':handler.order.order_sn,'callback':handler.callback_url}

def receive_order_callback(session, r, dal, data):
    handler = OrderHandler(session, r, dal, data)
    return OrderFactory.receive_order(handler)

if __name__ == '__main__':
    from db.connect import *
    from dal.core import *
    from util.commonutil import *
    import redis
    
    session = Session()
    user = session.query(TUser).first()
    set_context('session', session)
    
    r = redis.Redis(password='Wgc@123456')
    dal = DataAccess(r)

    #OrderFactory.create_order(OrderHandler(session, r, dal), 11260, 3, 'test_message') # 普通商�?
    #OrderFactory.create_order(OrderHandler(session, r, dal), 11260, 0, 'first_recharge') # 首冲
    #OrderFactory.create_order(OrderHandler(session, r, dal), 11260, -5, 'quick_recharge') # 快冲/红黑�?
    #OrderFactory.create_order(OrderHandler(session, r, dal), 11260, 1001, 'reward_box') # 宝箱
    #OrderFactory.create_order(OrderHandler(session, r, dal), 11260, 1013, 'wheel_recharge') # 转盘

    callback = {u'data':
        {
                        u'cp_id': u'LT20151153-108',
                        u'cp_order_sn': u'1472887662193GKEtoVrkx1',
                        u'money': u'0.01',
                        u'order_sn': u'LT147288765663644948100919662833',
                        u'private': {
                            u'order': u'201801103630624388', # 修改订单号来处理不同的订�?
                            u'other': u'24388',
                            u'privateInfo': u'd970d2fb85336be9221b16961f051f82',
                        }
        },
                u'sign': u''}


    OrderFactory.receive_order(OrderHandler(session, r, dal, callback[u'data']))
