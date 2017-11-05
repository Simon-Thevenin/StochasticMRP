import pandas as pd
import numpy as np
import openpyxl as opxl

import math
from ScenarioTree import ScenarioTree
from ScenarioTreeNode import ScenarioTreeNode
from InstanceReader import InstanceReader
from Scenario import Scenario
import cPickle as pickle
import os
from random import randint
from Tool import Tool
import random
import math
from Constants import Constants
import scipy as scipy

class GraveInstanceReader(InstanceReader):

    # Constructor
    def __init__( self, instance ):
        InstanceReader.__init__(self, instance)
        self.Supplychaindf = None
        self.Datasheetdf = None
        self.Actualdepdemand = [ [ ] ]
        self.ActualAvgdemand =[]
        self.Actualstd = [ [ ] ]

    def ReadProductList(self):
        self.Instance.ProductName = [] #self.Datasheetdf.Index#[row[0] for row in self.DTFile]
        print self.Datasheetdf.index
        for  row in self.Datasheetdf.index:
            print row
            self.Instance.ProductName.append(row)

    #Create datasets from the sheets for instance from Grave 2008
    def OpenFiles(self, instancename):
        wb2 = opxl.load_workbook("./Instances/GraveFiles/MSOM-06-038-R2.xlsx")
        # The supplychain is defined in the sheet named "01_LL" and the data are in the sheet "01_SD"
        self.Supplychaindf = Tool.ReadDataFrame(wb2, instancename + "_LL")
        self.Datasheetdf = Tool.ReadDataFrame(wb2, instancename + "_SD")
        self.Datasheetdf = self.Datasheetdf.fillna(0)

    def ReadNrResource(self):
        self.Instance.NrResource = len(self.Instance.ProductName)

    # Compute the requireement from the supply chain. This set of instances assume the requirement of each arc is 1.
    def CreateRequirement(self):
        self.Instance.Requirements = [[0] * self.Instance.NrProduct for _ in self.Instance.ProductSet]
        for i, row in self.Supplychaindf.iterrows():
            self.Instance.Requirements[self.Instance.ProductName.index(row.get_value('destinationStage'))][self.Instance.ProductName.index(i)] = 1

    def GetEchelonHoldingCost(self, uselessparameter):
         result =  [self.Datasheetdf.get_value(self.Instance.ProductName[p], 'stageCost') for p in self.Instance.ProductSet]
         return result

    def GetProductLevel(self):
         result =  [self.Datasheetdf.get_value(self.Instance.ProductName[p], 'relDepth') for p in self.Instance.ProductSet]
         return result

    def GenerateTimeHorizon(self):
        # Consider a time horizon of 20 days plus the total lead time
        self.Instance.NrTimeBucket =  self.Instance.MaxLeadTime
        self.Instance.NrTimeBucketWithoutUncertaintyBefore = 0
        self.Instance.NrTimeBucketWithoutUncertaintyAfter = 0
        self.Instance.ComputeIndices()

    def GenerateDistribution(self, forecasterror, rateknown):
        # Generate the sets of scenarios
        self.Instance.YearlyAverageDemand = [ self.Datasheetdf.get_value(self.Instance.ProductName[p], 'avgDemand')
                                              for p in self.Instance.ProductSet]


        self.Instance.YearlyStandardDevDemands = [self.Datasheetdf.get_value(self.Instance.ProductName[p], 'stdDevDemand')
                                                    for p in self.Instance.ProductSet]

        if self.Instance.Distribution == Constants.SlowMoving:
            self.Instance.YearlyAverageDemand = [1 if self.Datasheetdf.get_value(self.Instance.ProductName[p], 'avgDemand') > 0
                                                  else 0
                                                for p in self.Instance.ProductSet]
            self.Instance.YearlyStandardDevDemands = [1 if self.Datasheetdf.get_value(self.Instance.ProductName[p], 'avgDemand') > 0
                                                  else 0
                                                for p in self.Instance.ProductSet]

        if self.Instance.Distribution == Constants.Uniform:
            self.Instance.YearlyAverageDemand = [0.5 if self.Datasheetdf.get_value(self.Instance.ProductName[p], 'avgDemand') > 0
                                                 else 0
                                                 for p in self.Instance.ProductSet]


        stationarydistribution = ( self.Instance.Distribution == Constants.Normal) \
                                 or ( self.Instance.Distribution == Constants.SlowMoving) \
                                 or ( self.Instance.Distribution  == Constants.Lumpy) \
                                 or ( self.Instance.Distribution  == Constants.Uniform) \
                                 or ( self.Instance.Distribution  == Constants.Binomial)

        if stationarydistribution:
            self.Instance.ForecastedAverageDemand = [ self.Instance.YearlyAverageDemand for t in self.Instance.TimeBucketSet]
            self.Instance.ForcastedStandardDeviation = [ self.Instance.YearlyStandardDevDemands for t in self.Instance.TimeBucketSet]
            self.Instance.ForecastError = [self.Instance.YearlyStandardDevDemands[p] / self.Instance.YearlyAverageDemand[p]
                                           for t in  self.Instance.TimeBucketSet ]
            self.Instance.RateOfKnownDemand = 0.0
        else:
            self.Instance.ForecastError = [ forecasterror for p in self.Instance.ProductSet]
            self.Instance.RateOfKnownDemand = [math.pow(rateknown, t + 1) for t in self.Instance.TimeBucketSet]
            self.Instance.ForecastedAverageDemand = [[np.floor( np.random.normal(self.Instance.YearlyAverageDemand[p],
                                                                                 self.Instance.YearlyStandardDevDemands[p], 1).clip( min=0.0)).tolist()[0]
                                                      if self.Instance.YearlyStandardDevDemands[p] > 0
                                                      else float( self.Instance.YearlyAverageDemand[p])
                                                      for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet]

            self.Instance.ForcastedStandardDeviation = [ [ (1 - self.Instance.RateOfKnownDemand[t])
                                                           * self.Instance.ForecastError[p]
                                                           * self.Instance.ForecastedAverageDemand[t][p]
                                                           if t < (self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertaintyAfter)
                                                           else 0.0
                                                            for p in self.Instance.ProductSet ]
                                                         for t in self.Instance.TimeBucketSet]



        #This function generate the starting inventory
    def GenerateStartinInventory(self):

        sumdemand = [sum(self.Actualdepdemand[t][p] for t in range(self.TimeBetweenOrder)) if self.Instance.YearlyAverageDemand[p] > 0
                     else sum(self.Actualdepdemand[t][p] for t in range(self.TimeBetweenOrder, min(2 * self.TimeBetweenOrder, self.Instance.NrTimeBucket)))
                     for p in self.Instance.ProductSet]

        sumstd = [sum(self.Actualstd[t][p] for t in range(self.TimeBetweenOrder)) if self.Instance.YearlyAverageDemand[p] > 0
                  else sum(self.Actualstd[t][p] for t in range(self.TimeBetweenOrder, min(2 * self.TimeBetweenOrder, self.Instance.NrTimeBucket)))
                  for p in self.Instance.ProductSet]

        servicelevel = 0.6

        print "Level of product %r"%self.Level
        self.Instance.StartingInventories = [ ScenarioTreeNode.TransformInverse([[servicelevel]],
                                                                       1,
                                                                       1,
                                                                       self.Instance.Distribution,
                                                                       [sumdemand[p]],
                                                                       [sumstd[p]])[0][0]
                                                if ((self.Level[p]) % self.TimeBetweenOrder == 0)
                                                else 0.0
                                               for p in self.Instance.ProductSet  ]

        if self.Instance.Distribution == Constants.Binomial or self.Instance.Distribution == Constants.Uniform:
            self.StartingInventories = [ scipy.stats.binom.ppf(0.75, 2 * sumdemand[p], 0.5)
                                         if ((self.Level[p]) % self.TimeBetweenOrder == 1)
                                         else 0.0
                                         for p in self.Instance.ProductSet]

    def GenerateSetup(self, echelonstocktype):
        # Assume a starting inventory is the average demand during the lead time
        echeloninventorycost =  self.GetEchelonHoldingCost(echelonstocktype)
        #echeloninventorycost = [ self.Instance.InventoryCosts[p] \
        #                         - sum ( self.Instance.Requirements[p][q] * self.Instance.InventoryCosts[q]  for q in self.Instance.ProductSet  )
        #                         for p in self.Instance.ProductSet ]
        print "echeloninventorycost %r" % echeloninventorycost

        self.Instance.SetupCosts = [ ( self.DependentAverageDemand[p]
                              * echeloninventorycost[p]
                              * 0.5
                              * (self.TimeBetweenOrder) * (self.TimeBetweenOrder ) )
                           for p in self.Instance.ProductSet ]

    def GenerateCapacity(self):
        self.Instance.NrResource = self.Instance.NrLevel
        self.Instance.ProcessingTime = [[self.Datasheetdf.get_value(self.Instance.ProductName[p], 'stageTime')
                                            if (self.Level[p] == k)   else 0.0

                                            for k in range(self.Instance.NrResource)]
                                           for p in self.Instance.ProductSet]
        capacityfactor = 2;
        self.Instance.Capacity = [ capacityfactor * sum( self.DependentAverageDemand[p] * self.Instance.ProcessingTime[p][k]
                                                         for p in self.Instance.ProductSet)
                                   for k in range(self.Instance.NrResource)]

    # def  GenerateCostParameters(self):
    #     # Gamma is set to 0.9 which is a common value (find reference!!!)
    #     self.Instance.Gamma = 0.9
    #     # Back order is twice the  holding cost as in :
    #     # Solving the capacitated lot - sizing problem with backorder consideration CH Cheng1 *, MS Madan2, Y Gupta3 and S So4
    #     # See how to set this value
    #     self.Instance.BackorderCosts = [ 2 * self.Instance.InventoryCosts[p] for p in self.Instance.ProductSet ]
    #     self.Instance.LostSaleCost = [ 20 * self.Instance.InventoryCosts[p] for p in self.Instance.ProductSet ]

