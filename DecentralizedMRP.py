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
        self.LevelSet = sorted(set(self.Instance.Level), reverse=False)

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
        print prevquanity
        prevdemand = [ [ self.Solution.Scenarioset[0].Demands[t1][p1] for  p1 in self.Instance.ProductSet] for t1 in self.Instance.TimeBucketSet ]
        print prevdemand
        quantity = 0
        if  t + self.Instance.Leadtimes[p] < self.Instance.NrTimeBucket:
            projectedbackorder, projectedinventory, currrentstocklevel = self.Solution.GetCurrentStatus( prevdemand, prevquanity, t + self.Instance.Leadtimes[p]   )

            print projectedinventory
            quantity = - projectedinventory[p]

            if self.Instance.HasExternalDemand[p]:
                quantity = quantity + projectedbackorder[ self.Instance.ProductWithExternalDemandIndex[p]]

        print "Add quantity:%r"%(max( quantity, 0) *3)
        self.Solution.ProductionQuantity[0][t][p] = max( quantity, 0) *3

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
        #Check if the capacity is violated for product p at time t
        quantitytorepplan = self.CheckCapacity( p, t )

        print "quantitytorepplan: %r"%quantitytorepplan

        if quantitytorepplan > 0:
            #Try to move the quantity backward
            success = self.MoveBackward( quantitytorepplan, p, t)

            if not success:
                print "Backward failed"
            #Backward move fail, try to move the quantity forward

            #If forward move fail, remove the quantity




    #This function return the quantity to remove to make the plan feasible according to capacities
    def CheckCapacity( self, p, t ):
        result = -Constants.Infinity
        #for each resource:
        for k in self.Instance.ResourceSet:
            if self.Instance.ProcessingTime[p][k] > 0:
                #compute the capacity violation
                capacityconsumption = sum( self.Instance.ProcessingTime[q][k] * self.Solution.ProductionQuantity[0][t][q] for q in self.Instance.ProductSet)
                violation = capacityconsumption - self.Instance.Capacity[k]
                #Compute the quantity violating
                quantityviolation = violation / self.Instance.ProcessingTime[p][k]


                #record the largest violating quantity
                if result < quantityviolation:
                    result = quantityviolation

        return result

    # This function return the quantity to remove to make the plan feasible according to capacities
    def MoveBackward(self, quantity,  p, t):

        bestspreading = [0 for tau in range(t) ]
        bestspreadingcost = Constants.Infinity

        #For each time period compute the cost of spreading teh quantity from that point
        for tau in range(t):
            #while the remaining quantity is positive, replan as much as possible in the earliest period
            remainingquantity = quantity
            challengingspreading = [0 for tau2 in range(t) ]
            for tau2 in reversed(range(tau + 1)):
                quantityreplanattau2 = min( -self.CheckCapacity(p, tau2), remainingquantity)
                challengingspreading[tau2] = quantityreplanattau2
                remainingquantity = remainingquantity - quantityreplanattau2

            print "tentative psreading %r " % challengingspreading
            if remainingquantity == 0:
                cost = self.ComputeCostReplan(challengingspreading, p, t)
                print "cost %r" %cost
                if cost < bestspreadingcost:
                    bestspreading = [ challengingspreading[tau2]  for tau2 in range(t) ]
                    bestspreadingcost = cost
            else:
                print "spreading non feasible"

        #No feasible solution were found
        if bestspreadingcost == Constants.Infinity:

            return False

        else:
            print "chosen spreading %r" % bestspreading
            self.Solution.ProductionQuantity[0][t][p] = self.Solution.ProductionQuantity[0][t][p] - quantity
            for tau in range(t):
                self.Solution.ProductionQuantity[0][tau][p] =  self.Solution.ProductionQuantity[0][tau][p]  + bestspreading[tau]
            return True

    def ComputeCostReplan( self, spreading, p, t ):

        cost = 0

        #for each period add the inventory cost and setup
        for tau in range(t):
            inventorycost = spreading[tau] * ( (t+1) - tau ) * self.Instance.InventoryCosts[p]
            if spreading[tau] > 0 and self.Solution.ProductionQuantity[0][tau][p] == 0:
                setupcost = self.Instance.SetupCosts[p]
            else: setupcost = 0
            cost = cost + inventorycost + setupcost


        return cost

    # This function return the quantity to remove to make the plan feasible according to capacities
    def MoveForward(self, quantity, p, t):
        print "to be implemented"
        #for each time period greater than t, move as much as possible
        for tau in range(t, self.Instance.NrTimeBucket):
            #get the quantity to move if the
            quantityreplanattau2 = min(-self.CheckCapacity(p, tau), remainingquantity)
            self.Solution.ProductionQuantity[0][tau][p] = quantityreplanattau2
            remainingquantity = remainingquantity - quantityreplanattau2

        #This replaning can lead to an infeasible downstream  schedule.
        #For each downstream product (sorted by level)
            #compute the quantity to shift
            #for each time period (from t to the end of horizon)
                #Get the maximum quanitty which can be shifted to that period (consider capacity and raw material)



        #At the end of the forward, some quantity might not be planned if capacity is very restrictive, but the solution is feasible