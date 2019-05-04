# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from message.base import *
from proto import struct_pb2 as pb2
from proto.war_pb2 import *

class TableEventSender:
    def __init__(self, table):
        self.table = table

    def kick_player(self, uid):
        event = create_client_event(KickTableEvent)
        if self.table and self.table.players.has_key(uid):
            self.table.notify_one(event, self.table.players[uid])


class GameEventSender:
    def __init__(self, table, game):
        self.table = table
        self.game = game

    def send_game_started(self):
        event = create_client_event(WarGameStartEvent)
        self.table.get_proto_struct(event.body.table, True)

        if self.table:
            self.table.notify_event(event)

    def send_bet(self, player, player_action):
        event = create_client_event(WarGameActionEvent)
        self.game.bet_action_proto_struct(player, player_action, event.body)
        if self.game:
            self.table.notify_event(event)

    def send_bet_other(self):
        event = create_client_event(WarGameOtherActionEvent)
        self.game.get_other_proto_struct(event.body)
        if self.table:
            self.table.notify_event(event)

    def game_over(self):
        event = create_client_event(WarGameOverEvent)
        self.game.get_over_proto_struct(event.body)

        if self.game.big_winner.has_key('uid') and self.game.big_winner.has_key('win_gold'):
            if self.game.big_winner['win_gold'] > 0:
                self.table.players[self.game.big_winner['uid']].get_proto_struct(event.body.big_winner)
                self.game.player_result[self.game.big_winner['uid']].get_proto_struct(event.body.big_winner_result)


        for player_result in self.game.player_result.values():
            if self.table.players.has_key(player_result.uid) and self.table.players[player_result.uid].access_service != -1:
                player_result.get_proto_struct(event.body.my_result, player = self.table.players[player_result.uid], redis = self.table.redis)
            else:
                player_result.get_proto_struct(event.body.my_result)
            if self.table and self.table.players.has_key(player_result.uid):
                self.table.notify_one(event, self.table.players[player_result.uid])


