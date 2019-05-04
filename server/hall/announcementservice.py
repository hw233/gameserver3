#coding: utf-8

import json
import logging
import traceback
import socket
import gevent
import binascii
from ctypes import *

import random,time
from datetime import datetime
from datetime import date as dt_date
from datetime import time as dt_time



from services import GameService
from message.base import *
from message.resultdef import *

from proto.constant_pb2 import *
from proto.struct_pb2 import *
from proto.hall_pb2 import *

from util.handlerutil import *

from db.connect import *
from db.announcement import *
from helper import protohelper
from dal.core import *

from hall.announcement import *

class AnnouncementService(GameService):
    def setup_route(self):
        self.registe_command(QueryAnnouncementsReq,QueryAnnouncementsResp,self.handle_annoucement)

    def init(self):
        self.t_announcement = TAnnouncement()

    @USE_TRANSACTION
    def handle_annoucement(self,session,req,resp,event):

        annoucements = self.t_announcement.get_new_announcements(session, req.body.max_announcement_id)

        if len(annoucements) == 0:
            resp.header.result = RESULT_FAILED_ANNOUCEMENT_EMPTY
            return

        for item in annoucements:
            ann = Announcement(item)
            ann.get_proto_struct(resp.body.announcements.add())
        resp.header.result = 0