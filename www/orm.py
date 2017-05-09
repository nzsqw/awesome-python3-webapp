#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import asyncio
import aiomysql

__author__ = 'nz'


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

# ORM mapping sql select manipulation to select function
# sql == sql statement, args == sql options, size == max query result, none
# means return all queries


@asyncio.coroutine
def select(sql, args, size=None):
    log(sql, args)
    global __pool

    with (yield from __pool) as conn:

        cur = yield from conn.cursor(aiomysql.DictCursor)

        yield from cur.execute(sql.replace("?", "%s"), args or ())

        if size:

            rs = yield from cur.fetchmany(size)

        else:

            rs = yield from cur.fetchall()

        yield from cur.close()

        logging.info("rows return %s" % len(rs))

        return rs

# execute function was used to add,delete and update the database


def execute(sql, args):
    log(sql)

    with (yield from __pool) as conn:

        if not conn.get_autocommit():

            yield from conn.begin()

        try:
            cur = yield from conn.cursor()

            yield from cur.execute(sql.replace("?", "%s"), args)

            affected = cur.rowcount

            yield from cur.close()

            if not conn.get_autocommit():

                yield from conn.commit()

        except BaseException as e:

            if not conn.get_autocommit():

                yield from conn.rollback()

            raise

        return affected


def create_args_string(num):

    L = []

    for n in range(num):

        L.append("?")

    return ', '.join(L)


class Field(object):

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return "<%s, %s:%s>" % (self.__class__.__name__, self.column_type, self.name)


class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl="varchar(100)"):
        super().__init__(name, ddl, primary_key, default)


class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, "bigint", primary_key, default)


class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, "boolean", False, default)


class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, "real", primary_key, default)


class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, "text", False, default)


class ModelMetaclass(type):

    # cls: 当前准备创建的类对象,相当于self
    # name: 类名,比如User继承自Model,当使用该元类创建User类时,name=User
    # bases: 父类的元组
    # attrs: 属性(方法)的字典,比如User有__table__,id,等,就作为attrs的keys

    def __new__(cls, name, bases, attrs):

        if name == "Model":
            return type.__new__(cls, name, bases, attrs)


        tableName = attrs.get("__table__", None) or name

        logging.info("found model: %s (table: %s)" % (name, tableName))

        mappings = dict()  # 保存类属性与数据库表列属性的关系 e.g. name=StringField(ddl="varchar50")

        fields = []         # 保存除主键外的属性

        primaryKey = None

        for k, v in attrs.items():

            if isinstance(v, Field):

                logging.info(" found mapping: %s ==> %s" % (k, v))

                mappings[k] = v

                if v.primary_key:

                    if primaryKey:

                        raise RuntimeError("Duplicate primary key for field: %s" % k)

                    primaryKey = k

                else:

                    fields.append(k)

        if not primaryKey:

            raise RuntimeError("Primary key not found")

        for k in mappings.keys():

            attrs.pop(k)

        escaped_fields = list(map(lambda f: "`%s`" % f, fields))

        attrs['__mappings__'] = mappings

        attrs['__table__'] = tableName

        attrs['__primary_key__'] = primaryKey

        attrs['__fields__'] = fields

        # select statement
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)

        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))

        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)

        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)

        return  type.__new__(cls, name, bases, attrs)


class Model(dict, metaclass=ModelMetaclass):

    def __init__(self, **kw):

        super(Model, self).__init__(**kw)

    def __getattr__(self, key):

        try:

            return self[key]

        except KeyError:

            raise AttributeError(r"'Model' object has no attribute'%s'" % key)

    def __setattr__(self, key, value):

        self[key] = value

    def getValue(self, key):

        return getattr(self, key, None)

    def getValueDefault(self, key):

        value = getattr(self, key, None)

        if value is None:

            field = self.__mappings__[key]

            if field.default is not None:

                value = field.default() if callable(field.default) else field.default

                logging.debug("using default value for %s: %s" % (key, str(value)))

                setattr(self, key, value)

        return value

    @classmethod
    @asyncio.coroutine
    def findNumber(cls, selectField, where=None, args=None):

        sql = ["select %s _num_ from `%s`" % (selectField, cls.__table__)]

        if where:

            sql.append("where")

            sql.append(where)

        rs = yield from select(' '.join(sql), args, 1)

        if len(rs) == 0:

            return None

        return rs[0]["_num_"]

    @asyncio.coroutine
    def save(self):

        args = list(map(self.getValueDefault, self.__fields__))

        args.append(self.getValueDefault(self.__primary_key__))

        rows = yield from execute(self.__insert__, args)

        if rows != 1:

            logging.warn("failed to insert record: affected rows: %s" % rows)

    @asyncio.coroutine
    def update(self):

        args = list(map(self.getValue, self.__fields__))

        args.append(self.getValue(self.__primary_key__))

        rows = yield from execute(self.__update__, args)

        if rows != 1:

            logging.warn("faild to update by primary key: affected rows %s" % rows)

    @asyncio.coroutine
    def remove(self):

        args = [self.getValue(self.__primary_key__)]

        rows = yield from  execute(self.__delete__, args)

        if rows != 1:

            logging.warn("failed to remove by primary key: affected rows %s" % rows)




























