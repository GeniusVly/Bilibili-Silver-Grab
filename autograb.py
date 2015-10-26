#!/usr/bin/env python
#coding:utf-8
# Author:  Beining --<i#cnbeining.com>
# Co-op: SuperFashi
# Purpose: Auto grab silver of Bilibili
# Created: 10/22/2015
# https://www.cnbeining.com/
# https://github.com/cnbeining

import sys
import os
import requests
import json
import shutil
import getopt
from json import loads
import datetime
import time
import re
import logging
import traceback
try:
    from baiduocr import BaiduOcr
except ImportError:
    print("You need BaiduOcr module.")
    print("https://github.com/Linusp/baidu_ocr")
    exit()


# Dual support
try:
    input = raw_input
except NameError:
    pass

# LATER
#BAIDU_KEY =

#----------------------------------------------------------------------
def logging_level_reader(LOG_LEVEL):
    """str->int
    Logging level."""
    return {
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG
    }.get(LOG_LEVEL)

#----------------------------------------------------------------------
def generate_16_integer():
    """None->str"""
    from random import randint
    return str(randint(1000000000000000, 9999999999999999))

#----------------------------------------------------------------------
def safe_to_eval(string_this):
    """"""
    pattern = re.compile(r'^[\d\+\-\s]+$')
    match = pattern.match(string_this)
    if match:
        return True
    else:
        return False

#----------------------------------------------------------------------
def get_new_task_time_and_award(headers):
    """dict->tuple of int
    time_in_minutes, silver"""
    random_r = generate_16_integer()
    url = 'http://live.bilibili.com/FreeSilver/getCurrentTask?r=0.{random_r}'.format(random_r = random_r)
    response = requests.get(url, headers=headers)
    a = loads(response.content.decode('utf-8'))
    logging.debug(a)
    if a['code'] == 0:
        return (a['data']['minute'], a['data']['silver'])

#----------------------------------------------------------------------
def get_captcha_from_live(headers):
    """dict,str->str
    get the captcha link"""
    random_t = generate_16_integer()  #save for later
    url = 'http://live.bilibili.com/FreeSilver/getCaptcha?t=0.{random_t}'.format(random_t = random_t)
    response = requests.get(url, stream=True, headers=headers)
    filename = random_t + ".jpg"
    with open(filename, "wb") as f:
        f.write(response.content)
    result = os.path.abspath(filename)
    logging.debug(result)
    return result

#----------------------------------------------------------------------
def image_link_ocr(image_link):
    """link can be local file"""

    API_KEY = 'c1ff362dc90585fed08e80460496eabd'
    client = BaiduOcr(API_KEY, 'test')  # 使用个人免费版 API，企业版替换为 'online'

    res = client.recog(image_link, service='Recognize', lang='CHN_ENG')
    os.remove(image_link)
    logging.debug(res)

    return res['retData'][0]['word']

#----------------------------------------------------------------------
def send_heartbeat(headers):
    """"""
    random_t = generate_16_integer()
    url = 'http://live.bilibili.com/freeSilver/heart?r=0.{random_t}'.format(random_t = random_t)
    #print(url)
    response = requests.get(url, headers=headers)
    a = loads(response.content.decode('utf-8'))
    if a['code'] != 0:
        return False
    elif response.status_code != 200:
        print('WARNING: Unable to send heartbeat!')
        return False
    else:
        return True

#----------------------------------------------------------------------
def get_award(headers, captcha):
    """dict, str->int/str"""
    url = 'http://live.bilibili.com/freeSilver/getAward?r=0.{random_t}&captcha={captcha}'.format(random_t = generate_16_integer(), captcha = captcha)
    response = requests.get(url, headers=headers)
    a = loads(response.content.decode('utf-8'))
    if response.status_code != 200 or a['code'] != 0:
        print('WARNING: Unable to obtain!')
        print(a['msg'])
        return [int(a['code']), 0]
    else:
        return [int(a['data']['awardSilver']), int(a['data']['silver'])]

#----------------------------------------------------------------------
def award_requests(headers):
    url = 'http://live.bilibili.com/freeSilver/getSurplus?r=0.{random_t}'.format(random_t = generate_16_integer())
    response = requests.get(url, headers=headers)
    a = loads(response.content.decode('utf-8'))
    if response.status_code != 200 or a['code'] != 0:
        return False
    else:
        return True

