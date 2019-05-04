# -*- coding: utf-8 -*-
__author__ = 'Administrator'
from config.var import *

import urllib
import urllib2
import hashlib
import json
import md5

from helper import encryhelper
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

class SMS:
    def __init__(self):
        self.conf = SMS_CONF
        self.conf['zc_sms']['password'] = self.password_md5()

    def get_random_code(self):
        return ''.join([str(i) for i in random.sample(range(0, 9), 4)])

    def password_md5(self):
        return encryhelper.md5_encry(self.conf['zc_sms']['password'])

    def send_code(self, mobile):
        if mobile == None or mobile == '':
            return (False,'')
        code = self.get_random_code()
        self.conf['zc_sms']['mobile'] = mobile
        self.conf['zc_sms']['content'] = self.conf['tpl'].replace('@',code)+self.conf['sign']

        data = urllib.urlencode(self.conf['zc_sms'])

        request = urllib2.Request(self.conf['url'] + "?"+data)
        response = urllib2.urlopen(request)
        result = response.read()

        return True,json.loads(result), code

if __name__ == '__main__':
    # print SMS().send_code('13727853917')

    sms = SMS()
    print sms.send_code('17727853917')
    # print sms.send_code('17727853913')
    # print sms.send_code('17727853913')