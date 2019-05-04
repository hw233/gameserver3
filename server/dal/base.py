#coding:utf8

from util.commonutil import *
from datetime import datetime,date

from db.connect import *

class DalObject(object):
    def __init__(self,data_access,obj_id,table_class,redis_key):
        self._data = {}
        self.obj_id = obj_id
        self.da = data_access
        self.meta_table = table_class._sa_class_manager.mapper.tables[0]
        self.table_class = table_class
        self.r_key = redis_key

    def get_real_value(self,k,v):
        if v == None:
            return None
        python_type = self.meta_table.columns[k].type.python_type
        if python_type == datetime:
            return datetime.strptime(v,"%Y-%m-%d %H:%M:%S")
        elif python_type == date:
            return datetime.strptime(v,"%Y-%m-%d").date()
        elif python_type == int:
            try:
                return  int(v)
            except Exception as e:
                # print e.message
                pass
        return python_type(v)

    def __setattr__(self, key, value):
        if key in ["obj_id","r_key","_data","da","meta_table","table_class"]:
            super(DalObject,self).__setattr__(key,value)
            return
        self._data[key] = value

    def __getattr__(self,item):
        if item in ["obj_id","r_key","_data","da","meta_table","table_class"]:
            return super(DalObject,self).__getattribute__(item)
        return self._data.get(item,None)

    def load_from_database(self,session = None):
        session_created = False
        if session == None:
            session = get_context("session")

        if session == None:
            session = Session()
            session_created = True
        try :
            row = session.query(self.table_class).filter(self.table_class.id == self.obj_id).first()
            if row == None:
                return False
        finally:
            if session_created:
                session.close()
                session = None

        data = {}
        for f in dir(self.table_class):
            if f.startswith("_"):
                continue
            v = getattr(row,f)
            if v == None:
                continue
            data[f] = v
        self._data = data
        self.load_to_redis()
        return True

    def load(self,session = None):
        data = self.load_from_redis()
        if len(data) == 0:
            if session == None:
                session = get_context("session")
            row = session.query(self.table_class).filter(self.table_class.id == self.obj_id).first()
            if row == None:
                return False

            for f in dir(self.table_class):
                if f.startswith("_"):
                    continue
                v = getattr(row,f)
                if v == None:
                    continue
                data[f] = v
            self._data = data
            self.load_to_redis()
        else:
            self._data = data

        return True

    def save(self,session):
        row = session.query(self.table_class).with_lockmode("update").filter(self.table_class.id == self.obj_id).first()
        if row == None:
            row = self.table_class()

        for k,v in self._data.items():
            setattr(row,k,v)

        session.add(row)
        self.load_to_redis()

    def load_to_redis(self,**kw):
        for k,v in self._data.items():
            if v == None:
                del self._data[k]

        if len(kw) == 0:
            self.da.redis.hmset(self.r_key,self._data)
        else:
            self.da.redis.hmset(self.r_key,kw)

        self.da.redis.expire(self.r_key,3600)

    def load_from_redis(self):
        data = self.da.redis.hgetall(self.r_key)
        new_data = {}
        for k,v in data.items():
           new_data[k] = self.get_real_value(k,v)

        return new_data