# -*- coding: utf-8 -*-
from logging.handlers import TimedRotatingFileHandler

__author__ = 'Administrator'

import sys
import logging
from sysconfig import *

if __name__ == '__main__':
    import os
    os.chdir(sys.path[0])
    file = "system.ini"
    if len(sys.argv) > 1:
        myselfName = sys.argv[1]
    else:
        logging.error("需要输入server名字")
        sys.exit()

    console = False

    for i in range(len(sys.argv)):
        if sys.argv[i] == "-console":
            console = True
        elif sys.argv[i] == "-conf":
            file = sys.argv[i+1]


    if console:
        logging.basicConfig(level=logging.DEBUG, \
                        format='%(asctime)s %(levelname)s %(message)s', \
                        stream=sys.stdout, \
                        filemode='a')
    else:
        log_fmt = '%(threadName)s %(asctime)s %(levelname)s %(message)s'
        formatter = logging.Formatter(log_fmt)

        log_file_handler = TimedRotatingFileHandler(filename='logs/'+myselfName, when="midnight", interval=1, backupCount=2)
        log_file_handler.setFormatter(formatter)

        logging.basicConfig(level=logging.INFO,format=log_fmt)
        logger = logging.getLogger()
        logger.addHandler(log_file_handler)
        # logging.basicConfig(level=logging.DEBUG, \
        #                 format='%(asctime)s %(levelname)s %(message)s', \
        #                 stream=sys.stdout, \
        #                 filemode='a')
        # logging.basicConfig(level=logging.DEBUG, format="%(threadName)s:%(asctime)s %(levelname)s %(message)s",
        #                filename= "./" + myselfName + ".log",filemode='a')
        # logging.config.fileConfig("log4p.conf")

    logging.info("System Starting -> loading configuration %s" , file)
    conf = SystemConfig(file,myselfName)