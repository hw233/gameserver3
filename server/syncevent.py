#coding: utf-8
import gevent
from threading import Lock,Condition
import time
import logging
import struct

class SyncEventHandler:
    def __init__(self):
        self.sync_events = {}
        self.lock = Lock()
        gevent.spawn(self.remove_timeout)

    def add_event(self,event):
        #self.lock.acquire()
        try:
            helper = SyncEventResponseHelper(event.tranId)
            self.sync_events[event.tranId] = helper
            return helper
        finally:
            pass
        #    self.lock.release()
        
    def set_response(self,resp):
        #self.lock.acquire()
        try:
            if resp.tranId not in self.sync_events:
                return None
            helper = self.sync_events[resp.tranId]
            helper.set_response(resp)
            del self.sync_events[resp.tranId]
        finally:
            pass
            #self.lock.release()    
     
    # 防止有些场景下，消息未自动删除
    def remove_timeout(self):
        while True:
            #self.lock.acquire()
            try:
                for k,v in self.sync_events.items():
                    if v.is_expired():
                        del self.sync_events[k]
            finally:
                pass
                #self.lock.release()
            gevent.sleep(300)    

class SyncEventResponseHelper:
    def __init__(self,tranId):
        self.condition = Condition()
        self.ready = False
        self.response = None
        self.start = int(time.time())
        self.transaction = tranId
     
    def is_expired(self): 
        return (int(time.time()) - self.start) > 200
        
    def is_ready(self):
        #self.condition.acquire()
        try:
            return self.ready
        finally:
            pass
        #    self.condition.release()
        
    def get_response(self,timeout = None):
        #self.condition.acquire()
        try:
            print("get_response now !!!!")
            if timeout == None:
                timeout = 180 # 3分钟
            if self.response == None:
                self.condition.wait(timeout)
            return self.response
        finally:
            #self.condition.release()
            pass
            
    def set_response(self,resp):
        #self.condition.acquire()
        try:
            self.response = resp
            self.ready = True
            #self.condition.notify()
        finally:
            pass
            #self.condition.release()         
       