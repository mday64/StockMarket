#
# Stock Market Simulation
#

import os

class Options(object):
	pass
opts = Options()
opts.verbose = False

class InsufficientFunds(Exception):
	pass

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
				self[(year,month)] = (price, dividend, earnings)
		self.minYear = minYear
		self.maxYear = maxYear
marketData = MarketData()

class Simulation(object):
	initialBalance = 1000000.00
	
	def __init__(self, years=30, rate=0.04):
		self.years = years
		self.withdrawal = self.initialBalance * rate
	
	def __repr__(self):
		return "{0}{1}".format(self.__class__.__name__, self.__dict__)
	
	def SimPeriod(self, startYear):
		self.startYear = startYear
		self.balance = self.initialBalance
		self.cash = 0
		self.stock = self.initialBalance
		self.shares = self.stock / marketData[(startYear-1,12)][0]
		if opts.verbose: print "{0}({1}):".format(self.__class__.__name__, startYear)
		self.year = self.startYear - 1
		self.SimInit()		# Give the algorithm a chance to initialize itself
		for year in xrange(startYear, startYear+self.years):
			assert self.cash >= 0.0
			assert self.shares >= 0.0
			self.year = year
			self.SimYear()	# Move forward a year in the simulation
	
	def SimInit(self):
		pass
	
	def SimYear(self):
		pass
	
	def run(self):
		failures = 0
		for startYear in xrange(marketData.minYear+1, marketData.maxYear-self.years+2):
			try:
				self.SimPeriod(startYear)
			except InsufficientFunds as ex:
				if opts.verbose: print ex
				failures += 1
		if failures != 0:
			print "{0}: {1} failed periods".format(self.__class__.__name__, failures)

class AllStock(Simulation):
	"""Portfolio is 100% stocks"""
	def SimYear(self):
		price = marketData[(self.year,12)][0]
		sellShares = self.withdrawal / price
		if sellShares > self.shares:
			raise InsufficientFunds(self)
		self.shares -= sellShares
		self.stock = self.balance = self.shares * price
		if opts.verbose: print "    year={}, balance={:,.2f}".format(self.year, self.balance)

class NinetyTen(Simulation):
	"""Portfolio is 90% stock, 10% cash, rebalanced each year"""
	def Rebalance(self):
		self.cash = self.balance * 0.10
		self.stock = self.balance * 0.90
		self.shares = self.stock / marketData[(self.year,12)][0]
		if opts.verbose: print "    year={}, cash={:,.2f}, stock={:,.2f}, balance={:,.2f}".format(self.year, self.cash, self.stock, self.balance)
	def SimInit(self):
		self.Rebalance()
	def SimYear(self):
		price = marketData[(self.year,12)][0]
		self.stock = self.shares * price
		self.balance = self.cash + self.stock
		if self.balance < self.withdrawal:
			raise InsufficientFunds(self)
		self.balance -= self.withdrawal
		self.Rebalance()

class EightyTwenty(NinetyTen):
	"""Portfolio is 80% stock, 20% cash, rebalanced each year"""
	def Rebalance(self):
		self.cash = self.balance * 0.20
		self.stock = self.balance * 0.80
		self.shares = self.stock / marketData[(self.year,12)][0]
		if opts.verbose: print "    year={}, cash={:,.2f}, stock={:,.2f}, balance={:,.2f}".format(self.year, self.cash, self.stock, self.balance)

class FiftyFifty(NinetyTen):
	"""Portfolio is 50% stock, 50% cash, rebalanced each year"""
	def Rebalance(self):
		self.cash = self.balance * 0.50
		self.stock = self.balance * 0.50
		self.shares = self.stock / marketData[(self.year,12)][0]
		if opts.verbose: print "    year={}, cash={:,.2f}, stock={:,.2f}, balance={:,.2f}".format(self.year, self.cash, self.stock, self.balance)

def main():
	AllStock().run()
	NinetyTen().run()
	EightyTwenty().run()
	# FiftyFifty().run()

if __name__ == "__main__":
	import sys
	if "-v" in sys.argv:
		opts.verbose = True
	main()
