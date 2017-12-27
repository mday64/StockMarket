#!python3
#
# Stock Market Simulation
#

import sys
import os
import collections

class Options():
	pass
opts = Options()
opts.quiet = False
opts.verbose = False
opts.years = 30
opts.rate = 0.04

class InsufficientFunds(Exception):
	pass

MarketDataValue = collections.namedtuple('MarketDataValue', 'price,dividend,earnings,cpi,gs10,real_price,real_dividend,real_earnings'.split(','))

class MarketData(dict):
	def __init__(self, path="ie_data.csv"):
		super().__init__()
		minYear = None
		maxYear = None
		filename = os.path.expanduser(path)
		with open(filename, 'rU') as f:
			l = f.readline()
			assert l == "Year,Month,Price,Dividend,Earnings,CPI,GS10,Real Price,Real Dividend,Real Earnings\n"
			for l in f:
				fields = l.rstrip("\n").split(',')
				assert len(fields) == 10
				year,month = map(int, fields[0:2])
			
				if minYear is None:
					minYear = year
				elif year < minYear:
					minYear = year
			
				if maxYear is None:
					maxYear = year
				elif year > maxYear:
					maxYear = year
			
				vals = [None if x == "" else float(x) for x in fields[2:]]
				self[(year,month)] = MarketDataValue(*vals)
				if month == 12:
					self[year] = MarketDataValue(*vals)
		self.minYear = minYear
		self.maxYear = maxYear
marketData = MarketData()

class Simulation():
	initialBalance = 1000000.00
	
	def __init__(self):
		self.years = opts.years
		self.withdrawalRate = opts.rate
		self.logStr = ""
		
	def __repr__(self):
		s = self.__class__.__name__ + "(" + \
			"startYear={}, year={}, withdrawal={:,.2f}, ".format(self.startYear, self.year, self.withdrawal) + \
			"balance={:,.2f}, cash={:,.2f}, stock={:,.2f}, ".format(self.balance, self.cash, self.stock) + \
			"shares={:,.2f}, price={:,.2f})\n".format(self.shares, self.price)
		if opts.quiet is not True:
			s += self.logStr
		return s
	
	def Log(self, s):
		self.logStr = self.logStr + s
	
	def SimPeriod(self, startYear):
		self.logStr = ""
		self.startYear = self.year = startYear
		self.balance = self.initialBalance
		self.initialWithdrawal = self.withdrawal = self.initialBalance * self.withdrawalRate
		self.cash = 0
		self.price = marketData[self.year].price
		self.stock = self.initialBalance
		self.shares = self.stock / self.price
		if opts.verbose: print("{0}({1}):".format(self.__class__.__name__, startYear))
		self.SimInit()		# Give the algorithm a chance to initialize itself
		self.Log("    {}: withdrawal={:,.2f} cash={:,.2f} stock={:,.2f} shares={:,.2f} balance={:,.2f}; ".format(self.year, self.withdrawal, self.cash, self.stock, self.shares, self.balance))
		self.SimYear()		# Do the initial withdrawal
		for year in range(startYear, startYear+self.years):
			# Do subsequent years
			self.year = year

			# Adjust withdrawal for inflation
			self.withdrawal = self.withdrawal * marketData[year].cpi / marketData[year-1].cpi

			# Take a guess at interest earned on cash
			self.cash = self.cash * (1 + marketData[year].gs10 / 300.0)
			
			# Take dividend as cash
			dividend = marketData[year].dividend * self.shares
			self.cash += dividend
			
			# Update stock price, stock value, and total value
			self.price = marketData[year].price
			self.stock = self.shares * self.price
			self.balance = self.cash + self.stock
			self.Log("    {}: withdrawal={:,.2f} dividends={:,.2f} cash={:,.2f} stock={:,.2f} shares={:,.2f} balance={:,.2f}; ".format(year, self.withdrawal, dividend, self.cash, self.stock, self.shares, self.balance))
			
			# Let the specific algorithm decide how to satisfy the withdrawal
			self.SimYear()
		if opts.verbose: print(self.logStr)

	def SimInit(self):
		pass
	
	def SimYear(self):
		pass
	
	def run(self):
		failures = 0
		failDuration = 0
		for startYear in range(marketData.minYear+1, marketData.maxYear-self.years+2):
			try:
				self.SimPeriod(startYear)
			except InsufficientFunds as ex:
				print("\nFAILED! {}".format(ex))
				failures += 1
				failDuration += self.year - startYear
		if failures != 0:
			print("{0}: {1} failed periods (avg. {2} years)".format(self.__class__.__name__, failures, failDuration/failures))

