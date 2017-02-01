#
# Stock Market Simulation
#

import os, collections

class Options(object):
	pass
opts = Options()
opts.verbose = False

class InsufficientFunds(Exception):
	pass

MarketDataValue = collections.namedtuple('MarketDataValue', ['price', 'dividend', 'earnings'])

class MarketData(dict):
	def __init__(self, path="StockMarketData.csv"):
		minYear = None
		maxYear = None
		filename = os.path.expanduser(path)
		with open(filename, 'rU') as f:
			l = f.readline()
			assert l == "Date,Real Price,Real Dividend,Real Earnings\n"
			for l in f:
				fields = l.rstrip("\n").split(',')
				assert len(fields) == 4
				year,month = map(int, fields[0].split('.'))
			
				if minYear is None:
					minYear = year
				elif year < minYear:
					minYear = year
			
				if maxYear is None:
					maxYear = year
				elif year > maxYear:
					maxYear = year
			
				price,dividend = map(float, fields[1:3])
				if fields[3] == "":
					earnings = None
				else:
					earnings = float(fields[3])
				self[(year,month)] = MarketDataValue(price, dividend, earnings)
				if month == 12:
					self[year] = MarketDataValue(price, dividend, earnings)
		self.minYear = minYear
		self.maxYear = maxYear
marketData = MarketData()

class Simulation(object):
	initialBalance = 1000000.00
	
	def __init__(self, years=40, rate=0.04):
		self.years = years
		self.withdrawalRate = rate
		self.withdrawal = self.initialBalance * rate
		self.logStr = ""
		
	def __repr__(self):
		return self.logStr + self.__class__.__name__ + "(" + \
			"startYear={}, year={}, ".format(self.startYear, self.year) + \
			"balance={:,.2f}, cash={:,.2f}, stock={:,.2f}, ".format(self.balance, self.cash, self.stock) + \
			"shares={:,.2f}, price={:,.2f})".format(self.shares, self.price)
	
	def Log(self, s):
		self.logStr = self.logStr + s
	
	def SimPeriod(self, startYear):
		self.logStr = ""
		self.startYear = startYear
		self.year = self.startYear - 1		# To easily grab initial stock price
		self.balance = self.initialBalance
		self.cash = 0
		self.price = marketData[self.year].price
		self.stock = self.initialBalance
		self.shares = self.stock / self.price
		if opts.verbose: print "{0}({1}):".format(self.__class__.__name__, startYear)
		self.SimInit()		# Give the algorithm a chance to initialize itself
		for year in xrange(startYear, startYear+self.years):
			assert self.cash >= 0.0
			assert self.shares >= 0.0
			self.year = year
			dividend = marketData[year].dividend * self.shares
			# print "{0}: dividend={1}".format(year, dividend)
			self.cash += dividend
			self.price = marketData[(year, 12)].price
			self.stock = self.shares * self.price
			self.balance = self.cash + self.stock
			self.SimYear()	# Move forward a year in the simulation
	
	def SimInit(self):
		pass
	
	def SimYear(self):
		pass
	
	def run(self):
		failures = 0
		failDuration = 0
		for startYear in xrange(marketData.minYear+1, marketData.maxYear-self.years+2):
			try:
				self.SimPeriod(startYear)
			except InsufficientFunds as ex:
				print ex
				failures += 1
				failDuration += self.year - startYear
		if failures != 0:
			print "{0}: {1} failed periods (avg. {2} years)".format(self.__class__.__name__, failures, failDuration/failures)

class AllStock(Simulation):
	"""Portfolio is 100% stocks"""
	def SimYear(self):
		if self.cash >= self.withdrawal:
			# Withdrawal is all cash; don't sell any stock
			self.cash -= self.withdrawal
			self.balance -= self.withdrawal
		else:
			# Withdraw all cash; sell enough stock to make up the difference
			sellShares = (self.withdrawal - self.cash) / self.price
			if sellShares > self.shares:
				raise InsufficientFunds(self)
			self.shares -= sellShares
			self.cash = 0.0
			self.balance = self.stock = self.shares * self.price
		self.Log("    year={}, balance={:,.2f}\n".format(self.year, self.balance))

