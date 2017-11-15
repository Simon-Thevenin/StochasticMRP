from Constants import Constants
from ScenarioTreeNode import ScenarioTreeNode
from MRPSolution import MRPSolution
from ScenarioTree import ScenarioTree

#This object contains logic and methods to compute the classical MRP in decentralized fashion
class DecentralizedMRP(object):


    # constructor

    def __init__(self, mrpinstance):
        self.Instance =mrpinstance
        self.Solution = None

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

    def GetAverageDemandScenarioTree(self):
        scenariotree = ScenarioTree( self.Instance,
                                     [1]*(self.Instance.NrTimeBucket+1) + [0],
                                     0,
                                     averagescenariotree=True,
                                     scenariogenerationmethod=Constants.MonteCarlo,
                                     model = "YQFix" )

        return scenariotree

    def GetEmptySolution(self):
        scenariotree = self.GetAverageDemandScenarioTree()
        scenarioset = scenariotree.GetAllScenarios(False)
        production = [ [ [  0 for p in self.Instance.ProductSet ] for t in self.Instance.TimeBucketSet ] for w in scenarioset ]
        quanitity = [ [ [  0 for p in self.Instance.ProductSet ] for t in self.Instance.TimeBucketSet ] for w in scenarioset ]
        stock = [ [ [  0 for p in self.Instance.ProductSet ] for t in self.Instance.TimeBucketSet ] for w in scenarioset ]
        backorder = [ [ [  0 for p in self.Instance.ProductWithExternalDemand ] for t in self.Instance.TimeBucketSet ] for w in scenarioset ]
        result = MRPSolution( instance=self.Instance,
                              scenriotree=scenariotree,
                              scenarioset=scenarioset,
                              solquantity=quanitity,
                              solproduction=production,
                              solbackorder=backorder,
                              solinventory=stock)
        result.NotCompleteSolution = True
        return result

    #This method solve the instance given in argument wth the rule given in argument
    #The problem is decomposed by product, starting from end item to highest level component.
    #After each planning decision, the capacity is checked, and repair is applied if required.
    def SolveWithSimpleRule( self,  rule ):
        # Create an empty solution
        self.Solution = self.GetEmptySolution()

        # sort the prduct by level
        self.LevelSet = sorted(set(self.Instance.Level), reverse=True)

        # For each product, at each time periode, apply the decision rule to find the quantity to produce / order
        for l in self.LevelSet:
            prodinlevel = [p for p in self.Instance.ProductSet if self.Instance.Level[p] == l]
            for p in prodinlevel:
                for t in  self.Instance .TimeBucketSet:
                    self.GetIdealQuantityToOrder( p, t, rule)

                    # After each decision, check capacity, and repair if necessary
                    self.RepairCapacity(p, t)

        self.Solution.Print()

    # This method apply lot for lot to solve the instance
    def GetIdealQuantityToOrder(self,  p, t, rule):
        if rule == Constants.L4L:
            self.LotForLot( p, t)
        if rule == Constants.EOQ:
            self.EOQ( p, t)
        if rule == Constants.POQ:
            self.POQ( p, t)
        if rule == Constants.SilverMeal:
            self.SilverMeal( p, t)

    #return the quantity to order at time t for product p in instance with Lot for Lot rule
    def LotForLot( self, p, t ):
        print "prodct %r time %r"%(p,t)
        prevquanity  = [ [ self.Solution.ProductionQuantity[0][t1][p1] for  p1 in self.Instance.ProductSet] for t1 in self.Instance.TimeBucketSet ]
        prevdemand = [ [ self.Solution.Scenarioset[0].Demands[t1][p1] for  p1 in self.Instance.ProductSet] for t1 in self.Instance.TimeBucketSet ]
        print prevdemand
        projectedbackorder, projectedinventory, currrentstocklevel = self.Solution.GetCurrentStatus( prevdemand, prevquanity, t + self.Instance.Leadtimes[p] )


        quantity = - projectedinventory[p]

        if self.Instance.HasExternalDemand[p]:
            quantity = quantity + projectedbackorder[p]

        self.Solution.ProductionQuantity[0][t][p] = quantity

        return quantity

    # return the quantity to order at time t for product p in instance with EOQ
    def EOQ(self, p, t):
        return 0

    # return the quantity to order at time t for product p in instance with POQ
    def POQ(self, p, t):
        return 0

    # return the quantity to order at time t for product p in instance with SilverMeal
    def SilverMeal(self, p, t):
        return 0

    #This method check if the quantity of product p inserted in period t violate the capacity contraitn
    def RepairCapacity( self, p, t ):
        print "To be implemented"