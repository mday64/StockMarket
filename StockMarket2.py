#!python3

import itertools
import collections
import csv
import datetime

# See also more_itertools.windowed
def subranges(iterable, length):
    '''
    Yield all subranges of length @length from @iterable.

    >>> for s in subranges("abcdefghijklmnopqrstuvwxyz", 7):
    ...     print(s)
    ... 
    ('a', 'b', 'c', 'd', 'e', 'f', 'g')
    ('b', 'c', 'd', 'e', 'f', 'g', 'h')
    ('c', 'd', 'e', 'f', 'g', 'h', 'i')
    ('d', 'e', 'f', 'g', 'h', 'i', 'j')
    ('e', 'f', 'g', 'h', 'i', 'j', 'k')
    ('f', 'g', 'h', 'i', 'j', 'k', 'l')
    ('g', 'h', 'i', 'j', 'k', 'l', 'm')
    ('h', 'i', 'j', 'k', 'l', 'm', 'n')
    ('i', 'j', 'k', 'l', 'm', 'n', 'o')
    ('j', 'k', 'l', 'm', 'n', 'o', 'p')
    ('k', 'l', 'm', 'n', 'o', 'p', 'q')
    ('l', 'm', 'n', 'o', 'p', 'q', 'r')
    ('m', 'n', 'o', 'p', 'q', 'r', 's')
    ('n', 'o', 'p', 'q', 'r', 's', 't')
    ('o', 'p', 'q', 'r', 's', 't', 'u')
    ('p', 'q', 'r', 's', 't', 'u', 'v')
    ('q', 'r', 's', 't', 'u', 'v', 'w')
    ('r', 's', 't', 'u', 'v', 'w', 'x')
    ('s', 't', 'u', 'v', 'w', 'x', 'y')
    ('t', 'u', 'v', 'w', 'x', 'y', 'z')
    '''
    i = iter(iterable)
    subrange = tuple(itertools.islice(i, length))
    if len(subrange) < length:
        return
    else:
        yield subrange
    
    for item in i:
        subrange = subrange[1:] + (item,)
        yield subrange

#
# Access and manipulate historical stock market data.
# See http://www.irrationalexuberance.com/
#
# The columns are:
#   Date        {year:int}.{month:int} (note: month 10 may appear as "1"; month 1 is "01")
#   Price       :float
#   Dividend    :float (trailing 12 months)
#   Earnings    :float (trailing 12 months?)
#   CPI         :float
#   Date        :float (with month expressed as a fractional year)
#   GS10        :float (yield on 10-year treasury bond; overstates return on cash)
#   Real Price  :float (inflation-adjusted price)
#   Real Div    :float (inflation-adjusted dividend)
#   Real Earn   :float (inflation-adjusted earnings)
#   CAPE        :float-or-text (cyclically adjusted P/E; Price/10-year-Earnings-Average)
#
# See TB3MS.csv <https://fred.stlouisfed.org/series/TB3MS> for 3-month Treasury Bill
# yield.  This could be used for interest on cash.  Though it seems too high for actual
# interest earned on cash in a brokerage account.
#
# Should I just assume that cash earns 0%, or that it matches inflation?
#

# Is this the best name?  Should it be something like MarketData or ShillerData?
SP500 = collections.namedtuple('SP500', 'date close dividend earnings CPI GS10 '+
    'real_price real_div real_earnings')

# Refactor this a bit?
#       Need a filter for Shiller's formatting vs. Yahoo Finance
#       Need a way to parse or pass column info
def read_shiller(fn="ie_data-2.csv"):
    def float_or_none(string):
        if string == '':
            return None
        else:
            return float(string)
    
    with open(fn, mode='r') as f:
        lines = iter(f)

        # Keep only the lines that start with a number (the year.month)
        lines = itertools.dropwhile(lambda l: not l[0].isdigit(), lines)
        lines = itertools.takewhile(lambda l: l[0].isdigit(), lines)

        reader = csv.reader(lines)
        for row in reader:
            try:
                year, month = row[0].split('.')
                if month == "1":
                    month = "10"
                year, month = int(year), int(month)
                date = datetime.date(year, month, 1)

                close, dividend, earnings, cpi = [float_or_none(x) for x in row[1:5]]
                gs10, real_price, real_div, real_earnings = [float_or_none(x) for x in row[6:10]]
                yield SP500(date, close, dividend, earnings, cpi, gs10,
                    real_price, real_div, real_earnings)
            except ValueError:
                # Likely an empty string for dividend, earnings, CPI or GS10
                break

# Should this be YahooData?
YahooFinance = collections.namedtuple('YahooFinance', 'date open high low close adj_close volume')
def read_yahoo(fn='^GSPC.csv'):
    with open(fn, mode='r') as f:
        reader = csv.reader(f)
        next(reader)    # skip over column headers
        for row in reader:
            try:
                year, month, day = [int(i) for i in row[0].split('-')]
                date = datetime.date(year, month, day)
                values = (float(i) for i in row[1:])
                yield YahooFinance(date, *values)
            except ValueError:
                continue

class Decline(collections.namedtuple('Decline', 'peak trough recovery percent')):
    def summarize(self):
        peak, trough, recovery, percent = self
        result = f'{peak.date}: {peak.close:7.2f}  '
        result += f'{trough.date}: {trough.close:7.2f}  '
        result += f'{recovery.date}: {recovery.close:7.2f}  '
        result += f'{percent:6.2%}'
        return result

