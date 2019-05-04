#coding: utf-8

from message.base import *
import random

class SimpleRoute:
    def __init__(self):
        self.cache = {}

    def get_any_service(self,server,header):
        '''随机发给任一服务'''
        if header.route >= 0:
            return header.route
        
        ids = self.cache.get(header.command,None)
        if ids == None:
            cmd = MessageMapping.get_message_def(header.command)
            if cmd == None:
                return None
            
            services = server.conf.services[cmd.service]
            ids = self.cache[header.command] = [svc.id for svc in services]
        
        if len(ids) == 1:
            return ids[0]    
        else:
            which = random.randint(0,len(ids) - 1)
            return ids[which]    

    def get_all_service(self,server,header):
        '''获取所有的服务'''
        ids = self.cache.get(header.command,None)
        if ids == None:
            cmd = MessageMapping.get_message_def(header.command)
            if cmd == None or cmd.service == None:
                return None
            services = server.conf.services[cmd.service]
            ids = self.cache[header.command] = [svc.id for svc in services]
        return ids
    
class UserRoute:
    def __init__(self):
        self.cache_servers = []
        self.cache = {}

    def get_any_service(self,server,header):
        ''' 随机发给任一服务'''
        if len(self.cache_servers) == 0:
            cache_services = server.conf.services["CacheService"]
            self.cache_servers = [svc.host.name for svc in cache_services]
            
        better_server = self.cache_servers[header.user % len(self.cache_servers)]
               
        ids = self.cache.get(header.command,None)
        if ids == None:
            cmd = MessageMapping.get_message(header.command)
            services = server.conf.services[cmd.service]
            ids = self.cache[header.command] = {}
            for svc in services:
                ids[svc.id] = svc.host.name
        
        if len(ids) == 1:
            return ids.keys()[0]
        else:
            for id,name in ids.items():
                if better_server == name:
                    return id
            which = random.randint(0,len(ids) - 1)   
            return ids.keys()[which]    


    def get_all_service(self,server,header):
        '''获取所有的服务'''
        ids = self.cache.get(header.command,None)
        if ids == None:
            cmd = MessageMapping.get_message_def(header.command)
            services = server.conf.services[cmd.service]
            ids = self.cache[header.command] = {}
            for svc in services:
                ids[svc.id] = svc.host.name
            
        return ids.keys()
    
ROUTE = SimpleRoute()
#ROUTE = UserRoute()