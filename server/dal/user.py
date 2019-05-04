import gevent
from gevent import monkey;monkey.patch_all()
import json
import logging
import traceback
from sqlalchemy.sql import select, update, delete, insert, and_,or_, subquery, not_, null, func, text,exists
from sqlalchemy import desc

from util.commonutil import *

from db.connect import *
from db.user import *
from db.user_goldflower import *

from dal.base import *

class DalUser(DalObject):
    def __init__(self,data_access,uid):
        super(DalUser,self).__init__(data_access,uid,TUser,"u" + str(uid))

    def get_gold(self):
        gold = self.da.redis.hget(self.r_key,"gold")
        if gold == None:
            gold = 0
        else:
            gold = int(gold)
        self._data["gold"] = gold
        return gold

    def modify_gold(self,session,gold):
        row = None
        if session == None:
            session = Session()
            try :
                session.begin()
                row = session.query(TUser).with_lockmode("update").filter(TUser.id == self.obj_id).first()
                if row == None:
                    return None
                row.gold = 0 if row.gold + gold < 0 else row.gold + gold
                session.commit()
            except:
                traceback.print_exc()
                session.rollback()
                return None
            finally:
                if session == None:
                    session.close()
                    session = None
        else:
            row = session.query(TUser).with_lockmode("update").filter(TUser.id == self.obj_id).first()
            if row == None:
                return None
            row.gold = 0 if row.gold + gold < 0 else row.gold + gold
        self._data["gold"] = row.gold

        self.load_to_redis(gold=row.gold)
        return row.gold

class DalUserGoldFlower(DalObject):
    def __init__(self,data_access,uid):
        super(DalUserGoldFlower,self).__init__(data_access,uid,TUserGoldFlower,"ugf" + str(uid))