class NinetyTen(Simulation):
	"""Portfolio is 90% stock, 10% cash, rebalanced each year"""
	def Rebalance(self):
		self.cash = self.balance * 0.10
		self.stock = self.balance * 0.90
		self.shares = self.stock / self.price
		self.Log("    year={}, cash={:,.2f}, stock={:,.2f}, balance={:,.2f}\n".format(self.year, self.cash, self.stock, self.balance))
	def SimInit(self):
		self.Rebalance()
	def SimYear(self):
		if self.balance < self.withdrawal:
			raise InsufficientFunds(self)
		self.balance -= self.withdrawal
		self.Rebalance()

class EightyTwenty(NinetyTen):
	"""Portfolio is 80% stock, 20% cash, rebalanced each year"""
	def Rebalance(self):
		self.cash = self.balance * 0.20
		self.stock = self.balance * 0.80
		self.shares = self.stock / self.price
		self.Log("    year={}, cash={:,.2f}, stock={:,.2f}, balance={:,.2f}\n".format(self.year, self.cash, self.stock, self.balance))

class FiftyFifty(NinetyTen):
	"""Portfolio is 50% stock, 50% cash, rebalanced each year"""
	def Rebalance(self):
		self.cash = self.balance * 0.50
		self.stock = self.balance * 0.50
		self.shares = self.stock / self.price
		self.Log("    year={}, cash={:,.2f}, stock={:,.2f}, balance={:,.2f}\n".format(self.year, self.cash, self.stock, self.balance))

class CashCushion(Simulation):
	"""3 year cash cushion, used when portfolio is less than initial balance"""
	def Log(self, s):
		self.logStr = self.logStr + s
		if self.startYear == 1969:
			print s.rstrip('\n')

	def SimInit(self):
		self.cash = self.balance * self.withdrawalRate * 5
		self.cashGoal = self.cash
		self.stock = self.balance - self.cash
		self.shares = self.stock / self.price
		self.Log("    year={}, cash={:,.2f}, price={:,.2f}, stock={:,.2f}, balance={:,.2f}\n".format(self.year, self.cash, self.price, self.stock, self.balance))
	def SimYear(self):
		self.Log("    Begin year={}, cash={:,.2f}, price={:,.2f}, stock={:,.2f}, balance={:,.2f}\n".format(self.year, self.cash, self.price, self.stock, self.balance))
		if self.balance < self.initialBalance:
			# Try to use the cash cushion
			if self.cash >= self.withdrawal:
				self.cash -= self.withdrawal
				self.Log("    Using cash cushion.\n")
			else:
				sellShares = (self.withdrawal - self.cash) / self.price
				if sellShares > self.shares:
					raise InsufficientFunds(self)
				self.shares -= sellShares
				self.cash = 0.0
				self.Log("    Using cash cushion.  Selling {:,.2f} shares.\n".format(sellShares))
		else:
			# Sell stock.  Possibly replenish cash cushion.
			msg = "    "
			withdrawal = self.withdrawal
			useCash = 0.0
			if self.cash > self.cashGoal:
				useCash = min(self.withdrawal, self.cash - self.cashGoal)
				withdrawal -= useCash
				self.cash -= useCash
				msg = msg + "Using {:,.2f} excess cash.  ".format(useCash)
			sellShares = withdrawal / self.price
			if self.cash < self.cashGoal and self.balance > self.initialBalance * (1 + self.withdrawalRate):
				sellShares = 2 * sellShares		# Replenish cash
				msg = msg + "Replenishing cash.  "
			if sellShares > self.shares:
				raise InsufficientFunds(self)
			self.shares -= sellShares
			self.Log(msg + "Selling {:,.2f} shares.\n".format(sellShares))
		self.balance -= self.withdrawal
		self.stock = self.shares * self.price
		self.Log("    End year={}, cash={:,.2f}, price={:,.2f}, stock={:,.2f}, balance={:,.2f}\n".format(self.year, self.cash, self.price, self.stock, self.balance))

def main():
	#AllStock().run()
	#NinetyTen().run()
	#EightyTwenty().run()
	#FiftyFifty().run()
	CashCushion().run()

if __name__ == "__main__":
	import sys
	if "-v" in sys.argv:
		opts.verbose = True
	main()