class AllStock(Simulation):
	"""Portfolio is 100% stocks"""
	def SimYear(self):
		if self.cash >= self.withdrawal:
			# Withdrawal is all cash; don't sell any stock
			self.Log("using cash\n")
			self.cash -= self.withdrawal
			self.balance -= self.withdrawal
			# Reinvest excess cash?  (If so, rebalance with 100% stock, 0% cash)
		else:
			# Withdraw all cash; sell enough stock to make up the difference
			sellShares = (self.withdrawal - self.cash) / self.price
			if sellShares > self.shares:
				raise InsufficientFunds(self)
			self.Log("using cash; selling stock ({:,.2f}; {:,.2f} shares)\n".format(self.withdrawal-self.cash, sellShares))
			self.shares -= sellShares
			self.cash = 0.0
			self.balance = self.stock = self.shares * self.price

class NinetyTen(Simulation):
	"""Portfolio is 90% stock, 10% cash, rebalanced each year"""
	def Rebalance(self):
		self.cash = self.balance * 0.10
		self.stock = self.balance * 0.90
		self.shares = self.stock / self.price
	def SimInit(self):
		self.Rebalance()
	def SimYear(self):
		if self.balance < self.withdrawal:
			raise InsufficientFunds(self)
		self.balance -= self.withdrawal
		oldShares = self.shares
		self.Rebalance()
		newShares = self.shares
		if newShares < oldShares:
			self.Log("selling stock ({:,.2f}; {:,.2f} shares)\n".format((oldShares-newShares) * self.price, oldShares-newShares))
		else:
			self.Log("buying stock ({:,.2f}; {:,.2f} shares)\n".format((newShares-oldShares) * self.price, newShares-oldShares))

class EightyTwenty(NinetyTen):
	"""Portfolio is 80% stock, 20% cash, rebalanced each year"""
	def Rebalance(self):
		self.cash = self.balance * 0.20
		self.stock = self.balance * 0.80
		self.shares = self.stock / self.price

class FiftyFifty(NinetyTen):
	"""Portfolio is 50% stock, 50% cash, rebalanced each year"""
	def Rebalance(self):
		self.cash = self.balance * 0.50
		self.stock = self.balance * 0.50
		self.shares = self.stock / self.price

class CashCushion(Simulation):
	"""3 year cash cushion, used when portfolio is less than initial balance"""
	cushionYears = 3
	def SimInit(self):
		self.cash = self.cashGoal = self.withdrawal * self.cushionYears
		self.stock = self.balance - self.cash
		self.shares = self.stock / self.price
	def SimYear(self):
		self.cashGoal = self.withdrawal * self.cushionYears
		if self.balance < (self.withdrawal / self.withdrawalRate):
			# Try to use the cash cushion
			if self.cash >= self.withdrawal:
				self.cash -= self.withdrawal
				self.Log("using cash\n")
			else:
				sellShares = (self.withdrawal - self.cash) / self.price
				if sellShares > self.shares:
					raise InsufficientFunds(self)
				self.shares -= sellShares
				self.cash = 0.0
				self.Log("using cash; selling stock ({:,.2f}; {:,.2f} shares)\n".format(sellShares * self.price, sellShares))
		else:
			# Sell stock.  Possibly replenish cash cushion.
			msg = ""
			withdrawal = self.withdrawal
			useCash = 0.0
			if self.cash > self.cashGoal:
				useCash = min(self.withdrawal, self.cash - self.cashGoal)
				withdrawal -= useCash
				self.cash -= useCash
				msg = msg + "using {:,.2f} excess cash; ".format(useCash)
			sellShares = withdrawal / self.price
			if self.cash < self.cashGoal and self.balance > (self.withdrawal + self.withdrawal / self.withdrawalRate):
				sellShares = 2 * sellShares		# Replenish cash
				msg = msg + "replenishing cash; "
			if sellShares > self.shares:
				raise InsufficientFunds(self)
			self.shares -= sellShares
			self.Log(msg + "selling stock ({:,.2f}; {:,.2f} shares)\n".format(sellShares * self.price, sellShares))
		self.balance -= self.withdrawal
		self.stock = self.shares * self.price

def main():
	AllStock().run()
	#NinetyTen().run()
	#EightyTwenty().run()
	#FiftyFifty().run()
	CashCushion().run()

if __name__ == "__main__":	
	for arg in sys.argv:
		if arg == '-v':
			opts.verbose = True
		elif arg == '-q':
			opts.quiet = True
		elif arg[0:3] == '-y=':
			opts.years = int(arg[3:])
		elif arg[0:3] == '-r=':
			opts.rate = float(arg[3:])
	main()
