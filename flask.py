#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author NZ
from flask import Flask
from flask import request
app = Flask(__name__)

@app.route('/', methods=['GET','POST'])
def home():
    return '<h1>Home</h1>'

@app.route()

