#coding: utf-8

import json
import logging
import traceback

from sqlalchemy.sql import select, update, delete, insert, and_,or_, subquery, not_, null, func, text,exists
from sqlalchemy import desc

import random,time
from datetime import datetime
from datetime import date as dt_date
from datetime import time as dt_time


from services import GameService
from message.resultdef import *

from proto.constant_pb2 import *
from proto.mail_pb2 import *

from db.connect import *
from db.role import *
from db.mail import *
from db.chat import *

from helper import protohelper
from util.handlerutil import *
from util.commonutil import *


class MailService(GameService):
    def setup_route(self):
        self.registe_command(FetchMailReq,FetchMailResp,self.handle_fetch_mail)
        self.registe_command(ReceiveAttachmentReq,ReceiveAttachmentResp,self.handle_fetch_mail)
        self.registe_command()
        self.event_handlers = {
            FetchMailReq.DEF.Value("ID"):self.handle_fetch_mail,
            ReceiveAttachmentReq.DEF.Value("ID"):self.handle_receive_attachment,
        }
        
     

    @USE_TRANSACTION
    def handle_fetch_mail(self,session,req,resp,event):
        mails = session.query(TMail).filter(and_(or_(TMail.to_user == req.header.user,TMail.to_user <= 0),TMail.sent_time > req.body.when)).all()
        for mail in mails:
            protohelper.set_mail(resp.body.mails.add(),mail)

        resp.header.result = 0
        
    @USE_TRANSACTION
    def handle_receive_attachment(self,session,req,resp,event):
        mail = session.query(TMail).filter(and_(or_(TMail.to_user == req.header.user,TMail.to_user <= 0),TMail.id == req.body.mail_id)).first()
        if mail == None:
            resp.header.result = -1
            return 
        if mail.received > 0 :
            resp.header.result = -2
            return


    

                        
if __name__ == "__main__":
    pass
