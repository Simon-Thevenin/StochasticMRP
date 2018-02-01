from Constants import Constants
from random import randint
import math

class InstanceReader:
    # Constructor
    def __init__(self, instance):
        self.Instance = instance

        self.DependentAverageDemand = []
        self.TimeBetweenOrder = 2
        self.InstanceType = ""
        self.Level = [] #indicates the level of each produce
        self.LevelSet= []
        self.Filename = ""



    # This function reads the number of products, resources, ...
    def ReadInstanceStructure(self):
        # read the data
        # This set of instances assume no capacity
        self.Instance.NrResource = len(self.Instance.ProductName)
        self.Instance.NrProduct = len(self.Instance.ProductName)
        self.Instance.NrTimeBucket = 0
        self.Instance.ComputeIndices()

        self.Level = []  # indicates the level of each produce

        self.LevelSet = []

    # This function creates the lead times
    def CreateLeadTime(self, leadtimestructure):
        self.Instance.Leadtimes = [ 1 for p in self.Instance.ProductSet] #[randint(1, 1) for p in self.Instance.ProductSet]

        productwith0leadtime = []

        if leadtimestructure == 1 :
            productwith0leadtime = productwith0leadtime + [ p for p in self.Instance.ProductSet if self.Instance.Level[p] == 1 ]

            for p in productwith0leadtime:
                    self.Instance.Leadtimes[p] = 0

        if leadtimestructure == 2:
            maxleadtime = 10
            while ( maxleadtime > 5) :
                self.Instance.Leadtimes = [ randint(0, 3) for p in self.Instance.ProductSet]
                maxleadtime = self.Instance.ComputeMaxLeadTime()



    # Compute the requireement from the supply chain. This set of instances assume the requirement of each arc is 1.
    def CreateRequirement(self):
        self.Instance.Requirements = [[0] * self.Instance.NrProduct for _ in self.Instance.ProductSet]
        for i, row in self.Supplychaindf.iterrows():
            self.Instance.Requirements[self.Instance.ProductName.index(row.get_value('destinationStage'))][
                self.Instance.ProductName.index(i)] = 1

    #Generate the inventory costs
    def GenerateHoldingCostCost(self, e="n"):
         # Assume an inventory holding cost of 0.1 per day for now
        holdingcost = 1#0.1 / 250
        self.Instance.InventoryCosts = [0.0] * self.Instance.NrProduct
        # The cost of the product is given by  added value per stage. The cost of the product at each stage must be computed
        addedvalueatstage = self.GetEchelonHoldingCost(e)
        self.Level = self.GetProductLevel()
        self.LevelSet = sorted(set(self.Level), reverse=True)
        for l in self.LevelSet:
            prodinlevel = [p for p in self.Instance.ProductSet if self.Level[p] == l]
            for p in prodinlevel:
                addedvalueatstage[p] = sum(addedvalueatstage[q] * self.Instance.Requirements[p][q] for q in self.Instance.ProductSet) + \
                                       addedvalueatstage[p]
                self.Instance.InventoryCosts[p] = holdingcost * addedvalueatstage[p]

        if Constants.Debug:
            print  "Inventory cost:%r"%self.Instance.InventoryCosts



    def ComputeAverageDependentDemand(self):
        self.Level = self.GetProductLevel()
        self.ActualAvgdemand = [ math.ceil( float( sum(self.Instance.ForecastedAverageDemand[t][p]
                                                       for t in self.Instance.TimeBucketSet) ) \
                                            / float(self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertaintyBefore ) )
                                 for p
                                in self.Instance.ProductSet]
        self.Actualdepdemand = [ [ self.Instance.ForecastedAverageDemand[t][p] for p in self.Instance.ProductSet ] for t in
                                self.Instance.TimeBucketSet ]

        self.DependentAverageDemand = [self.ActualAvgdemand[p] for p in self.Instance.ProductSet]
        self.LevelSet = sorted(set(self.Level), reverse=False)

        for l in self.LevelSet:
            prodinlevel = [p for p in self.Instance.ProductSet if self.Level[p] == l]
            for p in prodinlevel:
                self.DependentAverageDemand[p] = sum(self.DependentAverageDemand[q] * self.Instance.Requirements[q][p]
                                                     for q in self.Instance.ProductSet) \
                                                 + self.DependentAverageDemand[p]
                for t in self.Instance.TimeBucketSet:
                    self.Actualdepdemand[t][p] = sum(self.Actualdepdemand[t][q] * self.Instance.Requirements[q][p]
                                                     for q in self.Instance.ProductSet) \
                                                 + self.Actualdepdemand[t][p]

        # dependentstd = [self.YearlyStandardDevDemands[p] for p in self.ProductSet]
        # self.LevelSet = sorted(set(self.Level), reverse=False)
        # for l in self.LevelSet :
        #    prodinlevel = [p for p in self.ProductSet if self.Level[p] == l]
        #    for p in prodinlevel:
        #        dependentstd[p] = sum(
        #            dependentstd[q] * self.Requirements[q][p] * self.Requirements[q][p] for q in self.ProductSet) + \
        #                          dependentstd[p]

        self.Actualstd = [[self.Instance.ForcastedStandardDeviation[t][p] for p in self.Instance.ProductSet] for t in
                          self.Instance.TimeBucketSet]
        self.LevelSet = sorted(set(self.Level), reverse=False)
        for l in self.LevelSet:
            prodinlevel = [p for p in self.Instance.ProductSet if self.Level[p] == l]
            for t in self.Instance.TimeBucketSet:
                for p in prodinlevel:
                    self.Actualstd[t][p] = sum(self.Actualstd[t][q]
                                               * self.Instance.Requirements[q][p]
                                               * self.Instance.Requirements[q][p] for q in self.Instance.ProductSet) \
                                           + self.Actualstd[t][p]



    def GenerateSetup(self):
        # Assume a starting inventory is the average demand during the lead time
        echeloninventorycost = [self.Instance.InventoryCosts[p] \
                                - sum(
            self.Instance.Requirements[p][q] * self.Instance.InventoryCosts[q] for q in self.Instance.ProductSet)
                                for p in self.Instance.ProductSet]
        print "echeloninventorycost %r" % echeloninventorycost

        self.Instance.SetupCosts = [(self.DependentAverageDemand[p]
                                     * echeloninventorycost[p]
                                     * 0.5
                                     * (self.TimeBetweenOrder) * (self.TimeBetweenOrder))
                                    for p in self.Instance.ProductSet]

    def GenerateCapacity(self):
        self.Instance.NrResource = self.Instance.NrLevel
        self.Instance.ProcessingTime = [[self.Datasheetdf.get_value(self.Instance.ProductName[p], 'stageTime')
                                         if (self.Level[p] == k)   else 0.0

                                         for k in range(self.Instance.NrResource)]
                                        for p in self.Instance.ProductSet]
        capacityfactor = 2;
        self.Instance.Capacity = [
            capacityfactor * sum(self.DependentAverageDemand[p] * self.Instance.ProcessingTime[p][k]
                                 for p in self.Instance.ProductSet)
            for k in range(self.Instance.NrResource)]

    def GenerateCostParameters(self, b, lostsale):
        # Gamma is set to 0.9 which is a common value (find reference!!!)
        self.Instance.Gamma = 1.0
        # Back order is twice the  holding cost as in :
        # Solving the capacitated lot - sizing problem with backorder consideration CH Cheng1 *, MS Madan2, Y Gupta3 and S So4
        # See how to set this value
        self.Instance.BackorderCosts = [b * self.Instance.InventoryCosts[p] for p in self.Instance.ProductSet]
        self.Instance.LostSaleCost = [lostsale * self.Instance.InventoryCosts[p] for p in self.Instance.ProductSet]

    def GenerateVariableCost(self):
         self.Instance.VariableCost = [ sum( self.Instance.Requirements[p][q] * self.Instance.InventoryCosts[q]
                                              for q in self.Instance.ProductSet )
                                         for p in self.Instance.ProductSet ]


    def GetfinishProduct(self):

        finishproduct = []
        for p in self.Instance.ProductSet:
            if sum(1 for q in self.Instance.ProductSet if self.Instance.Requirements[q][p]) == 0:
                finishproduct.append(p)

        return finishproduct


    def IsStationnaryDistribution(self):
        stationarydistribution = (self.Instance.Distribution == Constants.Normal) \
                                 or (self.Instance.Distribution == Constants.SlowMoving) \
                                 or (self.Instance.Distribution == Constants.Lumpy) \
                                 or (self.Instance.Distribution == Constants.Uniform) \
                                 or (self.Instance.Distribution == Constants.Binomial)
        return stationarydistribution

    def GenerateStationaryDistribution(self ):

        finishproduct = self.GetfinishProduct()

        # Generate the sets of scenarios
        if self.Instance.Distribution == Constants.SlowMoving:
            self.Instance.YearlyAverageDemand = [ 1 if  p in finishproduct else 0 for p in self.Instance.ProductSet]

            self.Instance.YearlyStandardDevDemands = [ 1 if p in finishproduct else 0 for p in self.Instance.ProductSet]

        if self.Instance.Distribution == Constants.Binomial:
            self.Instance.YearlyAverageDemand = [ 3.5 if p in finishproduct else 0 for p in self.Instance.ProductSet]

            self.Instance.YearlyStandardDevDemands = [1 if p in finishproduct else 0 for p in self.Instance.ProductSet]

        if self.Instance.Distribution == Constants.Uniform:
            self.Instance.YearlyAverageDemand = [ 0.5 if p  in finishproduct else 0 for p in self.Instance.ProductSet]

        self.Instance.ForecastedAverageDemand = [ [self.Instance.YearlyAverageDemand[p]
                                                 if t >= self.Instance.NrTimeBucketWithoutUncertaintyBefore
                                                 else 0
                                                 for p in self.Instance.ProductSet ]
                                                 for t in self.Instance.TimeBucketSet ]

        self.Instance.ForcastedStandardDeviation = [ [ self.Instance.YearlyStandardDevDemands[p]
                                                    if t >= self.Instance.NrTimeBucketWithoutUncertaintyBefore
                                                    else 0
                                                    for p in self.Instance.ProductSet ]
                                                    for t in self.Instance.TimeBucketSet]
        self.Instance.ForecastError = [-1 for t in self.Instance.TimeBucketSet]
        self.Instance.RateOfKnownDemand = 0.0


    # This funciton read the instance from the file ./Instances/MSOM-06-038-R2.xlsx
    def ReadFromFile(self, instancename, distribution = "NonStationary", b=2, forcasterror = 25, e="n", rateknown = 90, leadtimestructure = 1, lostsale = 2, longtimehoizon = False, capacityfactor = 2):

        self.Instance.InstanceName = "%s_%s_b%s_fe%s_e%s_rk%s_ll%s_l%s_H%s_c%s"%(instancename, distribution, b, forcasterror, e, rateknown, leadtimestructure, lostsale, longtimehoizon, capacityfactor)
        self.Instance.Distribution = distribution
        self.Filename = instancename
        self.OpenFiles(instancename)

        self.ReadProductList()
        self.ReadInstanceStructure()
        self.ReadNrResource()

        self.CreateRequirement()
        self.Instance.ComputeLevel()
        self.CreateLeadTime(leadtimestructure)
        self.GenerateHoldingCostCost(e)


        self.Instance.ComputeMaxLeadTime()
        self.GenerateTimeHorizon( longtimehoizon )
        self.GenerateDistribution( float(forcasterror/100.0), float( rateknown/100.0 ), longtimehorizon = longtimehoizon )
        self.ComputeAverageDependentDemand()
        self.GenerateStartinInventory()
        self.GenerateSetup(e)
        self.GenerateCapacity( capacityfactor )
        self.GenerateCostParameters( b, lostsale )
        self.GenerateVariableCost()
        self.Instance.SaveCompleteInstanceInExelFile()
        self.Instance.ComputeInstanceData()
