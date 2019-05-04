# -*- coding: utf-8 -*-
__author__ = 'Administrator'

import hashlib
import re

# 32位md5加密
def md5_encry(md5_str):
    m2 = hashlib.md5()
    m2.update(md5_str)
    return m2.hexdigest()

def get_file_md5(filename):
        """
        大文件的MD5值
        :param src:
        :return:
        """
        if not os.path.isfile(filename):
            return
        myhash = hashlib.md5()
        f = file(filename,'rb')
        while True:
            b = f.read(8096)
            if not b :
                break
            myhash.update(b)
        f.close()
        return myhash.hexdigest()

def filter_emoji(input_str, replace_str = ''):
    try:
        # Wide UCS-4 build
        myre = re.compile(u'['
            u'\U0001F300-\U0001F64F'
            u'\U0001F680-\U0001F6FF'
            u'\u2600-\u2B55]+',
            re.UNICODE)
    except re.error:
        # Narrow UCS-2 build
        myre = re.compile(u'('
            u'\ud83c[\udf00-\udfff]|'
            u'\ud83d[\udc00-\ude4f\ude80-\udeff]|'
            u'[\u2600-\u2B55])+',
            re.UNICODE)
    return myre.sub(replace_str, input_str)

def has_emoji(input_str):
    try:
        # Wide UCS-4 build
        myre = re.compile(u'['
            u'\U0001F300-\U0001F64F'
            u'\U0001F680-\U0001F6FF'
            u'\u2600-\u2B55]+',
            re.UNICODE)
    except re.error:
        # Narrow UCS-2 build
        myre = re.compile(u'('
            u'\ud83c[\udf00-\udfff]|'
            u'\ud83d[\udc00-\ude4f\ude80-\udeff]|'
            u'[\u2600-\u2B55])+',
            re.UNICODE)
    if len(myre.findall(input_str)) > 0:
        return True
    return False

# if __name__ == '__main__':
#     print filter_emoji(u'I have a dog \U0001f436 . You have a cat \U0001f431 ! I smile \U0001f601 to you!')
