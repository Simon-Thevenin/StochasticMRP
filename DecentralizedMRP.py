from scipy import optimize
from scipy.stats import norm
from Constants import Constants
from scipy.integrate import quad
import numpy as np
#This object contains logic and methods to compute the classical MRP in decentralized fashion
class DecentralizedMRP(object):


    # constructor

    def __init__(self, mrpinstance):
        self.Instance =mrpinstance

    def GetDistribution(self, time, product, x):
        if self.Instance.Distribution == Constants.NonStationary:
            return norm.cdf(x, 1,1)#self.Intance.ForecastedAverageDemand[time][product], self.Intance.ForcastedStandardDeviation[time][product])

    def ComputeSafetyStock(self):
        if self.Instance.Distribution <> Constants.NonStationary:
            raise "Not Impemented for other than normal!!!!"


        safetystock = [ [ 0.0 for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet ]
        for p in self.Instance.ProductSet:
            for t in self.Instance.TimeBucketSet:

                ratio = self.Instance.BackorderCosts[p] / (self.Instance.BackorderCosts[p] + self.Instance.InventoryCosts[p] )
                value = norm.ppf( ratio, self.Instance.ForecastedAverageDemand[t][p], self.Instance.ForcastedStandardDeviation[t][p] )
                #def normpdf(x, mu, sigma):
                #    u = (x - mu) / abs(sigma)
                #    y = (1 / (np.sqrt(2 * np.pi) * abs(sigma))) * np.exp(-u * u / 2)
                #    return y
                step =0.01
                def dist(a) :
                     return   norm.cdf(a + step, self.Instance.ForecastedAverageDemand[t][p], self.Instance.ForcastedStandardDeviation[t][p] )

                def incrementalcost(x, p, t):
                    if  t < self.Instance.NrTimeBucket - 1:
                        result = self.Instance.InventoryCosts[p] * step * ( dist( x ) ) - self.Instance.BackorderCosts[p] * step * ( 1 - dist( x ) )
                    else :
                        result = self.Instance.InventoryCosts[p] *step *  (dist(x)) - (self.Instance.LostSaleCost[p] )*step *  ( 1 - dist(x))
                    return result

                x = self.Instance.ForecastedAverageDemand[t][p]

                while  incrementalcost(x,p,t) < 0:
                    x+= step
                print "optimized %s, value %r, proba %r, forecast %r std %r value %r" %  (x,incrementalcost(x,p,t), dist(x), self.Instance.ForecastedAverageDemand[t][p], self.Instance.ForcastedStandardDeviation[t][p], value)

                safetystock[t][p] = x - self.Instance.ForecastedAverageDemand[t][p]

        return safetystock


    #def ComputeSafetyStock(self):

    #    ss = 0

    #    if self.Instance.Distribution <> Constants.NonStationary:
    #        raise "Not Impemented for other than normal!!!!"

        #compute the distribution of the average demand
        #meandeamnd = [mean( self.Instance.ForecastedAverageDemand[t][p] for t in self.Instance.TimeBucketSet) for p in self.Instance.ProductSet ]
        #meanstd  = [sum( np.power(self.Instance.ForecastedAverageDemand[t][p], 2) / np.power(self.Instance.NrTimeBucket, 2) for t in self.Instance.TimeBucketSet) for p in
        #              self.Instance.ProductSet]

                 #def normpdf(x, mu, sigma):
                #    u = (x - mu) / abs(sigma)
                #    y = (1 / (np.sqrt(2 * np.pi) * abs(sigma))) * np.exp(-u * u / 2)
                #    return y
        #         step =0.01
        #         def dist(a) :
        #              return   norm.cdf(a + step, self.Instance.ForecastedAverageDemand[t][p], self.Instance.ForcastedStandardDeviation[t][p] )
        #
        #         def incrementalcost(x, p, t):
        #             if  t < self.Instance.NrTimeBucket - 1:
        #                 result = self.Instance.InventoryCosts[p] * step * ( dist( x ) ) - self.Instance.BackorderCosts[p] * step * ( 1 - dist( x ) )
        #             else :
        #                 result = self.Instance.InventoryCosts[p] *step *  (dist(x)) - (self.Instance.LostSaleCost[p] )*step *  ( 1 - dist(x))
        #             return result
        #
        #         x = self.Instance.ForecastedAverageDemand[t][p]
        #
        #         while  incrementalcost(x,p,t) < 0:
        #             x+= step
        #         print "optimized %s, value %r, proba %r, forecast %r std %r" %  (x,incrementalcost(x,p,t), dist(x), self.Instance.ForecastedAverageDemand[t][p], self.Instance.ForcastedStandardDeviation[t][p])
        #
        #         ss[t][p] = x - self.Instance.ForecastedAverageDemand[t][p]
        # safetystock = [[ss for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet]

        #return safetystock
