#!/usr/bin/python
# -*- coding: utf-8 -*-
import ConfigParser
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

from lxclite import ls

# ###############################################################################
# "THE BEER-WARE LICENSE" (Revision 42):                                       #
# <lennartATlacerta.be> wrote this file. As long as you retain this notice you #
# can do whatever you want with this stuff. If we meet some day, and you think #
# this stuff is worth it, you can buy me a beer in return. Lennart Coopmans    #
################################################################################

# configuration
config = ConfigParser.SafeConfigParser()

try:
    config.readfp(open('/etc/lwp/lwp.conf'))
except IOError:
    print ' * missed /etc/lwp/lwp.conf file'
    try:
        # fallback on local config file
        config.readfp(open('../lwp.conf'))
    except IOError:
        print ' * cannot read config files. Exit!'
        sys.exit(1)

DEBUG = config.getboolean('global', 'debug')
DATABASE = config.get('database', 'file')

import sqlite3
import argparse
from time import time


def collect_data(con, group, timestamp):
    mem_rss = 0
    mem_cache = 0
    mem_swap = 0

    with open('/sys/fs/cgroup/lxc/%s/memory.stat' % (group,), 'r') as f:
        lines = f.read().splitlines()

    for line in lines:
        data = line.split()
        if data[0] == "total_rss":
            mem_rss = int(data[1])
        elif data[0] == "total_cache":
            mem_cache = int(data[1])
        elif data[0] == "total_swap":
            mem_swap = int(data[1])

    try:
        with open('/sys/fs/cgroup/lxc/%s/cpuacct.usage' % (group,), 'r') as f:
            cpu_usage = int(f.readline())
    except IOError:
        cpu_usage = 0

    con.execute("""\
                INSERT INTO graph_data (name, time, cpu_usage, mem_rss, mem_cache, mem_swap)
                VALUES (?,?,?,?,?,?)""", (group, timestamp, cpu_usage, mem_rss, mem_cache, mem_swap))


def init_database(con):
    con.execute("""\
                CREATE TABLE graph_data (
                  name TEXT NOT NULL,
                  time INTEGER NOT NULL,
                  cpu_usage INTEGER,
                  mem_rss INTEGER,
                  mem_cache INTEGER,
                  mem_swap INTEGER,
                  PRIMARY KEY (name,time)
                )
        """)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-db', '--database', default=DATABASE,
                        help="SQLite database file")
    #parser.add_argument('-c', '--containers', nargs='+',
    #                         help="LXC Containers to create charts for")
    parser.add_argument('--init', action='store_true',
                        help="Initialize the database")
    parser.add_argument('--debug', default=DEBUG, help="Active debug")

    args = parser.parse_args()

    con = sqlite3.connect(args.database)

    if args.init:
        init_database(con)
        sys.exit(0)

    containers = ls()
    for group in containers:
        collect_data(con, group, int(time()))

    con.commit()
    con.close()


if __name__ == "__main__":
    main()