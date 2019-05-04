# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import time

from message.base import *
from proto import struct_pb2 as pb2
from proto.lottery_pb2 import *

class EventSender:
    def __init__(self, table):
        self.table = table

    def game_running(self):
        event = create_client_event(GoldChangeEvent)
        self.table.game.get_gold_change_proto_struct(event.body)

        for uid, player in self.table.push_players.items():
            self.table.notify_one(event, player)

    def game_over(self):
        event = create_client_event(OverEvent)
        self.table.game.get_over_proto_struct(event.body)

        for uid, player in self.table.push_players.items():
            if player.user_info == None:
                player.lazy_load_user(self.table.service.dal)
            event.body.win_gold = int(player.win_gold)
            event.body.gold = player.get_gold()
            self.table.notify_one(event, player)
