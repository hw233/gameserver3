# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import json






class Friend:

    def __init__(self, redis, user):
        self.user = user
        self.my_friends = []

    def get_list_by_page(self, page, pagesize):
        pass

    def get_other_offline(self, redis, other):
        exists = redis.hexists('online', other)
        if exists > 0:
            return True
        return False

    def load_my_friends(self, session):
        self.my_friends = session.query(TFriend).filter(TFriend.apply_uid == self.user).all()