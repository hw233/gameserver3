# -*- coding: utf-8 -*-
__author__ = 'Administrator'

from db.connect import *
from db.user import *
from db.robot import *
from datetime import datetime,date
import random
session = Session()
session.begin()

for i in range(10048,10283):
    session.query(TUser).filter(TUser.id == i).update({
        TUser.gold : random.randint(50000,250000)
    })
    session.query(TRobot).filter(TRobot.uid == i).update({
	TRobot.state : 1
    });

session.commit()
