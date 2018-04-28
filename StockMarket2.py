#!python3

import itertools
from collections import namedtuple
import csv
import datetime
import statistics

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
SP500 = namedtuple('SP500', 'date close dividend earnings CPI GS10 '+
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
YahooFinance = namedtuple('YahooFinance', 'date open high low close adj_close volume')
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

TBill = namedtuple('TBill', 'date rate')
def read_tbills(fn='TB3MS.csv'):
    with open(fn, mode='r') as f:
        reader = csv.reader(f)
        headers = next(reader)    # skip over column headers
        assert(headers == ['DATE', 'TB3MS'])
        for row in reader:
            try:
                year, month, day = [int(i) for i in row[0].split('-')]
                date = datetime.date(year, month, day)
                rate = float(row[1])/100.0
                yield TBill(date, rate)
            except ValueError:
                continue

def read_market_data():
    MarketData = namedtuple('MarketData', 'date close dividend CPI interest')
    shiller = read_shiller()
    tbills = dict(read_tbills())
    for i in shiller:
        interest = tbills.get(i.date, 0.0)
        yield MarketData(i.date, i.close, i.dividend, i.CPI, interest)

class Decline(namedtuple('Decline', 'peak trough recovery percent')):
    def summarize(self):
        peak, trough, recovery, percent = self
        result = f'{peak.date}: {peak.close:7.2f}  '
        result += f'{trough.date}: {trough.close:7.2f}  '
        result += f'{recovery.date}: {recovery.close:7.2f}  '
        result += f'{percent:6.2%}'
        return result

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
# TODO: Should there be a separate mechanism to set the current stock price?
#       That would enable us to have a more accurate max_balance.
#

#
# Used for a history of the portfolio balance, withdrawal, and Consumer Price Index.
# Should that be a property of the Portfolio object, or should it be separate?
# Should it include stock and/or bond prices?  If so, just include the market data?
#
# Note: the balance item is the balance after the withdrawal and dividend
PortfolioHistoryItem = namedtuple('PortfolioHistoryItem', 'date withdrawal balance stock_price cpi')

PeriodsResult = namedtuple('PeriodsResult', [
    'survivability', 'sustainability',
    'balance_cgr_median', 'balance_cgr_mean', 'balance_cgr_std',
    'withdrawal_cgr_median', 'withdrawal_cgr_mean', 'withdrawal_cgr_std',
    'periods'])
Period = namedtuple('Period', 'date survived sustained min_real max_real last_real growth_rate_real history')

class Portfolio(object):
    def __init__(self,
                 withdrawals_per_year = 4,
                 annual_withdrawal_rate=0.04,
                 initial_balance=1000000.00,
                 cash_cushion = False,
                 cash_cushion_target = 3,       # Years of withdrawals
                 cash_use_threshold = 0.90,     # Percent of portfolio max balance
                 cash_rebuild_threshold = 1.0,  # Percent of portfolio max balance
                 cash_rebuild_rate = 1.5,
                 paycut = False,
                 paycut_threshold = 0.90,       # If portfolio is less than this much of maximum,
                 paycut_rate = 0.97,            # decrease the withdrawal to this much
                 raise_enable = False,
                 raise_threshold = 1.10,        # If portfolio is at least this much of prior year,
                 raise_rate = 1.10,             # increase the withdrawal by this much
                 ratchet = False,
                 ratchet_to_rate = 0.035,       # Increase withdrawal to this rate
                 verbose = False):
        self.shares = 0.0       # Number of shares of stock
        self.cash = 0.0         # Amount of cash, in dollars
        self.max_balance = 0.0  # Highest balance seen previously, used for cash cushion
        self.withdrawals_per_year = withdrawals_per_year
        self.annual_withdrawal_rate = annual_withdrawal_rate
        self.initial_balance = initial_balance
        self.annual_withdrawal = 0.0
        self.cash_cushion = cash_cushion
        self.cash_cushion_target = cash_cushion_target
        self.cash_use_threshold = cash_use_threshold
        self.cash_rebuild_threshold = cash_rebuild_threshold
        self.cash_rebuild_rate = cash_rebuild_rate
        self.paycut = paycut
        self.paycut_threshold = paycut_threshold
        self.paycut_rate = paycut_rate
        self.raise_enable = raise_enable
        self.raise_threshold = raise_threshold
        self.raise_rate = raise_rate
        self.ratchet = ratchet
        self.ratchet_to_rate = ratchet_to_rate
        self.verbose = verbose
    #
    # A Cash Cushion: keeping part of the portfolio in cash, to be used
    # during market declines.
    #
    # cash_cushion: False
    #   Set to true to enable a cash cushion.  (Note: we could derive
    #   this from cash cushion target; 0 means no cushion.  My intuition
    #   says that a separate flag is better.)
    # cash_cushion_target: 3
    #   The desired amount of cash, relative to the annual withdrawal amount
    # cash_use_threshold: 0.90
    #   A percentage of maximum portfolio value.  If the portfolio's
    #   value drops below this amount, use cash instead of selling stock
    #   to make a withdrawal.  If the portfolio is above this value,
    #   sell stock to make withdrawals.
    # cash_rebuild_threshold: 1.0
    #   A percentage of (prior) maximum portfolio value.  If the
    #   portfolio value exceeds this amount, and the cash cushion is
    #   below the cash cushion target, then sell some additional stock
    #   at each withdrawal to rebuild the cash cushion.
    #
    #   If this value is > 1.0, should it be relative to the balance
    #   at the start of the last decline?
    # cash_rebuild_rate: 1.5
    #   When selling additional stock to rebuild cash, sell this times
    #   as much as would normally be needed for withdrawal (but never
    #   more than is needed to bring cash to the target level).
    #   Ah!  That implies we don't need to know the desired withdrawal
    #   rate relative to portfolio value.  Note: This rate minus 1.0
    #   is the amount of the additional stock sale.
    #
    # If the portfolio value is only slightly higher than the rebuild
    # threshold, should we rebuild cash at a rate less than the rebuild
    # rate?  For example, should we only sell stock in the amount of
    # current portfolio minus prior maximum, plus enough for the withdrawal?
    #
    # Should the cash cushion target (and the cash use threshold and cash
    # rebuild threshold) be relative to the portfolio balance (stock + cash),
    # or relative to the value of the stock?  If relative to stock, then
    # computing the cash amount at deposit time (and the dollar target when
    # rebuilding) is slightly more complicated.
    #

    def balance(self, stock_price):
        return round(self.cash + self.shares * stock_price, 2)
    
    def init(self, stock_price):
        self.annual_withdrawal = self.initial_balance * self.annual_withdrawal_rate
        if self.cash_cushion:
            self.cash = self.cash_cushion_target * self.annual_withdrawal
            self.shares = (self.initial_balance - self.cash) / stock_price
        else:
            self.cash = 0.0
            self.shares = self.initial_balance / stock_price
        self.max_balance = 0.0  # Highest balance seen previously  TODO: Part of balance history?
        if self.verbose:
            print(f"init: cash=${self.cash:,.2f}, shares={self.shares:,.2f}")
    
    def receive_dividend(self, dividend_per_share, stock_price):
        # Implicitly reinvests dividends
        # Note: caller is responsible for determining the amount of the
        # dividend per period (for each time this method is called).
        dividend_amount = self.shares * dividend_per_share
        self.shares += dividend_amount / stock_price
        if self.verbose:
            print(f"receive_dividend: dividend=${dividend_amount:,.2f}, shares={self.shares:,.2f}")
    
    # Compute interest earned on cash.  Uses 3-month treasury bill (TB3MS.csv) as a proxy.
    def receive_interest(self, interest_rate):
        interest = self.cash * interest_rate
        self.cash += interest
        if self.verbose:
            print(f"receive_interest: interest=${interest:,.2f}")

    
    def withdraw(self, amount, stock_price):
        balance = self.balance(stock_price)
        if balance < amount:
            raise ValueError(f'Insufficient funds.  Withdrawal={amount:,.2f}, balance={balance:,.2f}')
        if self.cash_cushion and balance < self.max_balance * self.cash_use_threshold:
            # Try to use the cash cushion to satisfy the withdrawal
            if self.cash >= amount:
                self.cash -= amount
                if self.verbose:
                    print(f"withdraw: (using cushion) cash ${amount:,.2f}")
            else:
                if self.verbose:
                    print(f"withdraw: (using cushion) cash ${self.cash:,.2f}, stock ${amount-self.cash:,.2f}")
                self.shares -= (amount - self.cash) / stock_price
                self.cash = 0.0
        elif (self.cash_cushion and
                balance - amount >= self.max_balance * self.cash_rebuild_threshold and
                self.cash < self.annual_withdrawal * self.cash_cushion_target):
            # Rebuild the cash cushion
            cash_add = min(self.annual_withdrawal * self.cash_cushion_target - self.cash,
                           amount * (self.cash_rebuild_rate - 1.0),
                           balance - self.max_balance)
            num_shares = (amount + cash_add) / stock_price
            self.shares -= num_shares
            assert(self.shares >= 0)
            self.cash += cash_add
            if self.verbose:
                print(f"withdraw: (rebuild cushion) selling {num_shares} shares; adding ${cash_add:,.2f} cash")
        else:
            # Sell stock to fund the withdrawal
            self.shares -= amount / stock_price
            balance -= amount
            if balance > self.max_balance:
                self.max_balance = balance
            if self.verbose:
                print(f"withdraw: selling ${amount:,.2f} stock; balance ${balance:,.2f}; max_balance ${self.max_balance:,.2f}")

    
    def __repr__(self):
        return f'{self.__class__.__name__}(shares={self.shares})'
    
    def adjust_withdrawal(self, period_withdrawal, tick, history):
        # Called before the withdrawal has been made, so the next one can
        # be adjusted.
        #
        # NOTE: Currently called annually, starting with the 1-year anniversary.
        #

        previous_cpi = history[-self.withdrawals_per_year].cpi
        balance = self.balance(tick.close)

        annual_maximum = max(h.balance for h in history[::-self.withdrawals_per_year])
        if self.verbose:
            print(f"annual_maximum={annual_maximum}  {[h.balance for h in history[-self.withdrawals_per_year::-self.withdrawals_per_year]]}")

        if self.paycut and balance <= self.max_balance * self.paycut_threshold:
            period_withdrawal = round(period_withdrawal * self.paycut_rate, 2)
            if self.verbose:
                print(f"adjust_withdrawal: pay cut; withdrawal={period_withdrawal}")
        elif self.raise_enable and balance >= annual_maximum * self.raise_threshold:
            period_withdrawal = round(period_withdrawal * self.raise_rate, 2)
            if self.verbose:
                print(f"adjust_withdrawal: raise; withdrawal={period_withdrawal}")
        elif self.ratchet and self.annual_withdrawal < balance * self.ratchet_to_rate:
            period_withdrawal = round(balance * self.ratchet_to_rate / self.withdrawals_per_year, 2)
            if self.verbose:
                print(f"adjust_withdrawal: ratchet up; withdrawal={period_withdrawal}")
        else:
            period_withdrawal = round(period_withdrawal * tick.CPI / previous_cpi, 2)
            if self.verbose:
                print(f"adjust_withdrawal: (inflation); withdrawal={period_withdrawal}")
        
        return round(period_withdrawal, 2)

    def simulate_withdrawals(self,
                             market_data_seq):          # Assumes monthly Shiller data, length of one retirement
        market_data = tuple(market_data_seq)[::12//self.withdrawals_per_year]
        self.init(market_data[0].close)
        period_withdrawal = round(self.annual_withdrawal / self.withdrawals_per_year, 2)
        history = []
        for tick in market_data:
            # Adjust withdrawal amount annually.  TODO: Could this be every period?
            # TODO: Allow adjustment algorithm to be specified externally
            balance = self.balance(tick.close)
            if self.verbose:
                print(f"{tick.date}: balance=${balance:,.2f} cash=${self.cash:,.2f} shares={self.shares} price=${tick.close:,.2f}")
            if len(history) % self.withdrawals_per_year == 0 and len(history) > 0:
                period_withdrawal = self.adjust_withdrawal(period_withdrawal, tick, history)
                self.annual_withdrawal = period_withdrawal * self.withdrawals_per_year
                # TODO: Should period_withdrawal be a member variable?
            
            # Make the period's withdrawal
            if balance < period_withdrawal:
                if self.verbose:
                    print(f"simulate_withdrawals: FAILED balance={balance:,.2f}, withdrawal={period_withdrawal:,.2f}")
                return (False, history)
            self.withdraw(period_withdrawal, tick.close)

            # Receive dividends
            self.receive_dividend(tick.dividend/self.withdrawals_per_year, tick.close)

            # Receive interest on cash
            if self.cash:
                self.receive_interest(tick.interest/self.withdrawals_per_year)
            
            # Update the history
            balance = self.balance(tick.close)
            assert balance >= 0

            history.append(PortfolioHistoryItem(tick.date, period_withdrawal, balance, tick.close, tick.CPI))

        return (True, history)

    def sim_periods(self,
                    market_data,                    # Assumes monthly Shiller data
                    period_length = 360):           # in months/samples
        # Get rid of any trailing market data that is incomplete
        market_data = list(market_data)
        while market_data[-1].dividend is None or market_data[-1].CPI is None:
            del market_data[-1]
        
        # NOTE: "sustainability" is redundant.  Look at real balance growth rate >= 0.
        survived = []           # True/False whether each period was able to make all withdrawals
        sustained = []          # True/False whether each period's ending real balance was at least as large as the initial balance
        balance_growth = []     # Compound Annual Growth Rate for each period's real portfolio balance
        withdrawal_growth = []  # Compound Annual Growth Rate for each period's real withdrawal
        periods = []
        for period in subranges(market_data, period_length):
            success, history = self.simulate_withdrawals(period)
            real_balances = [i.balance * i.cpi / history[0].cpi for i in history]
            real_min = min(real_balances)
            real_max = max(real_balances)
            real_last = real_balances[-1]
            balance_growth_rate = ((real_last / self.initial_balance) ** (12/period_length)) - 1.0
            withdrawal_growth_rate = ((history[-1].withdrawal / history[0].withdrawal * history[0].cpi / history[-1].cpi) ** (12/period_length)) - 1.0
            sustain = real_last >= self.initial_balance

            periods.append(Period(period[0].date, success, sustain, real_min, real_max, real_last, balance_growth_rate, history))

            survived.append(success)
            sustained.append(sustain)
            if success:
                balance_growth.append(balance_growth_rate)
                withdrawal_growth.append(withdrawal_growth_rate)

        # Some statistics I'd like:
        #   * Survivability rate (what percentage of periods lasted long enough?)
        #   * Sustainability rate (what percentage of periods ended with at least the original amount, inflation adjusted?)
        #   * Mean/median ending withdrawal amount (real dollars).  Should it be a compound annual growth rate?
        #     If a growth rate, use harmonic mean instead of ordinary mean.
        #   Should the mean/stdev/median statistics apply only to periods that succeeded?
        survival_rate = sum(survived) / len(survived)
        sustain_rate = sum(sustained) / len(sustained)
        balance_mean = statistics.mean(balance_growth)
        balance_stdev = statistics.stdev(balance_growth, xbar=balance_mean)
        balance_median = statistics.median(balance_growth)
        withdraw_mean = statistics.mean(withdrawal_growth)
        withdraw_stdev = statistics.stdev(withdrawal_growth, xbar=withdraw_mean)
        withdraw_median = statistics.median(withdrawal_growth)

        return PeriodsResult(survival_rate, sustain_rate,
            balance_median, balance_mean, balance_stdev,
            withdraw_median, withdraw_mean, withdraw_stdev,
            periods)
            
def print_history(history):
    for item in history:
        print(f"{item.date}: withdrawal={item.withdrawal}  balance={item.balance}  stock_price={item.stock_price}  cpi={item.cpi}")
    print()
    
def main():
    for decline in declines(read_yahoo()):
        if decline.percent >= 0.05:
            print(decline.summarize())

if __name__ == '__main__':
    main()
