# -*- coding: utf-8 -*-
__author__ = 'Administrator'

# import sys
# sys.path.append('../')
import time
import json
from helper import datehelper

class TalkSession:
    def __init__(self, data, key = None):
        if data is None:
            self.talk = {}
        else:
            self.talk = json.loads(data)
        self.key = key
        self.data = data

    def add_talk(self, user, content, img = '', is_new = True, is_self = False):
        if self.talk is None or len(self.talk) == 0:
            self.talk['is_new'] = is_new
            self.talk['id'] = user
            self.talk['send_time'] = time.time()
            self.talk['user'] = {
                'name':user,
                'img':img
            }
            self.talk['messages'] = []
            self.talk['messages'].append({
                'content':content,
                'date':datehelper.get_today_str(),
                'self':is_self
            })
        else:
            self.talk['is_new'] = is_new
            self.talk['send_time'] = time.time()
            self.talk['messages'].append({
                'content':content,
                'date':datehelper.get_today_str(),
                'self':is_self
            })
	
        if self.key != None and type(self.key) == str and '_' in self.key:
            self.talk['to'] = int(self.key.split('_')[1])

    def set_back(self):
        self.talk['is_new'] = False

    def to_str(self):
        return json.dumps(self.talk)

    # def __repr__(self):
    #     return 'talk=%s' % json.dumps(self.talk)

class CustomerService:

    def __init__(self, redis):
        self.redis = redis
        self.talks = []

    def get_talks(self, talk_key = 'talk_session'):
        talks = self.redis.hgetall(talk_key)
        self.talks = [TalkSession(talk, key) for key, talk in talks.items()]
        self.sort_talks()
        return self.talks

    def sort_talks(self):
        self.talks.sort(cmp = self.cmp_sort_talks, reverse=True)
        # self.talks = sorted(self.talks, key=lambda x: x.talk.get('is_new'), reverse=True)

    def cmp_sort_talks(self, t1, t2):

        if t1.talk['is_new'] == t2.talk['is_new']:
            return cmp(t1.talk['send_time'], t2.talk['send_time'])
        if t1.talk['is_new']:
            return 1
        elif t2.talk['is_new']:
            return -1
        else:
            return 0


    def get_talk_user(self, user,talk_key='talk_session'):
    	talk = self.redis.hget(talk_key, user)
    	return TalkSession(talk, user)
		

    def update_talks(self, user, talks, talk_key='talk_session'):
        json_str = talks.to_str()
        self.redis.hset(talk_key, user, json_str)



if __name__ == '__main__':

    import redis
    r = redis.Redis(host='10.0.1.16', db=1, password='Wgc@123456')

    # 获得列表数据
    lists = CustomerService(r).get_talks()
    # for x in lists:
    #      print x.talk

    # set一个消息
    # cs = CustomerService(r)
    # talk = cs.get_talk_user(11991)
    # talk.add_talk(11991,'this is content',is_new=True, is_self=True)
    # cs.update_talks(11991, talk)

    # lists = [json.loads(x) for x in a.values()]
    # sorted(lists, key=lambda x: x.get('is_new'), reverse=True)

    # log = []
    # for x in lists:
    #     if x.get('is_new') == 1:
    #         log.insert(0,x)
    #     else:
    #         log.append(x)
    # print log

    # print sorted(lists, key=lambda x: x.get('is_new'), reverse=True)


    # print [json.loads(x) for x in a.values()]
    # a = {
    #     'id':11021,
    #     'user':{
    #         'name':11021,
    #         'img':''
    #     },
    #     'message':[
    #         {
    #             'message':'1this is hello',
    #             'date':'2016-12-12 12:12:12'
    #         },{
    #             'message':'2this is hello',
    #             'date':'2016-12-12 12:12:12'
    #         }
    #     ]
    # }
    # print json.dumps(a)