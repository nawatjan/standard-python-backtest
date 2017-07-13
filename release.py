#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul  4 17:24:32 2017

@author: z

This script use standard python libaries for multiple instrument backtesting
which can be relatively slow, but should be able to run in any python3 version
without a problem (have not been extensively tested).

To look at the result in chart format I recommended using matplotlib to visualize.
"""

import csv
import os
from datetime import datetime
from collections import namedtuple, OrderedDict, defaultdict
#from matplotlib import pyplot as plt

#This is where your csv is saved
STOCK_PATHS = ['/home/z/PythonScripts/NewDataFetcher/listed']

#Sample csv format
#Date,o,h,l,c,v
#2011-03-09,11.1,11.1,11.1,11.1,10000
#2011-03-10,11.1,11.1,11.1,11.1,10000
#2011-03-11,11.1,11.1,11.1,11.1,10000
#2011-03-14,11.1,11.1,11.1,11.1,10000
#2011-03-15,11.1,11.1,11.1,11.1,10000

class Instrument:
    '''
    base class for any instrument
    '''
    
    def __init__(self, name, data_dict):
        self.name = name
        self.data_dict = data_dict
        
    def convert_to_date(self, string):
        '''
        convert string key to datetime type
        '''
        if isinstance(string, str):
            string = datetime.strptime(string, '%Y-%m-%d')
        return string
        
    def __getitem__(self, key):
        ''' 
        Get input as datetime or '%Y-%m-%d' and give record of that date
        '''
        return self.data_dict[self.convert_to_date(key)]
    
class Stock(Instrument):
    '''
    a class hold stock historical data and other information
    '''
    
    def __init__(self, symbol, data_dict=None):
        super(Stock, self).__init__(symbol, data_dict)
        
    @property
    def symbol(self):
        return self.name
    
    @property
    def data_dict(self):
        ''' Return datetime of all records '''
        return self._data_dict
    
    @data_dict.setter
    def data_dict(self, value):
        ''' set data_dict and create some useful field o, h, l, c, v '''
        self._data_dict = value
        if self._data_dict is not None:
            self._index = {}
            for i, key in enumerate(self._data_dict):
                self._index[key] = i
            self._dates = list(self._data_dict.keys())
        
    def get_index(self, date):
        return self._index[self.convert_to_date(date)]
    
    def is_avaliable(self, date):
        return self.convert_to_date(date) in self._data_dict
    
    @property
    def dates(self):
        ''' Return datetime of all records '''
        return self._dates
    
    def __repr__(self):
        ''' Return name and earliest date to lastest date '''
        return '{0} | From {1} to {2}'.format(self.name, min(self.data_dict.keys()), max(self.data_dict.keys()))
    
    def __str__(self):
        return self.symbol
    
Tick = namedtuple('Tick', ['o', 'h', 'l', 'c', 'v'])
Order = namedtuple('Order', ['name', 'position_size'])
  
def parse_date(date):
    ''' parse date in Y-M-D to datetime '''
    dt = datetime.strptime(date, '%Y-%m-%d')
    return dt
        
def read_csv(path) -> dict:
    '''
    read stored csv file
    
    path: path to csv file
    
    expected csv with header of Date(Y-M-D), o, h, l, c, v
    
    return data_dict (type OrderedDict)
    '''
    #Use regular dict first
    data_dict = {}
    with open(path, 'r') as csvio:
        reader = csv.reader(csvio, delimiter=',')
        #Exclude first line
        next(reader)
        #Read the data in each line
        for row in reader:
            #Expected data in order of date, open, high, low, close, volume
            date, o, h, l, c, v = row
            data_dict[parse_date(date)] = Tick(float(o), float(h), float(l), float(c), float(v))
    #Use OrderedDict instead and sorted from earlier to lastest
    data_dict = OrderedDict(sorted(data_dict.items(), key=lambda x: x[0]))
    return data_dict
        
def load_stock(sym) -> Stock:
    '''
    load stock for a given symbol by searching through files in STOCK_PATHS
    
    return s (type Stock)
    '''
    #Create stock instance named *sym
    s = Stock(sym)
    data_dict = None
    #Search given folder for a stock named *sym
    for folder in STOCK_PATHS:
        fname = '{0}/{1}.csv'.format(folder, sym)
        #If the stock named *sym exist read it out
        if os.path.exists(fname):
            data_dict = read_csv(fname)
    #If the stock named *sym is not exist raise Exception
    if data_dict is None:
        raise ValueError('{0} not exist'.format(sym))
    s.data_dict = data_dict
    return s

abc = load_stock('ABC')

#==============================================================================
# Single stock backtesting with simple 20-days breakout rule 
#==============================================================================

def backtest(stock, dates=None):
    if dates is None:
        dates = stock.dates
    equity = 1
    buy, sell, hold = False, False, False
    equity_curve = [equity]
    
    for i in range(20, len(dates) - 1):
        #Current date
        curdate = dates[i]
        #Resistance of previous 20 day max close
        resistance = max(stock[dates[j]].c for j in range(i-20, i))
        #Support of previous 20 day min close
        support = min(stock[dates[j]].c for j in range(i-20, i))
        
        #If current stock price < support trigger sell signal
        if stock[curdate].c < support:
            buy, sell = False, True
        #If current stock price > resistance trigger buy signal
        elif stock[curdate].c > resistance:
            buy, sell = True, False
        else:
            buy, sell = False, False
            
        nextdate = dates[i + 1]
        
        #Add carry hold variable to indicate if the postion is held from previous day
        if not hold:
            carry_hold = False
        else:
            carry_hold = True
        if buy:
            hold = True
        if sell:
            if hold:
                #Sell at open next day if there's held position, 
                #increase equity gained from different of current close and next day close
                equity *= 1 + (stock[nextdate].o - stock[curdate].c) / stock[curdate].c
                hold = False
        else:
            if hold:
                if carry_hold:
                    #Increase equity gained from different of current close and next day close
                    equity *= 1 + (stock[nextdate].c - stock[curdate].c) / stock[curdate].c
                else:
                    #Increase equity gained from different of next day close and next day open
                    equity *= 1 + (stock[nextdate].c - stock[nextdate].o) / stock[nextdate].o
        
        equity_curve.append(equity)
        
    return equity_curve, dates[19 : -1]
    
equity_curve, dates = backtest(abc)
#plt.title(abc.name)
#plt.plot(dates, equity_curve)

#==============================================================================
# Portfolio backtesting with simple 20-days breakout rule
#==============================================================================

class NotEnoughDataPoints(Exception):
    pass

def safe_lookback(stock, field, date, lookback_period):
    last = stock.get_index(date)
    first = last - lookback_period
    if first < 0:
        raise NotEnoughDataPoints('Not enough data points')
    l = [getattr(stock[d], field) for d in stock.dates[first:last]]
    return l

def ref_date(stock, date, look_back):
    last = stock.get_index(date)
    if last - look_back < 0:
        raise NotEnoughDataPoints('Not enough data points')
    if last - look_back >= len(stock.dates):
        raise NotEnoughDataPoints('No more future points')
    return stock.dates[last - look_back]

class NotEnoughCash(Exception):
    pass

class Portfolio:
    
    def __init__(self, cash):
        self.cash = cash
        self._equity = defaultdict(float)
        self._equity_price = {}
        self._buy_list = defaultdict(list)
        self._sell_list = defaultdict(list)
        
    @property
    def value(self):
        '''
        calculate current portfolio value based in internal equity price
        and amount of cash
        '''
        return self.cash + sum([self._equity[name] * self._equity_price[name] for name in self._equity])
    
    def update(self, name, price):
        ''' update the price of named instrument '''
        self._equity_price[name] = price
        
    def excute_buy(self, date):
        ''' excute buy order in buylist on given date '''
        for order in self._buy_list[date]:
            #Check if cash is enough for an order
            if self.cash > order.position_size:
                #Increse number of equity
                self._equity[order.name] += order.position_size / self._equity_price[order.name]
                #Reduce cash in portfolio
                self.cash -= order.position_size 
            else:
                raise NotEnoughCash
        
    def excute_sell(self, date):
        ''' excute sell order in selllist on given date '''
        for order in self._sell_list[date]:
            #Increas cash in portfolio
            self.cash += self._equity[order.name] * self._equity_price[order.name]
            #Remove all holding position
            self._equity[order.name] = 0
        
    def queue_buy(self, name, position_size, date):
        ''' add buy order to buylist given name of instrument, position, date '''
        buy_list = self._buy_list[date]
        buy_list.append(Order(name, position_size))
    
    def queue_sell(self, name, date):
        ''' add buy order to buylist given name of instrument, date '''
        sell_list = self._sell_list[date]
        sell_list.append(Order(name, 0))
        
#Load all stocks in selected folder        
stocks = os.listdir(STOCK_PATHS[0])
stocks = [load_stock(stock.replace('.csv', '')) for stock in stocks]
#Build a list of all dates avaliable in records
dates = set()
for stock in stocks:
    dates = dates.union(set(stock.dates))
dates = list(sorted(dates))
#Initialize some variable
buy, sell = False, False
hold = {k.name : False for k in stocks}
#Create portfolio with 100000 cash
p = Portfolio(100000)
#Create equity curve to keep track of how the portfolio progress
equity_curve = [p.value]

#Loop through all the dates but exclude first 20 records and last record
for i in range(20, len(dates) - 1):
    #Set common dates
    curdate = dates[i]
    #Update stock price to open of current day and excuting buys and sells
    for stock in stocks:
        name = stock.name
        if stock.is_avaliable(curdate): #Check if there's record of current date
            p.update(name, stock[curdate].o)
    try:
        p.excute_buy(curdate)
    except NotEnoughCash:
        #This exception is made to continue the backtest 
        #if the cash in portfolio is not enough
        pass
    p.excute_sell(curdate)
    
    #Update stock price to close of current day
    for stock in stocks:
        name = stock.name
        if stock.is_avaliable(curdate):
            p.update(name, stock[curdate].c)
    #Append to equity_curve
    equity_curve.append(p.value)
    
    #Set amount of cash to convert to equity in this case 5% of lastest portfolio value
    position_size = 0.05 * equity_curve[-1]
    for stock in stocks:
        try:
            name = stock.name
            #Check if the given date has a stock record
            if not stock.is_avaliable(curdate):
                continue
            else:
                nextdate = ref_date(stock, curdate, -1)
            #Resistance of previous 20 day max close
            resistance = max(safe_lookback(stock, 'c', curdate, 20))
            #Support of previous 20 day min close
            support = min(safe_lookback(stock, 'c', curdate, 20))
            
            #If current stock price < support trigger sell signal
            if stock[curdate].c < support:
                buy, sell = False, True
            #If current stock price > resistance trigger buy signal
            elif stock[curdate].c > resistance:
                buy, sell = True, False
            else:
                buy, sell = False, False
            
            #Add carry hold variable to indicate if the postion is held from previous day
            if not hold[name]:
                carry_hold = False
            else:
                carry_hold = True
            if buy:
                hold[name] = True
            if sell:
                if hold[name]:
                    #Sell at open next day if there's held position,
                    p.queue_sell(name, nextdate)
                    hold[name] = False
            else:
                if hold[name]:
                    if carry_hold:
                        pass
                    else:
                        p.queue_buy(name, position_size, nextdate)
        except NotEnoughDataPoints:
            #This exception is made to continue the backtest 
            #if the cash in safe_looknack has less than specify amount of points
            #to return in this case 20.
            pass
    
#plt.plot(dates[19 : -1], equity_curve)