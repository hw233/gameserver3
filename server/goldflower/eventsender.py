#coding: utf-8

import json
import logging
import traceback


import random,time

from collections import Counter
from datetime import datetime
from datetime import date as dt_date
from datetime import time as dt_time

from message.base import *
from message.resultdef import *
from proto.constant_pb2 import *
from proto.game_pb2 import *
from proto import struct_pb2 as pb2

class TableEventSender:
    def __init__(self,table):
        self.table = table

    def send_player_join(self,player):
        #print "send_player_join",player.uid,self.table.id
        event = create_client_event(TableEvent)
        
        event.body.table_id = self.table.id
        event.body.event_type = PLAYER_JOIN
        event.body.player = player.uid
        player.get_brief_proto_struct(event.body.player_brief)
        event.body.seat = player.seat
        if self.table:
            self.table.notify_event(event)


    def send_player_connect(self,player,connect):
        #print "send_player_connect",player.uid,connect,self.table.id
        event = create_client_event(TableEvent)
        
        event.body.table_id = self.table.id
        if connect :
            event.body.event_type = PLAYER_RECONNECTED
        else:
            event.body.event_type = PLAYER_DISCONNECTED
        event.body.player = player.uid
        #player.get_brief_proto_struct(event.body.player_brief)
        if self.table:
            self.table.notify_event(event) 

    def send_player_updated(self,player):
        event = create_client_event(TableEvent)

        event.body.table_id = self.table.id
        event.body.event_type = PLAYER_UPDATED
        event.body.player = player.uid
        player.get_brief_proto_struct(event.body.player_brief)
        if self.table:
            self.table.notify_event(event)

    def send_player_leave(self,player):
        #print "send_player_leave",player.uid,self.table.id
        event = create_client_event(TableEvent)
        
        event.body.table_id = self.table.id
        event.body.event_type = PLAYER_LEAVE
        event.body.player = player.uid
        #player.get_brief_proto_struct(event.body.player_brief)
        
        if self.table:
            self.table.notify_event(event)
        # since the player is leaved now ,so send it by uid
        self.table.notify_event_player(event,player)

    def send_player_kicked(self,kicker_uid,player):
        #print "send_player_kicked",player.uid,self.table.id
        event = create_client_event(TableEvent)
        
        event.body.table_id = self.table.id
        event.body.event_type = PLAYER_KICKED
        event.body.player = player.uid
        event.body.kicker = kicker_uid

        #player.get_brief_proto_struct(event.body.player_brief)
        
        if self.table:
            self.table.notify_event(event)
        # since the player is leaved now ,so send it by uid
        self.table.notify_event_player(event,player)

