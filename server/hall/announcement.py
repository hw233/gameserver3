# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from sqlalchemy import and_
from proto import struct_pb2 as pb2
from db.announcement import *
from helper import datehelper

class Announcement:

    def __init__(self, t_announce):
        self.id = t_announce.id
        self.category = t_announce.category
        self.title = t_announce.title
        self.content = t_announce.content
        self.sort = t_announce.sort
        self.has_action = t_announce.has_action
        self.action = t_announce.action
        self.popup = t_announce.popup


    def get_proto_struct(self, pb_annoucement):
        if pb_annoucement is None:
            pb_annoucement = pb2.Annoucement()
        pb_annoucement.id = self.id
        pb_annoucement.category = self.category
        pb_annoucement.title = self.title
        pb_annoucement.content = self.content
        pb_annoucement.sort = self.sort
        pb_annoucement.has_action = self.has_action
        pb_annoucement.action = self.action
        pb_annoucement.popup = self.popup
        return pb_annoucement