#----------------------------------------------------------------------
def read_cookie(cookiepath):
    """str->list
    Original target: set the cookie
    Target now: Set the global header"""
    print(cookiepath)
    try:
        cookies_file = open(cookiepath, 'r')
        cookies = cookies_file.readlines()
        cookies_file.close()
        # print(cookies)
        return cookies
    except Exception:
        return ['']

#----------------------------------------------------------------------
def captcha_wrapper(headers):
    """"""
    captcha_link = get_captcha_from_live(headers)
    captcha_text = image_link_ocr(captcha_link).encode('utf-8')
    answer = ''
    if safe_to_eval(captcha_text):
        try:
            answer = eval(captcha_text)  #+ -
        except NameError:
            answer = ''
    return answer

#----------------------------------------------------------------------
def usage():
    """"""
    print("""Auto-grab

    -h: help:
    This.

    -c: cookies:
    Default: ./bilicookies
    location of cookies
    
    -l: Log Details
    Default: INFO
    INFO/DEBUG
    """)

#----------------------------------------------------------------------
def main(headers = {}):
    """"""
    try:
        time_in_minutes, silver = get_new_task_time_and_award(headers)
    except TypeError:
        print('You have reached the maximum free silver number, not for today anymore...')
        exit()
    print('ETA: {time_in_minutes} minutes, silver: {silver}'.format(time_in_minutes = time_in_minutes, silver = silver))
    now = datetime.datetime.now()
    picktime = now + datetime.timedelta(minutes = time_in_minutes) + datetime.timedelta(seconds = 10)
    while 1:
        if not send_heartbeat(headers):
            if ((picktime - datetime.datetime.now()).seconds / 60) <= 0 or ((picktime - datetime.datetime.now()).seconds / 60) > 10:
                while not award_requests(headers):
                    time.sleep(5)
                break
            print(str((picktime - datetime.datetime.now()).seconds / 60)+' minute(s) left...')
            time.sleep(60)
    answer = captcha_wrapper(headers)
    count = 1
    while answer == '':
        print('OCR ERROR!, Retry for #'+count)
        answer = captcha_wrapper(headers)
        count += 1
    award, nowsilver = get_award(headers, answer)
    #if award == -400 or award == -99:  #incorrect captcha/not good to collect
    if award < 0:  #error?
        #print('ere')
        for i in range(10):
            answer = captcha_wrapper(headers)
            count = 1
            while answer == '':
                print('OCR ERROR!, Retry for #'+count)
                answer = captcha_wrapper(headers)
                count += 1
            award, nowsilver = get_award(headers, answer)
            if award > 0:
                break
            else:
                print('Oops, retry #{i}'.format(i = i))
                time.sleep(5)
    print('Success, Award: '+str(award)+', now you have '+str(nowsilver)+' silvers.')
    return award

if __name__=='__main__':
    argv_list = []
    argv_list = sys.argv[1:]
    cookiepath,LOG_LEVEL = '', ''
    try:
        opts, args = getopt.getopt(argv_list, "hc:l:",
                                   ['help', "cookie=", "log="])
    except getopt.GetoptError:
        usage()
        exit()
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            exit()
        if o in ('-c', '--cookie'):
            cookiepath = a
            # print('aasd')
        if o in ('-l', '--log'):
            try:
                LOG_LEVEL = str(a)
            except Exception:
                LOG_LEVEL = 'INFO'
    logging.basicConfig(level = logging_level_reader(LOG_LEVEL))
    if cookiepath == '':
        cookiepath = './bilicookies'
    if not os.path.exists(cookiepath):
        print('Unable to open the cookie\'s file!')
        print('Please put your cookie in the file \"'+cookiepath+'\"')
        exit()
    cookies = read_cookie(cookiepath)[0]
    if cookies == '':
        print('Cannot read cookie! Please check it.')
        exit()
    headers = {
        'accept-encoding': 'gzip, deflate, sdch',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.16 Safari/537.36',
        'authority': 'live.bilibili.com',
        'cookie': cookies,
    }
    while 1:
        try:
            main(headers)
        except KeyboardInterrupt:
            exit()
        except Exception as e:
            print('Shoot! {e}'.format(e = e))
            traceback.print_exc()
