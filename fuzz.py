#!/usr/bin/env python
# -*- utf8 -*-
# author=dave
# create=20150408

"""
* A Tool For Fuzzing Sub-domain.
* GitHub: https://github.com/Captain-D/FuzSub
* Version: 1.0
* SUPPORT TOP-LEVEL & SECOND-LEVEL
"""
import datetime
import sys
import random
import re
import requests
import os
import time
import itertools
from common.output import output_add, output_init, output_finished
from gevent.pool import Pool
from gevent import monkey, socket;
monkey.patch_os()

TOP_LEVEL = []
THREADS_NUM = 64
DNS_LIST = ['223.5.5.5', '223.6.6.6', '180.76.76.76']

# TODO
# 1.make this program can stop while receive sigterm.


def get_ban_ip(dns, domain):
    # In Case it's Pan analytical
    ban_ip = 'time out'
    while ban_ip == 'time out':
        try:
            ban_ip = find_ip_from_dns(dns, 'an9xm02d.' + domain)
        except Exception as e:
            print e
            ban_ip = 'time out'
    return ban_ip


def find_ip_from_dns(dns_server, sub_domain):
    # Core Content
    host = ''
    for i in sub_domain.split('.'):
        host += chr(len(i)) + i
    index = os.urandom(2)
    data = '%s\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00' \
           '%s\x00\x00\x01\x00\x01' % (index, host)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(15)
    s.sendto(data, (dns_server, 53))
    respond = s.recv(512)
    ip_list = []
    for j in re.findall("\xC0[\s\S]\x00\x01\x00\x01[\s\S]{6}([\s\S]{4})",
                        respond):
        ip = '.'.join(str(ord(ii)) for ii in j)
        ip_list.append(ip)
    ip_list.sort()
    return ip_list


def get_ip(sub_domain, ban_ip, category, domain):
    # Use Method find_ip_from_dns to Fetch ip
    global DNS_LIST, TOP_LEVEL
    if sub_domain == '' or sub_domain.startswith('.'):
        return
    dns_server = random.choice(DNS_LIST)
    try_count = 0
    while True:
        try:
            ip = find_ip_from_dns(dns_server, sub_domain)
            try_count = 0
            break
        except Exception as e:
            '''
            print "[-] Get Failed exception %s! " \
                  "Regetting... Domain: %s" % (str(e), sub_domain)
            '''
            try_count += 1
            time.sleep(3)  # sleep 3 seconds to avoid network error.
    if ip != ban_ip and ip != []:
        print "[+] <Found> %s" % sub_domain
        output_add(sub_domain, ip, category, domain)
        if category == "TOP-LEVEL":
            return sub_domain


def get_ip_x(args):
    return get_ip(*args)


def start_fuzz(domain):
    global TOP_LEVEL, DNS_LIST
    print "[*] Target: %s" % domain
    output_init(domain)
    # file_handle = open("./dict/dns.dict")
    # DNS_LIST = file_handle.read().split('\n')
    # In Case it's Pan analytical
    ban_ip = get_ban_ip(random.choice(DNS_LIST), domain)
    print "[*] %s" % ban_ip
    '''
    while not ban_ip:
        ban_ip = get_ban_ip(random.choice(DNS_LIST), domain)
    '''
    fuzz_top_domain_pool(domain, ban_ip)
    fuzz_second_domain_pool(domain, ban_ip)
    print "[*] Done!"
    output_finished(domain)


def fuzz_top_domain_pool(domain, ban_ip):
    print "[*] TOP-LEVEL DOMAIN FUZZING..."
    file_handle = open("./dict/top-level.dict")
    content_dict = file_handle.read().split('\n')
    if content_dict[-1] == '':
        del content_dict[-1]

    pool = Pool(THREADS_NUM)
    results = pool.map(get_ip_x, itertools.izip(
        map(lambda x: x + '.' + domain, content_dict),
        itertools.repeat(ban_ip),
        itertools.repeat('TOP-LEVEL'),
        itertools.repeat(domain)))
    TOP_LEVEL.extend([r for r in results if r])
    pool.terminate()
    print "[*] TOP-LEVEL DOMAIN FINISHED..."


def fuzz_second_domain_pool(domain, ban_ip):
    global TOP_LEVEL
    print "[*] SECOND-LEVEL DOMAIN FUZZING..."
    file_handle = open("./dict/second-level.dict")
    content_dict = file_handle.read().split('\n')
    pool = Pool(THREADS_NUM)

    pool.map(get_ip_x, itertools.izip(
        (str(sub) + '.' + str(top)
         for sub in content_dict for top in TOP_LEVEL),
        itertools.repeat(ban_ip),
        itertools.repeat('SECOND-LEVEL'),
        itertools.repeat(domain)))
    pool.terminate()
    print "[*] SECOND-LEVEL DOMAIN FINISHED..."


def domain_verify(doamin):
    full_domain = "http://%s" % doamin
    try:
        status = requests.get(full_domain, timeout=3).status_code
        print "[+] <[%s]> %s" % (status, full_domain)
    except Exception as  e:
        # Something to check whether the network problem
        print e
        pass


if __name__ == "__main__":
    start_time = datetime.datetime.now()
    print "[*] FuzSub is hot."
    if len(sys.argv) == 1:
        print "[-] Error! You should input the domain you want to Fuzz."
        print "[-] E.g. python fuzz.py foo.com"
    else:
        domain = sys.argv[1]
        # domain = "qq.com"
        start_fuzz(domain)
    end_time = datetime.datetime.now()
    print '[*] Total Time Consumption: ' + \
          str((end_time - start_time).seconds) + 's'