# TODO: Should this take a @min_percent parameter?
def declines(market_data_seq):
    market_data = iter(market_data_seq)
    tick = next(market_data)
    
    try:
        while True:
            # Find the peak before the decline
            peak = tick
            tick = next(market_data)
            while tick.close > peak.close:
                peak = tick
                tick = next(market_data)
            
            # Find the trough and recovery points
            trough = tick
            while tick.close < peak.close:
                if tick.close < trough.close:
                    trough = tick
                tick = next(market_data)
            recovery = tick

            percent = (peak.close - trough.close) / peak.close

            yield Decline(peak, trough, recovery, percent)
    except StopIteration:
        pass

#
# For now, maintains its entire balance in shares of stock
#
# TODO: Should we round the number of shares (eg., to 5 places)?
#
class Portfolio(object):
    def __init__(self, initial_balance, stock_price):
        self.shares = initial_balance / stock_price
    
    def balance(self, stock_price):
        # TODO: Round to cents?
        return self.shares * stock_price
    
    def receive_dividend(self, dividend_per_share, stock_price):
        # Implicitly reinvests dividends
        # Note: caller is responsible for determining the amount of the
        # dividend per period (for each time this method is called).
        dividend_amount = self.shares * dividend_per_share
        self.shares += dividend_amount / stock_price

    def withdraw(self, amount, stock_price):
        self.shares -= amount / stock_price
    
    def __repr__(self):
        return f'{self.__class__.__name__}(shares={self.shares})'

#
# TODO: Need a history of the portfolio balance, stock prices, and Consumer Price Index.
# Should that be a property of the Portfolio object, or should it be separate?
#

#
# I would like to be able to customize/parameterize the following:
#   * Algorithm for adjusting withdrawal amount
#       * Adjust up by inflation, typically
#       * Might depend on balance or stock price history
#           * Portfolio up enough, ratchet up the withdrawal
#               * Should there be a parameter to control the new target percentage?
#           * In a down year, perhaps decrease the withdrawal (before/after adjusting for inflation)
#   * Algorithm/data about asset mix (cash, stock, bonds, etc.)
#       * Need to be able to provide current balance based on Shiller data
#       * Need to be able to make a withdrawal, including rebalancing asset classes as needed
#       * Should probably pass in current month's Shiller market data
#   * Initial withdrawal rate/percentage
#   * Secondary withdrawal percentage (eg., when the portfolio has grown substantially)
#   * Length of retirement (or is that the caller's responsibility?)
#       * Might need to know, to adjust withdrawal amount based on time remaining
#   * How many withdrawals during the year?  (Start with 4 - quarterly)
#   * How often to adjust the withdrawal amount?
#
# I'd like it to return a sequence of absolute balance, and either inflation-adjusted balance
# or Consumer Price Index.  Should it return an indication of insufficient funds, or deduce
# that from a negative balance and/or short output sequence?
#
# Maybe there should be a debug log associated with the output.  (See io.StringIO and logging)
#
# TODO: Simulate receiving of dividends
#
# TODO: The withdrawal rate should really be the initial withdrawal rate, specified as an
# annual amount/percentage.
#
# TODO: Should the market data be quarterly or monthly?
def simulate_withdrawals(market_data_seq, withdrawal_rate=0.01, initial_balance=1000000.00):
    market_data = iter(market_data_seq)
    tick = next(market_data)
    portfolio = Portfolio(initial_balance, tick.close)
    month = tick.date.month
    withdrawal_amount = round(initial_balance * withdrawal_rate, 2)
    balance_history = [(initial_balance, tick)]
    for tick in market_data:
        portfolio.withdraw(withdrawal_amount, tick.close)
        balance = portfolio.balance(tick.close)
        assert balance >= 0
        balance_history.append((balance, tick))
        if tick.date.month == month:
            # Adjust the withdrawal for inflation
            withdrawal_amount = round(withdrawal_amount * 1.025, 2)
    return balance_history        

def adjust_withdrawal_for_inflation(withdrawal_amount, balance_history):
    # Suppose we're adjusting annually.  Month #0 is when retirement started.
    # We would be making withdrawals on months #0, #3, #6, #9, #12, etc.
    # Month #12 (the 13th month) is when we'd do the first adjustment.
    #
    # Hmmm.  I wonder if the same function/object should be used to make the
    # withdrawals, and adjust the withdrawal amount?  That way, it could
    # consistently be quarterly, annually, or whatever.  It would be easy to
    # first make the adjustment, then make the withdrawal.  Perhaps the
    # withdrawal amount should be part of the history of the portfolio.
    #
    # Note that a different object needs to be responsible for maintaining
    # the portfolio balance and asset composition.  For example, it might
    # need to sell stocks to satisfy a withdrawal (in which case it needs
    # to update the number of shares of stock).

    months = len(balance_history)

    # Has it been an integral number of years since the start?
    if months > 12 and (months - 1) % 12 == 0:
        # Adjust the withdrawal_amount by the last year's inflation
        withdrawal_amount *= balance_history[-1][1].CPI / balance_history[-13][1].CPI
    
    # TODO: Add a rule to increase the withdrawal when the portfolio has grown enough (10%?)
    # TODO: Add a rule to decrease the withdrawal (slightly; 3-4%) after down years?
    # Note: Both of the above should probably be controlled by options.
    
    return withdrawal_amount

def main():
    for decline in declines(read_yahoo()):
        if decline.percent >= 0.05:
            print(decline.summarize())

if __name__ == '__main__':
    main()
