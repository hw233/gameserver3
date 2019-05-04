# -*- coding: utf-8 -*-
__author__ = 'Administrator'

class EventSender:
    def __init__(self,manager):
        self.manager = manager

    def send_event(self,users,event):
        event_data = event.encode()
        for user in users:
            access_service = self.manager.service.redis.hget("online",user)
            if access_service == None:
                continue
            access_service = int(access_service)
            user = int(user)
            self.manager.service.send_client_event(access_service,user,event.header.command,event_data)

    def send_friend_message(self, event, user):
        if self.manager:
            return self.manager.notify_one(event,user)



    def make_friend_apply(self,event,user):
        if self.manager:
            return self.manager.notify_one(event,user)
