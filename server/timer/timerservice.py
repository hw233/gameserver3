#coding=utf-8
import time
import logging
from datetime import *
import traceback

from services import IService
from threading import Lock

from db.connect import *
from db.timer import *

from timers import *
import gevent
from gevent.pool import Pool
from gevent import monkey;monkey.patch_all()
           
class TimersManager:
    def __init__(self):
        self.timers = {}
        self.lock = Lock()        
        self.timers_duration = 20
        gevent.spawn(self.load_timers_from_database)
    
    def load_timers_from_database(self):
        while True:
            #self.lock.acquire()
            now = int(time.time())
            session = Session()
            try :
                rows = session.query(TTimer).filter(and_(
                                        TTimer.expired <= (now + self.timers_duration),
                                        #TTimer.expired >= (now - 60),
                                        )).all()
                #logging.info("===> load timers :" + str(len(rows)))
                for row in rows:
                    self._add_timer_from_db(row)
            except:
                logging.exception("װ�ض�ʱ�����ݳ����쳣")
            finally:
                session.close()
            #    self.lock.release()
            gevent.sleep(10)
            
    def get_and_remove_timers(self, timer = None):
        #self.lock.acquire()
        try :
            if timer == None:
                timer = int(time.time())
            if self.timers.has_key(timer):
                timers = self.timers[timer]
                del self.timers[timer]
            else:
                timers = {}
            while len(self.timers) != 0:
                min_timer = min(self.timers)
                
                if min_timer <= timer:
                    timers.update(self.timers[min_timer])
                    del self.timers[min_timer]
                else:
                    break           
        finally:
            #self.lock.release()
            pass
        
        return timers
        
    def _add_timer_from_db(self,timer):
        timers = None
        if  timer.expired in self.timers :
            timers = self.timers[timer.expired]
        else:
            timers = {}
            self.timers[timer.expired] = timers
        if timer.id not in timers:
            timers[timer.id] = timer    
            
    # ��ʱ������ʱ�¼�        
    def add_timer_from_service(self,timer_event):
        pass       
    
class TimerService(IService):
    def init(self):
        self.timers_manager = TimersManager()
        self.last_time = datetime.now()
        self.gevent_pool = Pool(10)
        gevent.spawn(self.on_second_timer)
        self.event_handlers = {
            
        }
    
    def on_second_timer(self):
        while True:
            #logging.info("Dida.")
            now = datetime.now()
            try :
                self.handle_normal_timer()
                
                for handler in get_second_handlers(now.second):
                    self.gevent_pool.spawn(self.handle_periodic_timer,handler)
                
                if now.minute != self.last_time.minute:
                    for handler in get_minute_handlers(now.minute):
                        self.gevent_pool.spawn(self.handle_periodic_timer,handler)
                if now.hour != self.last_time.hour:
                    for handler in get_hour_handlers(now.hour):
                        self.gevent_pool.spawn(self.handle_periodic_timer,handler)
                
                if now.day != self.last_time.day:
                    for handler in get_day_handlers(now.day):
                        self.gevent_pool.spawn(self.handle_periodic_timer,handler)
                
            except:
                logging.exception("��ʱ���������쳣")
            finally:
                self.last_time = now
            gevent.sleep(1)
            
    def handle_periodic_timer(self,handler):
        session = None
        try:
            session = Session()
            session.begin()
            handler(self,session)
            session.commit()
        except:
            session.rollback()
            logging.exception("�����Զ�ʱ�������쳣")
        finally:
            if session != None:
                session.close()
                session = None
               
            
    def handle_normal_timer(self):
        timers = self.timers_manager.get_and_remove_timers()
        if timers == None:
            return
        for timer in timers.values():
            self.gevent_pool.spawn(self.handle_one_timer,timer)
  
    def handle_one_timer(self,timer):
        if timer.event_id in TIMER_HANDLERS:
            handler = TIMER_HANDLERS[timer.event_id]
            session = None
            try:
                session = Session()
                session.begin()
                new_timer = session.query(TTimer).filter(TTimer.id == timer.id).first()
                if new_timer != None:
                    handler(self,session,new_timer)
                    session.delete(new_timer)
                session.commit()
            except:
                logging.exception("��ͨ��ʱ�������쳣 event=%d,user_id=%d,object_id=%d",timer.event_id,timer.uid,timer.object_id)
                session.rollback()
            finally:
                if session != None:
                    session.close()
                    session = None
  
    def onEvent(self,event):
        event_type = event.eventType
        if event_type not in self.event_handlers:
            logging.info("No valid event handler for event:%d", event_type)
            return 
        handler = self.event_handlers[event_type]
        try :
            handler(event)
        except:
            logging.exception("Error Is Happend for event %d", event_type)

    # ��ʱ������ʱ�¼�
    def handle_create_timer(self,event):
        pass
    
    
    
