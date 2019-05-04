# -*- coding: utf-8 -*-
__author__ = 'Administrator'
import requests
import time
import datetime
import random
import logging

from sqlalchemy import and_

from helper import encryhelper
from db.flow_order import *
from db.flow_items import *
from config.var import *
from hall.messagemanager import *



CODE_MAP = {
    0: u'订购中',
    1: u'订购成功',
    2: u'订购失败',
    -1: u'系统错误',
    -100000: u'不合法的请求,非信任IP',
    -100001: u'数据验证未通过',
    -100003: u'参数格式异常',
    -100010: u'销售品ID未配置',
    -100012: u'您的库存不足',
    -100013: u'分销商未申请接入分销接口',
    -100016: u'订购接口返回异常信息',
    -100017: u'号码归属地获取异常',
    -100018: u'激活码不存在或已使用',
    -100019: u'未知渠道商！'
}


class Flow:
    def __init__(self, uid, phone, flow_card, flow_id, flow_name, comment):
        self.order = TFlowOrder()
        self.order.flow_order_sn = self.get_sn()
        self.order.uid = uid
        self.order.phone = phone
        self.order.flow_card = flow_card
        self.order.flow_item_id = flow_id
        self.order.flow_item_name = flow_name
        self.order.status = 0 # 订购中
        self.order.status_text = u'订购中'
        self.order.comment = comment
        self.order.callback_msg = ''
        self.order.create_time = time.strftime('%Y-%m-%d %H:%M:%S')

    def save_order(self, session, flow_item):
        session.add(self.order)
        flow_item.used = flow_item.used + 1
        session.add(flow_item)
        self.order.sn = flow_item.sn
        session.flush()

    def send_request(self):
        resp = requests.get(FLOW_URL, params=self.encry_params(self.order))
        return resp

    def save_resp(self, session, resp):
        logging.info(u'流量卡购买请求响应：'+str(resp.json()))
        resp_json = resp.json()
        # resp_json = {
        #     'code': random.choice([0,2]),
        #     'text':'',
        #     'ext':{}
        # }
        resp_json['text'] = u'订购中' if resp_json['code'] == 0 else u'订购失败'
        if 'code' in resp_json and resp_json['code'] == 0:
            self.update_flow_status(session, self.order, 0, resp_json['text'])
            return True,resp_json['text']
        else:
            if resp_json['code'] in CODE_MAP.keys():
                res_msg = CODE_MAP[resp_json['code']]
                self.update_flow_status(session, self.order, resp_json['code'], resp_json['text'])
            else:
                res_msg = resp_json['code']
                self.update_flow_status(session, self.order, resp_json['code'], resp_json['text'])
            return False,res_msg

    def encry_params(self, order):
        t = str(int(time.time() * 1000))
        params = [
            'req_id=%s' % order.flow_order_sn,
            'phone=%s' % order.phone,
            'pkg_id=%s' % order.sn,
            'pkg_name=%s' % order.flow_item_name.encode('utf-8'),
            'channel_code=%s' % FlOW_CHANNEL_CODE,
            'timestamp=%s' % t,
        ]
        params.append('md5=%s' % self.get_md5_str(order.flow_order_sn,order.phone,order.sn, order.flow_item_name, t))
        return "&".join(params)

    def get_md5_str(self, req_id, phone, pkg_id, pkg_name,timestamp):
        return encryhelper.md5_encry(
                str(req_id)+
                str(phone)+
                str(pkg_id)+
                str(FlOW_CHANNEL_CODE)+
                str(timestamp)+
                str(FLOW_KEY)
        )

    def update_flow_status(self, session, order, status, status_text):
        order.status = status
        order.status_text = status_text
        session.add(order)

    @staticmethod
    def callback_flow(session, flow_order_sn, code, msg, dal, r):
        session.begin()
        try:
            flow_order = session.query(TFlowOrder).filter(TFlowOrder.flow_order_sn == flow_order_sn).first()
            if flow_order == None:
                return
            if code != 1:
                user_info = dal.get_user(flow_order.uid, True)
                user_info.flow_card = user_info.flow_card + flow_order.flow_card
                dal.save_user(session, user_info)

                MessageManager.send_mail(session, user_info, 0,
                    title=u'流量充值',
                    content=u'流量充值失败，请验证你的手机号码',
                    type=0,
                )
            flow_order.status = code
            flow_order.status_text = msg
            flow_order.callback_msg = CODE_MAP[code]
            flow_order.callback_time = time.strftime('%Y-%m-%d %H:%M:%S')
            session.add(flow_order)
            session.commit()
        except Exception as e:
            # print e.message
            session.rollback()
        finally:
            return {'code': 1, 'text': 'success', 'ext': {}}

    def get_sn(self):
        return datetime.datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(100000, 999999))
