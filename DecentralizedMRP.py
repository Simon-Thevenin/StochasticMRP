from scipy import optimize
from scipy.stats import norm
from Constants import Constants
from scipy.integrate import quad
import numpy as np
#This object contains logic and methods to compute the classical MRP in decentralized fashion
class DecentralizedMRP(object):


    # constructor

    def __init__(self, mrpinstance):
        self.Intance =mrpinstance

    def GetDistribution(self, time, product, x):
        if self.Intance.Distribution == Constants.NonStationary:
            return norm.cdf(x, 1,1)#self.Intance.ForecastedAverageDemand[time][product], self.Intance.ForcastedStandardDeviation[time][product])

    def ComputeServiceLevel(self):
        safetystock = [ [ 0.0 for p in self.Intance.ProductSet] for t in self.Intance.TimeBucketSet ]

        for p in self.Intance.ProductSet:
            for t in self.Intance.TimeBucketSet:
                #def normpdf(x, mu, sigma):
                #    u = (x - mu) / abs(sigma)
                #    y = (1 / (np.sqrt(2 * np.pi) * abs(sigma))) * np.exp(-u * u / 2)
                #    return y

                def dist(a) :
                     return   norm.cdf(a + 1, self.Intance.ForecastedAverageDemand[t][p], self.Intance.ForcastedStandardDeviation[t][p] )


                x = self.Intance.ForecastedAverageDemand[t][p]
                while  self.Intance.InventoryCosts[p] * ( dist( x ) ) - self.Intance.BackorderCosts[p] * ( 1 - dist( x ) ) < 0:
                    x+= 0.01
                print "optimized %s, value %r, proba %r " %  (x,self.Intance.InventoryCosts[p] * ( dist( x ) ) - self.Intance.BackorderCosts[p] * ( 1 - dist( x ) ), dist(x))

                safetystock[t][p] = x - self.Intance.ForecastedAverageDemand[t][p]

            #quad(lambda a: (x*x - a*x) * dist(a) , 100.0, x)[0] \
                    #quad(lambda a: (a*x - x*x) * dist(a), x, 100000000)[0] #np.inf

            #return quad( lambda a: self.Intance.InventoryCosts[0] *  self.GetDistribution( 0, 0, a), 0, x)[0] \
            #        +  quad(lambda a: self.Intance.BackorderCosts[0] * self.GetDistribution(0, 0, a), x, 10000000)[0]

                         # self.Intance.InventoryCosts[0] * ( self.GetDistribution( 0, 0, x) ) \
                   #+ self.Intance.BackorderCosts[0] * ( 1 -self.GetDistribution( 0, 0, x) )

     # optimize.minimize_scalar(F)


        return safetystock



