# -*- coding: utf-8 -*-
__author__ = 'Administrator'


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

from proto.access_pb2 import *
from proto.texas_pb2 import *
from proto.hall_pb2 import *
from proto.constant_pb2 import *
from proto.struct_pb2 import *


from util.handlerutil import *

from config.var import *

from robot import *
from texasroom import *


class TexasRobotService(GameService):
    def setup_route(self):
        self.registe_command(OnlineReq,OnlineResp,self.handle_user_online)


    def init(self):
        self.registe_handler(TexasSitTableResp,None,self.handle_sit_table)
        self.registe_handler(TexasBetActionResp,None,self.handle_bet)
        self.registe_handler(TexasQueryPlayerResp,None,self.handle_query_player)
        self.registe_handler(TexasLeaveTableResp,None,self.handle_leave_table)
        self.registe_handler(TexasLeaveInternalResp,None,self.handle_leave_internal)
        self.registe_handler(TexasUpdatePlayerResp,None,self.handle_update_player)

        self.registe_handler(TexasBetActionEvent,None,self.handle_bet_event)
        self.registe_handler(TexasRoundEvent,None,self.handle_round_event)
        self.registe_handler(TexasTableEvent,None,self.handle_table_event)
        self.registe_handler(TexasGameOverEvent,None,self.handle_over_event)
        self.registe_handler(TexasStartEvent,None,self.handle_start_event)

        self.registe_handler(NotificationEvent,None,self.handle_pass)

        self.redis = self.server.redis
        self.manager = RobotManager(self)
        gevent.spawn(self.handle_queue)

    @USE_TRANSACTION
    def handle_user_online(self,session,req,resp,event):
        print 'handle_user_online event................'
        self.manager.handle_user_online(session,req.body.uid)
        return False

    @ROBOT_HANDLER
    def handle_sit_table(self,session,user,event):
        print "=====> receive sit_table_resp",user,event.header.result
        if event.header.result != 0:
            return
        robot = self.manager.get_robot(user)
        if robot:
            robot.handle_sit_table_resp(event)

    @ROBOT_HANDLER
    def handle_start_event(self,session,user,event):
        print "=====> receive start event",user,event.body.table.texas_status,event.body.table.id
        robot = self.manager.get_robot(user)
        if robot:
            robot.handle_start_event(event)

    @ROBOT_HANDLER
    def handle_round_event(self,session,user,event):
        print "=====> receive round event",user,event.body.texas_status
        robot = self.manager.get_robot(user)
        if robot and not robot.play_timeout():
            robot.handle_round_event(event)

    @ROBOT_HANDLER
    def handle_over_event(self,session,user,event):
        print "=====> receive over event",user
        robot = self.manager.get_robot(user)
        if robot and not robot.play_timeout():
            robot.handle_over_event(event)


    @ROBOT_HANDLER
    def handle_bet_event(self,session,user,event):
        if user == event.body.player:
            robot = self.manager.get_robot(user)
            if robot and not robot.play_timeout():
                robot.handle_bet_event(event)
                # pass

    @ROBOT_HANDLER
    def handle_table_event(self,session,user,event):
        print 'table event:',user
        robot = self.manager.get_robot(user)
        if robot and not robot.play_timeout():
            robot.handle_table_event(event)

    @ROBOT_HANDLER
    def handle_leave_table(self,session,user,event):
        pass

    @ROBOT_HANDLER
    def handle_bet(self,session,user,event):
        pass

    @ROBOT_HANDLER
    def handle_query_player(self,session,user,event):
        pass

    @ROBOT_HANDLER
    def handle_leave_internal(self,session,user,event):
        pass

    @ROBOT_HANDLER
    def handle_update_player(self,session,user,event):
        pass

    @ROBOT_HANDLER
    def handle_pass(self,session,user,event):
        pass
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