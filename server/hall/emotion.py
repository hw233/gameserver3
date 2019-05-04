# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from message.base import *
from message.resultdef import *

from config.var import *
from proto.chat_pb2 import *

from helper import protohelper

class Emotion:
    def __init__(self, service, from_user, table_id, table, target_id, emotion_id, count):
        self.from_user = from_user
        self.table_id = table_id
        self.table = table
        self.target_id = target_id
        self.emotion_id = emotion_id
        self.count = count
        self.service = service

    def send(self, session):
        self.emotion_fee()
        self.service.da.save_user(session, self.from_user)
        self.create_emotion_event()

    def emotion_fee(self,):
        self.from_user.gold = self.from_user.get_gold() - self.emotion_gold()

    def create_emotion_event(self):
        event = create_client_event(EmotionEvent)
        event.body.sender = self.from_user.id
        event.body.table_id = self.table_id
        event.body.target_player = self.target_id
        event.body.emotion_id = self.emotion_id
        event.body.count = self.count
        event_data = event.encode()

        for user in self.table:
            access_service = self.service.redis.hget("online",user)
            if access_service == None:
                continue
            access_service = int(access_service)
            user = int(user)
            self.service.send_client_event(access_service,user,event.header.command,event_data)

    def validate(self):
        if self.gold_enough() == False:
            return RESULT_FAILED_NO_ENOUGH_GOLD, False

        code, result = self.in_table(  )
        return code, result

    def gold_enough(self):
        return self.from_user.get_gold() >= self.emotion_gold()

    def emotion_gold(self):
        return  EMOTION_ONCE_GOLD * self.count

    def in_table(self):
        table_users = [int(x) for x in self.table.keys()]

        if self.from_user.id not in table_users:
            return RESULT_FAILED_INVALID_NOT_EXISTS, False

        if self.target_id not in table_users:
            return RESULT_FAILED_INVALID_NOT_EXISTS, False

        return 0, True

    def set_result(self, pb_result):
        protohelper.set_result(pb_result,
                               gold=self.from_user.get_gold(),
                               diamond=self.from_user.diamond,
                               incr_gold=-self.emotion_gold())


