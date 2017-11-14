from Constants import Constants
from ScenarioTreeNode import ScenarioTreeNode
from MRPSolution import MRPSolution


#This object contains logic and methods to compute the classical MRP in decentralized fashion
class DecentralizedMRP(object):


    # constructor

    def __init__(self, mrpinstance):
        self.Instance =mrpinstance


    def ComputeSafetyStock(self):

        safetystock = [ [ 0.0 for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet ]
        for p in self.Instance.ProductSet:
            for t in self.Instance.TimeBucketSet:

                ratio = float(self.Instance.BackorderCosts[p] ) / float((self.Instance.BackorderCosts[p] + self.Instance.InventoryCosts[p] ) )

                #value = norm.ppf( ratio, self.Instance.ForecastedAverageDemand[t][p], self.Instance.ForcastedStandardDeviation[t][p] )
                x = ScenarioTreeNode.TransformInverse([[ratio]],
                                                  1,
                                                  1,
                                                  self.Instance.Distribution,
                                                  [self.Instance.ForecastedAverageDemand[t][p]],
                                                  [self.Instance.ForcastedStandardDeviation[t][p]])[0][0]

                if Constants.Debug:
                    print "optimized %s forecast %r std %r  "%  (x, self.Instance.ForecastedAverageDemand[t][p], self.Instance.ForcastedStandardDeviation[t][p])

                safetystock[t][p] = x - self.Instance.ForecastedAverageDemand[t][p]

        return safetystock

    #This method solve the instance given in argument wth the rule given in argument
    #The problem is decomposed by product, starting from end item to highest level component.
    #After each planning decision, the capacity is checked, and repair is applied if required.
    def SolveWithSimpleRule( self, instance, rule ):
        # Create an empty solution
        result =  MRPSolution( instance= instance )

        # sort the prduct by level
        self.LevelSet = sorted(set(self.Level), reverse=False)

        # For each product, at each time periode, apply the decision rule to find the quantity to produce / order
        for l in self.LevelSet:
            prodinlevel = [p for p in self.Instance.ProductSet if self.Level[p] == l]
            for p in prodinlevel:
                for t in instance.TimeBucketSet:
                    self.GetIdealQuantityToOrder(instance, p, t, rule)

                    # After each decision, check capacity, and repair if necessary
                    self.RepairCapacity(p, t)

    # This method apply lot for lot to solve the instance
    def GetIdealQuantityToOrder(self, instance,  p, t, rule):
        if rule == Constants.L4L:
            self.LotForLot(instance,  p, t)
        if rule == Constants.EOQ:
            self.EOQ( instance,  p, t)
        if rule == Constants.POQ:
            self.POQ(instance,  p, t)
        if rule == Constants.SilverMeal:
            self.SilverMeal(instance,  p, t)

    #return the quantity to order at time t for product p in instance with Lot for Lot rule
    def LotForLot( self, instance,  p, t ):
        return 0

    # return the quantity to order at time t for product p in instance with EOQ
    def EOQ(self, instance, p, t):
        return 0

    # return the quantity to order at time t for product p in instance with POQ
    def POQ(self, instance, p, t):
        return 0

    # return the quantity to order at time t for product p in instance with SilverMeal
    def SilverMeal(self, instance, p, t):
        return 0

    #This method check if the quantity of product p inserted in period t violate the capacity contraitn
    def RepairCapacity( self, p, t ):
        print "To be implemented"