#coding:utf-8
import gevent
from gevent import monkey;monkey.patch_all()


import json
import logging
import traceback
import gevent

import binascii
from ctypes import *
from sqlalchemy.sql import select, update, delete, insert, and_, subquery, not_, null, func, text,exists
from sqlalchemy import desc

import random,time
from datetime import datetime

from services import GameService
from message.base import *
from message.resultdef import *

from db.connect import *

from proto.game_pb2 import *
from proto.chat_pb2 import *
from proto.access_pb2 import *
from proto.constant_pb2 import *
from proto.struct_pb2 import *
from proto.hall_pb2 import *
from proto.friend_pb2 import *

from util.handlerutil import *
from util.commonutil import *

from config.var import *

from robot import *

class RobotService(GameService):
    def setup_route(self):
        #self.registe_command(SitTableReq,SitTableResp,self.handle_sit_table)
        self.registe_command(OnlineReq,OnlineResp,self.handle_user_online)

    def init(self):
        self.registe_handler(SitTableResp,None,self.handle_sit_table)
        self.registe_handler(LeaveTableResp,None,self.handle_leave_table)
        self.registe_handler(KickOtherResp,None,self.handle_kick_other)
        self.registe_handler(SetPlayerReadyResp,None,self.handle_set_player_ready)
        self.registe_handler(BetActionResp,None,self.handle_bet_action_resp)
        self.registe_handler(GamePlayerReadyEvent,None,self.handle_player_ready)
        self.registe_handler(GameReadyEvent,None,self.handle_game_ready)
        self.registe_handler(GameCancelEvent,None,self.handle_game_cancel)
        self.registe_handler(GameStartEvent,None,self.handle_game_start)
        self.registe_handler(GameOverEvent,None,self.handle_game_over)
        self.registe_handler(GameTurnEvent,None,self.handle_game_turn)
        self.registe_handler(ChatEvent,None,self.handle_chat_event)
        self.registe_handler(NotificationEvent,None,self.handle_notification_event)

        self.registe_handler(EmotionEvent,None,self.handle_emotion_event)
        self.registe_handler(SendEmotionResp,None,self.handle_send_emotion_resp)

        self.registe_handler(BetActionEvent,None,self.handle_bet_action_event)
        self.registe_handler(TableEvent,None,self.handle_table_event)

        self.registe_handler(GetFriendsResp,None,self.handle_get_friends_resp)
        self.registe_handler(GetFriendAppliesResp,None,self.handle_get_friend_applies_resp)
        self.registe_handler(NotificationEvent,None,self.handle_notify_event)
        self.registe_handler(HandleFriendApplyResp,None,self.handle_handle_apply_resp)

        self.redis = self.server.redis

        self.manager = RobotManager(self)
        gevent.spawn(self.handle_queue)

    def onEvent(self, event):
        event_type = event.eventType
        if event_type not in self.event_handlers:
            logging.info(" No valid event handler for event:%d", event_type)
            return
        handler = self.event_handlers[event_type]
        try :
            if event.param1 > 0:
                handler(event.param1,event.eventData)
            else:
                handler(event)
        except:
            logging.exception("Error Is Happend for event %d", event_type)

    @USE_TRANSACTION
    def handle_user_online(self,session,req,resp,event):
        self.manager.handle_user_online(session,req.body.uid)
        return False


    @ROBOT_HANDLER
    def handle_sit_table(self,session,user,event):
        #print "=====> receive sit_table_resp",event.header.result,user
        robot = self.manager.get_robot(user)
        if robot:
            robot.handle_sit_table_resp(event)

    @ROBOT_HANDLER
    def handle_leave_table(self,session,user,event):
        #print "=====> receive leave_table_resp",event.header.result,user
        robot = self.manager.get_robot(user)
        if robot:
            robot.handle_leave_table_resp(event)


    @ROBOT_HANDLER
    def handle_kick_other(self,session,user,event):
        #print "=====> receive kick_other_resp",event.header.result,user
        pass

    @ROBOT_HANDLER
    def handle_set_player_ready(self,session,user,event):
        #print "=====> receive set_player_ready_resp",event.header.result,user
        robot = self.manager.get_robot(user)
        if robot:
            robot.handle_set_player_ready_resp(event)

    @ROBOT_HANDLER
    def handle_bet_action_resp(self,session,user,event):
        #print "=====> receive bet_action_resp",event.header.result,user
        robot = self.manager.get_robot(user)
        if robot:
            robot.handle_bet_action_resp(event)

    @ROBOT_HANDLER
    def handle_game_turn(self,session,user,event):
        #print "=====> receive game turn",event.body
        robot = self.manager.get_robot(user)
        if robot != None and robot.table_id == event.body.table_id:
            robot.handle_game_turn_event(event)
        else:
            if robot:
                robot.info(color.red("game turn event is received but invalid table[%d]"),event.body.table_id)
            else:
                logging.info(color.red("robot[%d] is not exist !"),user)

    @ROBOT_HANDLER
    def handle_player_ready(self,session,user,event):
        robot = self.manager.get_robot(user)
        if robot != None and robot.table_id == event.body.table_id:
            robot.handle_player_ready_event(event)
        else:
            if robot:
                robot.info(color.red("player ready event is received but invalid table[%d]"),event.body.table_id)
            else:
                logging.info(color.red("robot[%d] is not exist !"),user)

    @ROBOT_HANDLER
    def handle_notification_event(self,session,user,event):
        # do nothing
        pass

    @ROBOT_HANDLER
    def handle_game_ready(self,session,user,event):
        robot = self.manager.get_robot(user)
        if robot != None and robot.table_id == event.body.table_id:
            robot.handle_game_ready_event(event)
        else:
            if robot:
                robot.info(color.red("game ready event is received but invalid table[%d]"),event.body.table_id)
            else:
                logging.info(color.red("robot[%d] is not exist !"),user)

    @ROBOT_HANDLER
    def handle_game_cancel(self,session,user,event):
        robot = self.manager.get_robot(user)
        if robot != None and robot.table_id == event.body.table_id:
            robot.handle_game_cancel_event(event)
        else:
            if robot:
                robot.info(color.red("game cancel event is received but invalid table[%d]"),event.body.table_id)
            else:
                logging.info(color.red("robot[%d] is not exist !"),user)

    @ROBOT_HANDLER
    def handle_game_over(self,session,user,event):
        robot = self.manager.get_robot(user)
        if robot != None and robot.table_id == event.body.table_id:
            robot.handle_game_over_event(event)
        else:
            if robot:
                robot.info(color.red("game over event is received but invalid table[%d]"),event.body.table_id)
            else:
                logging.info(color.red("robot[%d] is not exist !"),user)

    @ROBOT_HANDLER
    def handle_game_start(self,session,user,event):
        robot = self.manager.get_robot(user)
        if robot != None and robot.table_id == event.body.table_id:
            robot.handle_game_start_event(event)
        else:
            if robot:
                robot.info(color.red("game start event is received but invalid table[%d]"),event.body.table_id)
            else:
                logging.info(color.red("robot[%d] is not exist !"),user)


    @ROBOT_HANDLER
    def handle_chat_event(self,session,user,event):
        robot = self.manager.get_robot(user)
        if robot != None:
            robot.handle_chat_event(event)

    @ROBOT_HANDLER
    def handle_emotion_event(self,session,user,event):
        robot = self.manager.get_robot(user)
        if robot != None:
            robot.handle_emotion_event(event)

    @ROBOT_HANDLER
    def handle_send_emotion_resp(self,session,user,event):
        robot = self.manager.get_robot(user)
        if robot != None:
            robot.handle_send_emotion_resp(event)

    @ROBOT_HANDLER
    def handle_bet_action_event(self,session,user,event):
        robot = self.manager.get_robot(user)
        if robot != None and robot.table_id == event.body.table_id:
            robot.handle_bet_action_event(event)
        else:
            if robot:
                robot.info(color.red("bet action event is received but invalid table[%d]"),event.body.table_id)
            else:
                logging.info(color.red("robot[%d] is not exist !"),user)

    @ROBOT_HANDLER
    def handle_table_event(self,session,user,event):
        robot = self.manager.get_robot(user)
        if robot:
            robot.handle_table_event(event)


    @ROBOT_HANDLER
    def handle_get_friends_resp(self,session,user,event):
        robot = self.manager.get_robot(user)
        if robot:
            robot.handle_get_friends_resp(event)

    @ROBOT_HANDLER
    def handle_get_friend_applies_resp(self,session,user,event):
        robot = self.manager.get_robot(user)
        if robot:
            robot.handle_get_friend_applies_resp(event)

    @ROBOT_HANDLER
    def handle_handle_apply_resp(self,session,user,event):
        robot = self.manager.get_robot(user)
        if robot:
            robot.handle_handle_apply_resp(event)



    @ROBOT_HANDLER
    def handle_notify_event(self,session,user,event):
        robot = self.manager.get_robot(user)
        if robot:
            robot.handle_notify_event(event)


    def handle_queue(self):
        while True:
            try:
                #data = self.redis.brpoplpush("queue" + str(self.server_id),"queue_debug")
                _,data = self.redis.brpop("queue" + str(self.serviceId))

                user,transaction,event_type = struct.unpack_from("llh",data)

                msg = data[struct.calcsize("llh"):]
                handler = self.event_handlers.get(event_type)
                if handler != None:
                    handler(user,msg)
                else:
                    logging.info("robot does not handle this event %d",event_type)
            except:
                traceback.print_exc()


    def stop(self):
        self.manager.shutdown()
