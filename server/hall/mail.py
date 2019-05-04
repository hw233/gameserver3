# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import time

from db.mail import *

class Mail:

    def __init__(self, from_user, to_user, title, type=0, diamond=0, gold=0, state=1, content = ''):
        self.mail = TMail()
        self.mail.from_user = from_user
        self.mail.to_user = to_user
        self.mail.sent_time = int(time.time())
        self.mail.title = title

        self.mail.type = type
        self.mail.diamond = diamond
        self.mail.gold = gold
        self.mail.state = state
        self.mail.content = content

    def send_mail(self, session):
        session.add(self.mail)
        session.flush()