class GameEventSender:
    def __init__(self,table,game):
        self.table = table
        self.game = game
    
    def send_player_ready(self,uid,is_ready = True):
        #print "send_player_ready",uid,is_ready,self.table.id
        event = create_client_event(GamePlayerReadyEvent)
        
        event.body.table_id = self.table.id
        event.body.player = uid
        event.body.is_ready = is_ready
        
        if self.table:
            self.table.notify_event(event)  

    def send_game_ready(self,seconds):
        #print "send_game_ready",self.table.id
        event = create_client_event(GameReadyEvent)
        
        event.body.table_id = self.table.id
        event.body.seconds = seconds
        
        if self.table:
            self.table.notify_event(event)  

    def send_game_started(self): 
        #print "send_game_started",self.table.id,self.game
        event = create_client_event(GameStartEvent)
        
        event.body.table_id = self.table.id
        event.body.dealer = self.game.dealer.uid
        for gambler in self.game.gamblers.values():
            pb_player_gold = event.body.player_golds.add()
            pb_player_gold.uid = gambler.uid
            pb_player_gold.action_gold = gambler.action_gold
            pb_player_gold.bet_gold = gambler.bet_gold
            pb_player_gold.gold = gambler.get_gold()

        if self.table:
            self.table.notify_event(event) 
    
    def send_game_cancel(self):
        #print "send_player_cancel",self.table.id
        event = create_client_event(GameCancelEvent)
        
        event.body.table_id = self.table.id
        
        if self.table:
            self.table.notify_event(event)   

    def send_see_poker(self,uid):
        #print "send_player_see_poker",self.table.id,uid
        event = create_client_event(BetActionEvent)
        
        event.body.table_id = self.table.id
        event.body.action = SEE_POKER
        event.body.player = uid

        if self.table:
            self.table.notify_event(event)  

    def send_bet_follow(self,current_gambler,uid,gold):
        #print "send_bet_follow" ,self.table.id,uid,gold
        event = create_client_event(BetActionEvent)
        
        event.body.table_id = self.table.id
        event.body.action = FOLLOW
        event.body.player = uid
        event.body.action_gold = gold
        event.body.bet_gold = current_gambler.bet_gold
        event.body.gold = current_gambler.get_gold()

        if self.table:
            self.table.notify_event(event)

    def send_bet_add(self,current_gambler,uid,gold):
        #print "send_bet_add" ,self.table.id,uid,gold
        event = create_client_event(BetActionEvent)

        event.body.table_id = self.table.id
        event.body.action = ADD
        event.body.player = uid
        event.body.action_gold = gold
        event.body.bet_gold = current_gambler.bet_gold
        event.body.gold = current_gambler.get_gold()

        if self.table:
            self.table.notify_event(event)

    def send_bet_give_up(self,uid):
        #print "send_bet_give_up" ,self.table.id,uid
        event = create_client_event(BetActionEvent)
        
        event.body.table_id = self.table.id
        event.body.action = GIVE_UP
        event.body.player = uid

        if self.table:
            self.table.notify_event(event)
       
    def send_bet_compare(self,current_gambler,uid,other,gold,winner):
        #print "send_bet_compare" ,self.table.id,uid,other,gold,winner
        event = create_client_event(BetActionEvent)
        
        event.body.table_id = self.table.id
        event.body.action = COMPARE
        event.body.player = uid
        event.body.action_gold = gold
        event.body.bet_gold = current_gambler.bet_gold
        event.body.gold = current_gambler.get_gold()
        event.body.other = other
        event.body.compare_winner = winner

        if self.table:
            self.table.notify_event(event)

    def send_show_hand(self,current_gambler,uid,gold,winner):
        #print "send_show_hand" ,self.table.id,uid,gold
        event = create_client_event(BetActionEvent)
        
        event.body.table_id = self.table.id
        event.body.action = SHOW_HAND
        event.body.player = uid
        event.body.action_gold = gold
        event.body.bet_gold = current_gambler.bet_gold
        event.body.gold = current_gambler.get_gold()
        event.body.compare_winner = winner

        if self.table:
            self.table.notify_event(event)

    def send_current_turn(self,round,current_gambler):
        #print "send_current_turn" ,self.table.id,uid,self.game
        event = create_client_event(GameTurnEvent)
        
        event.body.table_id = self.table.id
        event.body.round = round
        event.body.current = current_gambler.uid

        if self.table:
            self.table.notify_event(event)

    def send_game_over_event(self,winner,win_gold,fee_gold,lucky_type,total_lucky_gold,lucky_gold):
        #print "send_game_over_event" ,self.table.id,winner,win_gold,fee_gold
        event = create_client_event(GameOverEvent)
        
        event.body.table_id = self.table.id
        event.body.winner = winner
        event.body.gold = win_gold
        event.body.fee = fee_gold

        if lucky_type != 0:
            event.body.lucky_gold.lucky_type = lucky_type
            event.body.lucky_gold.total_lucky_gold = total_lucky_gold
            event.body.lucky_gold.lucky_gold = lucky_gold

        for gambler in self.game.gamblers.values():
            gambler.pokers.get_proto_struct(event.body.pokers.add())
            
            pb_player_gold = event.body.player_golds.add()
            pb_player_gold.uid = gambler.uid
            pb_player_gold.action_gold = gambler.action_gold
            pb_player_gold.bet_gold = gambler.bet_gold
            pb_player_gold.gold = gambler.get_gold()

        if self.table:
            self.table.notify_event(event)    

if __name__ == '__main__':
    pass
