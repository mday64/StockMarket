#
# Stock Market Simulation
#

import sys, os

class MarketData(dict):
	def __init__(self, path="~/StockMarketData.csv"):
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

class Simulation:
	def __init__(self, marketData, years=30):
		self.marketData = marketData
		self.years = years
		
	def run(self):
		for startYear in xrange(self.marketData.minYear, self.marketData.maxYear-self.years+2):
			print startYear

def main():
	marketData = MarketData()
	Simulation(marketData).run()
	
if __name__ == "__main__":
	main()
