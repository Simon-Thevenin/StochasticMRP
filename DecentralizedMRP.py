from Constants import Constants
from ScenarioTreeNode import ScenarioTreeNode
from MRPSolution import MRPSolution
#from Solver import Solver

import math

#This object contains logic and methods to compute the classical MRP in decentralized fashion
class DecentralizedMRP(object):


    # constructor
    def __init__(self,  mrpinstance):
        self.Instance =mrpinstance
        self.Solution = None
        self.SafetyStock = None
        self.EOQValues = None
        self.FixUntil = -1
        self.FixedSetup = False

        #This array indicates whether a produt and time period have already been planned
        self.Planned = [ [ False for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet ]

    # Compute the average (dependent) demand
    def ComputeAverageDemand(self):

        depdemand = [sum(self.Instance.ForecastedAverageDemand[t][p] for t in self.Instance.TimeBucketSet)
                     / (self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertaintyBefore)  for p in self.Instance.ProductSet]

        levelset = sorted(set(self.Instance.Level), reverse=False)

        for l in levelset:
            prodinlevel = [p for p in self.Instance.ProductSet if self.Instance.Level[p] == l]
            for p in prodinlevel:
                depdemand[p] = sum(depdemand[q] * self.Instance.Requirements[q][p] for q in self.Instance.ProductSet) \
                               + depdemand[p]

        return depdemand

    def ComputeDependentDemandBasedOnProjectedInventory(self, product):
        result = [ 0 for t in self.Instance.TimeBucketSet ]
        previousdemand = 0
        for t in self.Instance.TimeBucketSet:
                    projectedbackorder, projectedinventory = self.GetProjetedInventory(t)
                    #result[t] += -min(projectedinventory[product], 0) + previousprojected
                    #previousprojected = min(projectedinventory[product], 0)
                    demand = max(-projectedinventory[product], 0)
                    result[t] +=  demand - previousdemand
                    previousdemand = demand


        if self.FixUntil + 2 + self.Instance.Leadtimes[product] < self.Instance.NrTimeBucket:
            result[self.FixUntil + 1 + self.Instance.Leadtimes[product]] = sum(
                result[tau] for tau in range(self.FixUntil + 1, self.FixUntil + 2 + self.Instance.Leadtimes[product]))

        #Do not consider negative demand
        for t in self.Instance.TimeBucketSet:
            result[t] = max( result[t], 0.0)

        return result

    def ComputeDependentDemand( self, product ):
        demand = [ self.Solution.Scenarioset[0].Demands[t][product] for t in self.Instance.TimeBucketSet ]

        levelset = sorted(set(self.Instance.Level), reverse=False)

        for l in levelset:
            prodinlevel = [p for p in self.Instance.ProductSet if self.Instance.Level[p] == l]
            for p in prodinlevel:
                for t in self.Instance.TimeBucketSet:
                    demand[t] += self.Solution.ProductionQuantity[0][t][p] * self.Instance.Requirements[p][product]

        return demand

    #this function compute the Economic order quantity for each item
    def ComputeEOQ(self):

        depdemand = self.ComputeAverageDemand()

        #Use max, because some instance have products with 0 setup cost. EOQ should be greater than 0
        eoq = [  max( round( math.sqrt(2.0 * self.Instance.SetupCosts[p] * depdemand[p] / self.Instance.InventoryCosts[p]), 0), 1) for p in self.Instance.ProductSet]

        return eoq

    #This function compute the period with order according to POQ
    def ComputePOQ(self, product ):

        depdemand = self.ComputeAverageDemand()

        eoq = self.ComputeEOQ()

        poq = [ int(eoq[p] / depdemand[p]) +1 for p in self.Instance.ProductSet ]

        firstperiod = self.GetFirstPeriodOrder( product )
        #print "first period:%r"%firstperiod
        for t in self.Instance.TimeBucketSet:
            if (t >= firstperiod and (((t - firstperiod) % poq[product]) == 0) ):
                self.Solution.Production[0][t][product] = 1
            else:
                self.Solution.Production[0][t][product] = 0

        return poq

    #This return the first period with order (used for POQ and silver meal)
    def GetFirstPeriodOrder(self, p):
        #Find the period where the Projected inventory in negative
        t = self.FixUntil +1
        if  t + self.Instance.Leadtimes[p]< self.Instance.NrTimeBucket :
            projectedbackorder, projectedinventory= self.GetProjetedInventory( t + self.Instance.Leadtimes[p] )
            while projectedinventory[p] > 0 and t + self.Instance.Leadtimes[p]< self.Instance.NrTimeBucket -1:
                t += 1
                projectedbackorder, projectedinventory = self.GetProjetedInventory(t + self.Instance.Leadtimes[p])




        return t

    def ComputeSafetyStock(self):

        # self.LevelSet = sorted(set(self.Instance.Level), reverse=False)
        # incrementalinventorycost = [ [ self.Instance.InventoryCosts[p]
        #                                for p in self.Instance.ProductWithExternalDemand ]
        #                                     for t in self.Instance.TimeBucketSet ]
        #
        # cumulativerequirement = [[ self.Instance.Requirements[p][q]
        #                             for q in self.Instance.ProductSet]
        #                          for p in self.Instance.ProductWithExternalDemand]
        #
        # for l in self.LevelSet:
        #     if l>2:
        #         prodinlevel = [p for p in self.Instance.ProductSet if self.Instance.Level[p] == l]
        #         for q in prodinlevel:
        #             for p in self.Instance.ProductWithExternalDemand:
        #                 cumulativerequirement[p][q] = sum( self.Instance.Requirements[q2][q] * cumulativerequirement[p][q2]
        #                                                    for q2 in self.Instance.ProductSet )
        # for l in self.LevelSet:
        #    for p in self.Instance.ProductWithExternalDemand:
        #          if self.FixUntil + l < self.Instance.NrTimeBucket:
        #             incrementalinventorycost[self.FixUntil + l][p] = self.Instance.InventoryCosts[p]  \
        #                                              - sum (cumulativerequirement[p][q] * self.Instance.InventoryCosts[q]
        #                                                     for q in self.Instance.ProductSet if self.Instance.Level[q] == l)

        safetystock = [ [ 0.0 for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet ]
        for p in self.Instance.ProductWithExternalDemand:
            for t in range(self.FixUntil+1, self.Instance.NrTimeBucket):

                ratio = float(self.Instance.BackorderCosts[p] ) / float((self.Instance.BackorderCosts[p] + self.Instance.InventoryCosts[p] ) )
                #ratio = float(self.Instance.BackorderCosts[p]) / float(
                #    (self.Instance.BackorderCosts[p] + incrementalinventorycost[t][p]))

                #value = norm.ppf( ratio, self.Instance.ForecastedAverageDemand[t][p], self.Instance.ForcastedStandardDeviation[t][p] )
                x = ScenarioTreeNode.TransformInverse([[ratio]],
                                                  1,
                                                  1,
                                                  self.Instance.Distribution,
                                                  [self.Instance.ForecastedAverageDemand[t][p]],
                                                  [self.Instance.ForcastedStandardDeviation[t][p]])[0][0]


                safetystock[t][p] = x - self.Instance.ForecastedAverageDemand[t][p]

        return safetystock







    def FixGivenSolution(self, givensetup, givenquantities, demanduptotimet ):

        self.FixedSetup = ( len(givensetup) > 0 )

        if self.FixUntil  >= 0:
            for p in self.Instance.ProductSet:
                for t in self.Instance.TimeBucketSet:
                    self.Solution.Production[0][t][p] = givensetup[t][p]
                    if t <= self.FixUntil:
                        self.Planned[t][p] = True
                        self.Solution.ProductionQuantity[0][t][p] = givenquantities[t][p]
                        self.Solution.Scenarioset[0].Demands[t][p] = demanduptotimet[t][p]

    #This method solve the instance given in argument wth the rule given in argument
    #The problem is decomposed by product, starting from end item to highest level component.
    #After each planning decision, the capacity is checked, and repair is applied if required.
    def SolveWithSimpleRule( self,  rule, givensetup =[], givenquantities =[], fixuntil = -1, demanduptotimet = [] ):
        # Create an empty solution

        self.Solution = MRPSolution.GetEmptySolution( self.Instance )

        #Fix given solution
        self.FixUntil = fixuntil
        self.FixGivenSolution(givensetup, givenquantities, demanduptotimet)

        #Compute preliminary values
        self.SafetyStock = self.ComputeSafetyStock()
        if rule == Constants.EOQ:
            self.EOQValues = self.ComputeEOQ()


        # sort the prduct by level
        self.LevelSet = sorted(set(self.Instance.Level), reverse=False)

        # For each product, at each time periode, apply the decision rule to find the quantity to produce / order
        for l in self.LevelSet:
            prodinlevel = [p for p in self.Instance.ProductSet if self.Instance.Level[p] == l]
            for p in prodinlevel:
                if rule == Constants.POQ and not self.FixedSetup:
                    self.ComputePOQ(p)
                if rule == Constants.SilverMeal and not  self.FixedSetup:
                    firstperiod = self.GetFirstPeriodOrder(p)
                    for t in range(firstperiod, self.Instance.NrTimeBucket):
                        self.Solution.Production[0][t][p] = 1

                for t in  range( fixuntil+1,  self.Instance.NrTimeBucket):
                    quantity = self.GetIdealQuantityToOrder( p, t, rule)
                    self.Solution.ProductionQuantity[0][t][p]  += quantity
                    self.Planned[t][p] = True

                    # After each decision, check capacity, and repair if necessary
                    self.RepairCapacity(p, t)
        self.RepairRequirement( None )

        self.InferY()

        self.InferInventory()
        if Constants.Debug:
            self.Solution.Print()

        return self.Solution

    # This method apply lot for lot to solve the instance
    def GetIdealQuantityToOrder(self,  p, t, rule):

        #If setup are fixed quantity is 0 if no setup
        if self.FixedSetup and self.Solution.Production[0][t][p] == 0:
            return 0

        result = -1
        if rule == Constants.L4L:
            result = self.LotForLot( p, t)
        if rule == Constants.EOQ:
            result = self.EOQ( p, t)
        if rule == Constants.POQ:
            result = self.POQ( p, t)
        if rule == Constants.SilverMeal:
            result = self.SilverMeal( p, t )

        if Constants.Debug:
            print "Plan prod %r periode %r: suggested quantity: %r" % (p, t, result)

        return result


    def GetProjetedInventory(self, time):
        prevquanity = [[self.Solution.ProductionQuantity[0][t1][p1] for p1 in self.Instance.ProductSet] for t1 in
                       self.Instance.TimeBucketSet]
        prevdemand = [ [ self.Solution.Scenarioset[0].Demands[t1][p1] + self.SafetyStock[t1][p1]
                       for p1 in self.Instance.ProductSet ]
                      for t1 in self.Instance.TimeBucketSet ]
        projectedbackorder, projectedinventory, currrentstocklevel = self.Solution.GetCurrentStatus(prevdemand, prevquanity, time)
        return projectedbackorder, projectedinventory

    #return the quantity to order at time t for product p in instance with Lot for Lot rule
    def LotForLot( self, p, t ):
        quantity = 0
        if  t + self.Instance.Leadtimes[p] < self.Instance.NrTimeBucket:
            projectedbackorder, projectedinventory = self.GetProjetedInventory(  t + self.Instance.Leadtimes[p]   )

            quantity = - projectedinventory[p]

            if self.Instance.HasExternalDemand[p]:
                quantity = quantity + projectedbackorder[ self.Instance.ProductWithExternalDemandIndex[p]]


        quantity = max( quantity, 0)

        return quantity

    # return the quantity to order at time t for product p in instance with EOQ
    def EOQ(self, p, t):
        quantity = 0
        if t + self.Instance.Leadtimes[p] < self.Instance.NrTimeBucket:
            projectedbackorder, projectedinventory = self.GetProjetedInventory(t + self.Instance.Leadtimes[p])

            if projectedinventory[p] < 0:
                #Order a multiple of EOQ
                quantity = ( int(-projectedinventory[p]/self.EOQValues[p])+1 ) * self.EOQValues[p]

        return quantity



    # return the quantity to order at time t for product p in instance with POQ
    def POQ(self, p, t):

        quantity = 0
        if self.Solution.Production[0][t][p] == 1 and  t + self.Instance.Leadtimes[p] < self.Instance.NrTimeBucket:
            demand = self.ComputeDependentDemandBasedOnProjectedInventory( p )

            #order the demand until the next order

            time = t + self.Instance.Leadtimes[p]+1
            quantity =  demand[t + self.Instance.Leadtimes[p]]
            while time < self.Instance.NrTimeBucket and self.Solution.Production[0][time - self.Instance.Leadtimes[p]][p] == 0:
                quantity += demand[ time ]
                time += 1
            #time  = min( time, self.Instance.NrTimeBucket -1 )
            #projectedbackorder, projectedinventory = self.GetProjetedInventory(time)
            #quantity = -projectedinventory[p]

        if Constants.Debug:
            print "Quanitity: %r"% quantity

        return quantity

    # return the quantity to order at time t for product p in instance with SilverMeal
    def SilverMeal(self, p, t):

        bestcost = Constants.Infinity
        bestperiod = -1
        demand = self.ComputeDependentDemandBasedOnProjectedInventory(p)





        quantity = [0]
        if self.Solution.Production[0][t][p] == 1 and t + self.Instance.Leadtimes[p]<self.Instance.NrTimeBucket:
            maxperiod = self.Instance.NrTimeBucket - (t + self.Instance.Leadtimes[p]) +1
            quantity = [0] * maxperiod
            for nrperiod in range(1,maxperiod):
                #Compute the cost associated with ordering until t
                cost = (self.Instance.SetupCosts[p] + sum(tau * demand[t + tau+ self.Instance.Leadtimes[p]]  for tau in range( nrperiod )) ) /nrperiod
                quantity[nrperiod] = sum( demand[t + tau + self.Instance.Leadtimes[p]]  for tau in range( nrperiod ))
                if Constants.Debug:
                    print "nr periods %r, quantity %r, cost %r"%(nrperiod, quantity, cost)
                if cost < bestcost :
                    bestperiod = nrperiod
                    bestcost = cost
        if quantity[bestperiod] > 0:
            for period in range(1, bestperiod):
                self.Solution.Production[0][t+period][p] = 0
                self.Planned[t][p] = True

        return quantity[bestperiod]



    #This method check if the quantity of product p inserted in period t violate the capacity contraitn
    def RepairCapacity( self, p, t ):
        #Check if the capacity is violated for product p at time t
        quantitytorepplan = self.CheckCapacity( p, t )


        if quantitytorepplan > 0:
            #Try to move the quantity backward
            success = self.MoveBackward( quantitytorepplan, p, t)

            if not success:
                if Constants.Debug:
                    print "Backward failed"
                self.MoveForward( quantitytorepplan, p, t)
            #Backward move fail, try to move the quantity forward

            #If forward move fail, remove the quantity

                # Push the production forward to ensure the plan is feasible according to the requirments in components

    def RepairRequirement(self, afterprod):
            # This replaning can lead to an infeasible downstream  schedule.
            # sort the prduct by level
            self.LevelSet = sorted(set(self.Instance.Level), reverse=True)

            # For each product, at each time periode, apply the decision rule to find the quantity to produce / order
            for l in self.LevelSet:
                if afterprod is None or l < self.Instance.Level[afterprod]:
                    prodinlevel = [p for p in self.Instance.ProductSet if self.Instance.Level[p] == l]
                    for p in prodinlevel:
                        # For each downstream product (sorted by level)
                        quantitytoshift = 0

                        # for each time period (from t to the end of horizon)
                        for t in self.Instance.TimeBucketSet:
                            # compute the quantity to shift
                            quantityinviolation = max(self.GetViolation(p, t), 0)
                            quantitytoshift += quantityinviolation
                            self.Solution.ProductionQuantity[0][t][p] -= quantityinviolation
                            # Get the maximum quanitty which can be shifted to that period (consider capacity and raw material)
                            if t < self.Instance.NrTimeBucket - 1:
                                maximumshiftable = max(- self.GetViolation(p, t + 1), 0)
                                shiftedquantity = min(maximumshiftable, quantitytoshift)
                                self.Solution.ProductionQuantity[0][t + 1][p] += shiftedquantity
                                quantitytoshift -= shiftedquantity
                                # At the end of the forward, some quantity might not be planned if capacity is very restrictive, but the solution is feasible


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

     # This function return the quantity to remove to make the plan feasible according to requirementt in components
    def CheckRequirement(self, p, t):
            result = -Constants.Infinity
            # for each resource:
            for q in self.Instance.ProductSet:
                if self.Instance.Requirements[p][q] > 0 and (t-self.Instance.Leadtimes[q] < 0 or self.Planned[t-self.Instance.Leadtimes[q]][q]):
                    #Compute the quantity of q reuire to produce p
                    requiredquantity = self.Instance.Requirements[p][q] * self.Solution.ProductionQuantity[0][t][p]

                   # if (t - self.Instance.Leadtimes[q]) >= 0 :
                    projectedbackorder, projectedinventory = self.GetProjetedInventory( t )

                    quantityviolation = min(requiredquantity, -( projectedinventory[q] / self.Instance.Requirements[p][q] ) )
                    #else:
                    #    quantityviolation = requiredquantity
                    if result < quantityviolation:
                        result = quantityviolation

            return result

    def CheckFixedSetup(self, p, t):
        if self.FixedSetup and self.Solution.Production[0][t][p] == 0:
                return 0
        else:
            return Constants.Infinity

    def GetViolation(self, p, t):
        result = max( self.CheckRequirement( p, t ), self.CheckCapacity( p, t ) )
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
            for tau2 in reversed(range(  self.FixUntil+1, tau + 1)):
                quantityreplanattau2 = min( -self.CheckCapacity(p, tau2), remainingquantity, self.CheckFixedSetup(p, tau2))
                challengingspreading[tau2] = quantityreplanattau2
                remainingquantity = remainingquantity - quantityreplanattau2

            if remainingquantity == 0:
                cost = self.ComputeCostReplan(challengingspreading, p, t)
                if cost < bestspreadingcost:
                    bestspreading = [ challengingspreading[tau2]  for tau2 in range(t) ]
                    bestspreadingcost = cost
            else:
                if Constants.Debug:
                    print "spreading non feasible"

        #No feasible solution were found
        if bestspreadingcost == Constants.Infinity:
            return False

        else:
            if Constants.Debug:
                print "chosen spreading %r" % bestspreading
            self.Solution.ProductionQuantity[0][t][p] -= quantity
            for tau in range(t):
                self.Solution.ProductionQuantity[0][tau][p] +=  bestspreading[tau]
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
    def MoveForward(self, quantity, prod, time):
        remainingquantity = quantity
        self.Solution.ProductionQuantity[0][time][prod] -= remainingquantity
        #for each time period greater than t, move as much as possible
        for tau in range(time, self.Instance.NrTimeBucket):
            #get the quantity to move if the
            quantityreplanattau2 = min(-self.CheckCapacity(prod, tau), remainingquantity)
            self.Solution.ProductionQuantity[0][tau][prod] += quantityreplanattau2
            remainingquantity = remainingquantity - quantityreplanattau2


        self.RepairRequirement( prod )

    #This functioninfer the value of Y from the value of Q
    def InferY( self ):
        self.Solution.Production = [ [ [ 1 if self.Solution.ProductionQuantity[0][t][p] > 0 else 0
                                         for p in self.Instance.ProductSet]
                                         for t in self.Instance.TimeBucketSet ] ]


    #This functioninfer the value of Y from the value of Q
    def InferInventory( self ):
        self.Solution.InventoryLevel = [ [ [ 0 for p in self.Instance.ProductSet ]
                                           for t in self.Instance.TimeBucketSet ] ]

        self.Solution.BackOrder = [[ [ 0 for p in self.Instance.ProductWithExternalDemand ]
                                     for t in self.Instance.TimeBucketSet ] ]
        for t in self.Instance.TimeBucketSet:
            backorder, inventory = self.GetProjetedInventory( t )
            for p in self.Instance.ProductSet:
                self.Solution.InventoryLevel[0][t][p] = max( inventory[p], 0 )
                if self.Instance.HasExternalDemand[p]:
                    self.Solution.BackOrder[0][t][ self.Instance.ProductWithExternalDemandIndex[p] ] =  max( -inventory[ p ], 0 )
