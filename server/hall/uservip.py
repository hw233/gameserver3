# -*- coding: utf-8 -*-
__author__ = 'Administrator'

# import os
# import sys
# sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import vip


def get_vip(charge):
    lst_len = len(vip.VIP_CONF)
    for index in range(lst_len):
        if index + 1 == lst_len:
            if charge >= vip.VIP_CONF[index].get('charge'):
                return vip.VIP_CONF[index]['level']
            else:
                return vip.VIP_CONF[index - 1]['level']

        if charge >= vip.VIP_CONF[index].get('charge') and charge < vip.VIP_CONF[index + 1].get('charge'):
            return vip.VIP_CONF[index]['level']


if __name__ == '__main__':
    # print get_vip(100)
    pass
