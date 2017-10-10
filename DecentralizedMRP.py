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
        servicelevel = []
        def dist(a) :
            sigma = 1
            mu = 100
            return ( ( 1 / ( sigma * np.sqrt(2*np.pi) )) * np.exp(-0.5 * (np.power( ( (a-mu)/sigma) , 2) ) ) )
        def f(x):
            return quad(lambda a: 1 * dist(a), 0, x)[0] \
                   + quad(lambda a: 1000 * dist(a), x, np.inf)[0]

            #return quad( lambda a: self.Intance.InventoryCosts[0] *  self.GetDistribution( 0, 0, a), 0, x)[0] \
            #        +  quad(lambda a: self.Intance.BackorderCosts[0] * self.GetDistribution(0, 0, a), x, 10000000)[0]

                         # self.Intance.InventoryCosts[0] * ( self.GetDistribution( 0, 0, x) ) \
                   #+ self.Intance.BackorderCosts[0] * ( 1 -self.GetDistribution( 0, 0, x) )


        result = optimize.minimize_scalar(f,  bounds=(0, 1000), method='bounded')
           # optimize.minimize_scalar(F)
        print "optimized %s, value %r" %(result.success, result)
        return servicelevel



