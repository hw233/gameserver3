# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from message.base import create_client_event

from proto.constant_pb2 import *
from proto import struct_pb2 as pb2
from proto.texas_pb2 import *

class TableEventSender:

    def __init__(self, table):
        self.table = table


    def send_player_updated(self,player):
        event = create_client_event(TableEvent)

        event.body.table_id = self.table.id
        event.body.event_type = PLAYER_UPDATED
        event.body.player = player.uid
        player.get_brief_proto_struct(event.body.player_brief)
        if self.table:
            self.table.notify_event(event)

    def send_player_join(self, player):
        event = create_client_event(TexasTableEvent)

        event.body.table_id = self.table.id
        event.body.event_type = PLAYER_JOIN
        event.body.player = player.uid
        player.get_brief_proto_struct(event.body.player_brief)
        event.body.seat = player.seat
        if self.table:
            self.table.notify_event(event)

    def send_player_connect(self,player,connect):
        #print "send_player_connect",player.uid,connect,self.table.id
        event = create_client_event(TexasTableEvent)

        event.body.table_id = self.table.id
        if connect :
            event.body.event_type = PLAYER_RECONNECTED
        else:
            event.body.event_type = PLAYER_DISCONNECTED
        event.body.player = player.uid
        #player.get_brief_proto_struct(event.body.player_brief)
        if self.table:
            self.table.notify_event(event)

    def send_player_kicked(self, uid):
        #print "send_player_kicked",player.uid,self.table.id
        event = create_client_event(TexasTableEvent)

        event.body.table_id = self.table.id
        event.body.event_type = PLAYER_KICKED
        event.body.player = uid
        event.body.kicker = -1

        #player.get_brief_proto_struct(event.body.player_brief)

        if self.table:
            self.table.notify_event(event)
        # since the player is leaved now ,so send it by uid
        # self.table.notify_event_player(event,player)

    def send_player_leave(self,player):
        #print "send_player_leave",player.uid,self.table.id
        event = create_client_event(TexasTableEvent)

        event.body.table_id = self.table.id
        event.body.event_type = PLAYER_LEAVE
        event.body.player = player.uid
        #player.get_brief_proto_struct(event.body.player_brief)

        if self.table:
            self.table.notify_event(event)
        # since the player is leaved now ,so send it by uid
        # self.table.notify_event_player(event,player)

class GameEventSender:

    def __init__(self, table, game):
        self.table = table
        self.game = game

    def send_start(self):
        event = create_client_event(TexasStartEvent)

        event.body.table.id = self.table.id
        event.body.table.texas_status =  self.game.status
        event.body.table.remain_seconds = int(self.game.get_remain_seconds(self.game.round_start_time) / 1000)
        if self.table:
            self.table.notify_event(event)

    def send_bet_add(self,uid, gambler, gold):
        #print "send_bet_add" ,self.table.id,uid,gold
        event = create_client_event(TexasBetActionEvent)

        event.body.table_id = self.table.id
        event.body.player = uid
        event.body.bet_type = ADD_BEI
        event.body.texas_status = self.game.status

        event.body.action_gold = gold
        event.body.bet_reward_gold = gambler.bet_reward_gold
        event.body.bet_gold = gambler.get_bet_gold()
        event.body.gold = gambler.player.get_gold()

        if self.table:
            self.table.notify_event(event)

    def send_bet_give_up(self,uid):
        #print "send_bet_give_up" ,self.table.id,uid
        event = create_client_event(TexasBetActionEvent)

        event.body.table_id = self.table.id
        event.body.player = uid
        event.body.bet_type = GIVEUP
        event.body.texas_status = self.game.status

        if self.table:
            self.table.notify_event(event)

    def send_bet_pass(self,uid):
        #print "send_bet_give_up" ,self.table.id,uid
        event = create_client_event(TexasBetActionEvent)

        event.body.table_id = self.table.id
        event.body.player = uid
        event.body.bet_type = PASS
        event.body.texas_status = self.game.status

        if self.table:
            self.table.notify_event(event)

    def send_bet_watch(self, uid):
        #print "send_bet_give_up" ,self.table.id,uid
        event = create_client_event(TexasBetActionEvent)

        event.body.table_id = self.table.id
        event.body.player = uid
        event.body.bet_type = WATCH
        event.body.texas_status = self.game.status

        if self.table:
            self.table.notify_event(event)

    def send_bet_bet(self,uid, gold, gambler):
        #print "send_bet_give_up" ,self.table.id,uid
        event = create_client_event(TexasBetActionEvent)

        event.body.table_id = self.table.id
        event.body.player = uid
        event.body.bet_type = BET
        event.body.texas_status = self.game.status

        event.body.action_gold = gold
        event.body.bet_reward_gold = gambler.bet_reward_gold
        event.body.bet_gold = gambler.get_bet_gold()
        event.body.gold = gambler.player.get_gold()

        if self.table:
            self.table.notify_event(event)

    def send_hand_poker(self):
        #print "send_bet_give_up" ,self.table.id,uid
        event = create_client_event(TexasRoundEvent)

        event.body.table_id = self.table.id
        event.body.texas_status = self.game.status

        for player in self.table.players.values():
            if player.uid in self.game.gamblers.keys():
                if len(event.body.player_pokers) > 0:
                    for _ in xrange(len(event.body.player_pokers)):
                        event.body.player_pokers.pop()

                gambler = self.game.gamblers[player.uid]
                if not gambler.is_watch():
                    for poker in gambler.pokers:
                        poker.get_proto_struct(event.body.player_pokers.add())

            if self.table:
                self.table.notify_event_player(event, player)

    def send_public_pokers(self, public_pokers = None):
        #print "send_bet_give_up" ,self.table.id,uid
        event = create_client_event(TexasRoundEvent)

        event.body.table_id = self.table.id
        event.body.texas_status = self.game.status

        if self.game != None:
            if public_pokers != None:
                for poker in public_pokers:
                    poker.get_proto_struct(event.body.public_pokers.add())
            else:
                for poker in self.game.public_pokers:
                    poker.get_proto_struct(event.body.public_pokers.add())

        if self.table:
            self.table.notify_event(event)

    def send_game_over(self):
        #print "send_bet_give_up" ,self.table.id,uid
        event = create_client_event(TexasGameOverEvent)

        event.body.table_id = self.table.id
        for poker in self.game.public_pokers:
            poker.get_proto_struct(event.body.public_pokers.add())

        for gambler in self.game.gamblers.values():
            if gambler.is_add_bei():
                gambler.get_final_poker_proto_struct(event.body.final_player_pokers.add())
                gambler.get_own_proto_struct(event.body.own_pokers.add())

            gambler.get_result_proto_struct(event.body.player_results.add())

        self.game.dealer.get_own_proto_struct(event.body.own_pokers.add())
        self.game.dealer.get_final_poker_proto_struct(event.body.final_player_pokers.add())

        if self.table:
            self.table.notify_event(event)