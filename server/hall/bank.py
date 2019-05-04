# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import  time
from helper import datehelper

from db.bank_account import *
from db.mail import *



class BankAccount:

    def __init__(self, user_info):
        self.user_info = user_info

    def init_user_bank(self, session):
        user_bank = TBankAccount()
        user_bank.uid = self.user_info.id
        user_bank.gold = 0
        user_bank.diamond = 0
        user_bank.update_time = datehelper.get_today_str()
        user_bank.create_time = datehelper.get_today_str()
        session.add(user_bank)
        # print '------->init bank!!!!!!!!'

    def get_bank_gold(self, session, uid):
        user_bank = session.query(TBankAccount).filter(TBankAccount.uid == uid).first()
        if user_bank == None:
            return 0
        return user_bank.gold

    def save_bank_gold(self, session, uid, gold):
        return session.query(TBankAccount).filter(TBankAccount.uid == uid).update({
            TBankAccount.gold : gold
        })

    def send_transfer_mail(self,session, source_uid, user_info, **kwargs):
        # 加入邮件日志，待用户下次启动拉取
        mail = TMail()
        mail.from_user = source_uid
        mail.to_user = user_info if type(user_info) == int else user_info.id
        mail.sent_time = int(time.time())
        mail.title = kwargs.get('title')
        mail.content = kwargs.get('content')
        mail.type = kwargs.get('type')
        mail.diamond = kwargs.get('diamond',0)
        mail.gold = kwargs.get('gold',0)
        mail.items = kwargs.get('items')
        mail.gifts = kwargs.get('gifts')
        mail.received_time = kwargs.get('received_time')
        mail.state = 0 # 0 = 未收取
        session.add(mail)