# -*- coding: utf-8 -*-
__author__ = 'Administrator'
from db.user import *
from message.resultdef import *
from config.var import *

from mail_text import *

def send_mail(from_user,to_user,title,content,items = None,gifts = []):
    pass

def send_mail_charge_success(uid,name,money,gold):
    mail_title = MAIL_TEMP_CHARGE_SUCCESS % ()
    mail_content = MAIL_TEMP_CHARGE_SUCCESS % (name,money,gold)

    send_mail(-1,uid,mail_title,mail_content)

def send_mail_welcome(uid,name):
    pass


