#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'nz'

import logging
import asyncio
import aiomysql

def log(sql, arg=()):
    logging.info("SQL: %s" % sql)

# Creating global database connecting pool

@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info("create database connection pool...")
    global __pool

    __pool = yield from aiomysql.create_pool(
            host       = kw.get("host", "localhost"),
            port       = kw.get("port", 3306),
            user       = kw["user"],
            password   = kw["password"],
            db         = kw["database"],
            charset    = kw.get("charset", "utf8"),
            autocommit = kw.get("autocommit", True),

            maxsize    = kw.get("maxsize", 10),
            minsize    = kw.get("minsize", 1),
            loop       = loop
            )

#ORM mapping sql select manipulation to select function
# sql == sql statement, args == sql options, size == max query result, none
# means return all queries
@asyncio.coroutine
def select(sql,args,size=None):
    log(sql,args)
    global __pool

#In python the with keyword is used when working with unmanaged resources (like file streams).
# It is similar to the using statement in VB.NET and C#.
# It allows you to ensure that a resource is "cleaned up" when the code that uses it finishes running, even if exceptions are thrown.
# It provides 'syntactic sugar' for try/finally blocks.
    with (yield from __pool) as conn:







