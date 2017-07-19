import pandas as pd
from Tool import Tool
import csv
from datetime import datetime
import math
from ScenarioTree import ScenarioTree
from Constants import Constants
from Tool import Tool
from MRPInstance import MRPInstance
import openpyxl as opxl
from ast import literal_eval
import numpy as np

class MRPSolution:

    def GetSolutionFileName(self, description):
        result ="./Solutions/"+  description + "_Solution.xlsx"
        return result

    def GetSolutionPickleFileNameStart(self, description, dataframename):
        result ="./Solutions/"+  description + "_" + dataframename
        return result

    # This function print the solution different pickle files
    def PrintToPickle(self, description):
            prodquantitydf, inventorydf, productiondf, bbackorderdf = self.DataFrameFromList()

            prodquantitydf.to_pickle( self.GetSolutionPickleFileNameStart(description, 'ProductionQuantity') )
            productiondf.to_pickle( self.GetSolutionPickleFileNameStart(description,  'Production') )
            inventorydf.to_pickle( self.GetSolutionPickleFileNameStart(description,  'InventoryLevel') )
            bbackorderdf.to_pickle( self.GetSolutionPickleFileNameStart(description,  'BackOrder') )

            general = [self.MRPInstance.InstanceName, self.MRPInstance.Distribution, self.ScenarioTree.Owner.Model,
                       self.CplexCost, self.CplexTime, self.CplexGap]
            columnstab = ["Name", "Distribution", "Model", "CplexCost", "CplexTime", "CplexGap"]
            generaldf = pd.DataFrame(general, index=columnstab)
            generaldf.to_pickle( self.GetSolutionPickleFileNameStart(description, "Generic") )

            scenariotreeinfo = [self.MRPInstance.InstanceName, self.ScenarioTree.Seed, self.ScenarioTree.TreeStructure,
                                self.ScenarioTree.AverageScenarioTree, self.ScenarioTree.ScenarioGenerationMethod]
            columnstab = ["Name", "Seed", "TreeStructure", "AverageScenarioTree", "ScenarioGenerationMethod"]
            scenariotreeinfo = pd.DataFrame(scenariotreeinfo, index=columnstab)
            scenariotreeinfo.to_pickle( self.GetSolutionPickleFileNameStart(description,  "ScenarioTree") )

    #This function print the solution in an Excel file in the folde "Solutions"
    def PrintToExcel(self, description):
        prodquantitydf, inventorydf, productiondf, bbackorderdf = self.DataFrameFromList()
        writer = pd.ExcelWriter( self.GetSolutionFileName( description ), engine='openpyxl')
        #givenquantty = [[self.ProductionQuantity.ix[p, t].get_value(0) for p in self.MRPInstance.ProductSet]
        #                for t in self.MRPInstance.TimeBucketSet]
        #toprint = pd.DataFrame( givenquantty )

        prodquantitydf.to_excel(writer, 'ProductionQuantity')
        productiondf.to_excel(writer, 'Production')
        inventorydf.to_excel(writer, 'InventoryLevel')
        bbackorderdf.to_excel(writer, 'BackOrder')

        general = [  self.MRPInstance.InstanceName, self.MRPInstance.Distribution, self.ScenarioTree.Owner.Model, self.CplexCost, self.CplexTime, self.CplexGap  ]
        columnstab = ["Name", "Distribution", "Model", "CplexCost", "CplexTime", "CplexGap"]
        generaldf = pd.DataFrame( general, index=columnstab )
        generaldf.to_excel(writer, "Generic")

        scenariotreeinfo = [self.MRPInstance.InstanceName, self.ScenarioTree.Seed, self.ScenarioTree.TreeStructure, self.ScenarioTree.AverageScenarioTree, self.ScenarioTree.ScenarioGenerationMethod]
        columnstab = ["Name", "Seed", "TreeStructure", "AverageScenarioTree", "ScenarioGenerationMethod" ]
        scenariotreeinfo = pd.DataFrame( scenariotreeinfo, index=columnstab)
        scenariotreeinfo.to_excel(writer, "ScenarioTree")


        writer.save()

    def ReadExcelFiles(self, description):
        # The supplychain is defined in the sheet named "01_LL" and the data are in the sheet "01_SD"
        prodquantitydf = Tool.ReadMultiIndexDataFrame(self.GetSolutionFileName(description), "ProductionQuantity")
        productiondf = Tool.ReadMultiIndexDataFrame(self.GetSolutionFileName(description), "Production")
        inventorydf = Tool.ReadMultiIndexDataFrame(self.GetSolutionFileName(description), "InventoryLevel")
        bbackorderdf = Tool.ReadMultiIndexDataFrame(self.GetSolutionFileName(description), "BackOrder")

        wb2 = opxl.load_workbook(self.GetSolutionFileName(description))
        instanceinfo = Tool.ReadDataFrame(wb2, "Generic")
        scenariotreeinfo = Tool.ReadDataFrame(wb2, "ScenarioTree")

        return prodquantitydf, productiondf, inventorydf, bbackorderdf, instanceinfo, scenariotreeinfo

    def ReadPickleFiles(self, description):
        # The supplychain is defined in the sheet named "01_LL" and the data are in the sheet "01_SD"
        prodquantitydf = pd.read_pickle( self.GetSolutionPickleFileNameStart( description, 'ProductionQuantity' ) )
        productiondf = pd.read_pickle( self.GetSolutionPickleFileNameStart( description, 'Production' ) )
        inventorydf = pd.read_pickle( self.GetSolutionPickleFileNameStart( description, 'InventoryLevel' ) )
        bbackorderdf = pd.read_pickle( self.GetSolutionPickleFileNameStart( description, 'BackOrder' ) )

        instanceinfo = pd.read_pickle(self.GetSolutionPickleFileNameStart(description, "Generic") )
        scenariotreeinfo = pd.read_pickle(self.GetSolutionPickleFileNameStart(description, "ScenarioTree"))

        return prodquantitydf, productiondf, inventorydf, bbackorderdf, instanceinfo, scenariotreeinfo


    #This function read the instance from the excel file
    def ReadFromFile(self, description):

        if Constants.PrintSolutionFileToExcel:
            prodquantitydf, productiondf, inventorydf, bbackorderdf, instanceinfo, scenariotreeinfo = self.ReadExcelFiles( description )
        else:
            prodquantitydf, productiondf, inventorydf, bbackorderdf, instanceinfo, scenariotreeinfo = self.ReadPickleFiles( description )

        self.MRPInstance = MRPInstance()
        self.MRPInstance.ReadInstanceFromExelFile( instanceinfo.get_value( 'Name', 0 ), instanceinfo.get_value( 'Distribution', 0 ), )

        scenariogenerationm = scenariotreeinfo.get_value('ScenarioGenerationMethod', 0)
        avgscenariotree = scenariotreeinfo.get_value( 'AverageScenarioTree', 0 )
        scenariotreeseed = int( scenariotreeinfo.get_value( 'Seed', 0 ) )
        branchingstructure  =  literal_eval( str( scenariotreeinfo.get_value( 'TreeStructure', 0 ) ) )
        model = instanceinfo.get_value( 'Model', 0 )
        RQMCForYQfix = (model == Constants.ModelYQFix and scenariogenerationm == Constants.RQMC )

        self.ScenarioTree = ScenarioTree ( instance = self.MRPInstance,
                                           branchperlevel = branchingstructure,
                                           seed = scenariotreeseed,
                                           averagescenariotree =  avgscenariotree,
                                           scenariogenerationmethod =  scenariogenerationm,
                                           generateRQMCForYQfix = RQMCForYQfix )

        self.CplexCost = instanceinfo.get_value( 'CplexCost', 0 )
        self.CplexTime = instanceinfo.get_value( 'CplexTime', 0 )
        self.CplexGap = instanceinfo.get_value( 'CplexGap', 0 )

        self.Scenarioset = self.ScenarioTree.GetAllScenarios( False )
        self.SenarioNrset = range(len(self.Scenarioset))
        self.ListFromDataFrame(prodquantitydf, inventorydf, productiondf, bbackorderdf)
        self.ComputeCost()

        if model <> Constants.ModelYQFix:
            self.ScenarioTree.FillQuantityToOrderFromMRPSolution(self, self.Scenarioset)
            # for s in range( len(self.Scenarioset) ):
            #     print "Scenario with demand:%r" % self.Scenarioset[s].Demands
            #     print "quantity %r" % [ [ self.ProductionQuantity.loc[self.MRPInstance.ProductName[p], (time, s)] for p in
            #                            self.MRPInstance.ProductSet ] for time in self.MRPInstance.TimeBucketSet]

    #This function prints a solution
    def Print(self):
        prodquantitydf, inventorydf, productiondf, bbackorderdf = self.DataFrameFromList()
        print "production ( cost: %r): \n %r" % ( self.SetupCost , productiondf )
        print "production quantities: \n %r" % prodquantitydf
        print "inventory levels at the end of the periods: ( cost: %r ) \n %r" % ( self.InventoryCost, inventorydf )
        print "backorder quantities:  ( cost: %r ) \n %r" % ( self.BackOrderCost, bbackorderdf )

    #This funciton conpute the different costs (inventory, backorder, setups) associated with the solution.
    def ComputeCost(self):
             self.TotalCost, self.InventoryCost, self.BackOrderCost,  self.SetupCost, self.LostsaleCost = self.GetCostInInterval(  self.MRPInstance.TimeBucketSet )


    #This function return the costs encountered in a specific time interval
    def GetCostInInterval(self, timerange):

        inventorycost = 0
        backordercost = 0
        setupcost = 0
        lostsalecost = 0
        gammas = [math.pow(self.MRPInstance.Gamma, t) for t in self.MRPInstance.TimeBucketSet]
        for w in range(len(self.Scenarioset)):
            for t in timerange:
                for p in self.MRPInstance.ProductSet:

                    inventorycost += self.InventoryLevel[w][t][p] \
                                          * self.MRPInstance.InventoryCosts[p] \
                                          * gammas[t] \
                                          * self.Scenarioset[w].Probability

                    setupcost += self.Production[w][t][p] \
                                      * self.MRPInstance.SetupCosts[p] \
                                      * gammas[t] \
                                      * self.Scenarioset[w].Probability

                    if self.MRPInstance.HasExternalDemand[p]:
                        if t < self.MRPInstance.NrTimeBucket - 1:
                            backordercost += self.BackOrder[w][t][
                                                      self.MRPInstance.ProductWithExternalDemandIndex[p]] \
                                                  * self.MRPInstance.BackorderCosts[p] \
                                                  * gammas[t] \
                                                  * self.Scenarioset[w].Probability
                        else:
                            lostsalecost += self.BackOrder[w][t][
                                                     self.MRPInstance.ProductWithExternalDemandIndex[p]] \
                                                 * self.MRPInstance.LostSaleCost[p] \
                                                 * gammas[t] \
                                                 * self.Scenarioset[w].Probability

                totalcost = inventorycost + backordercost + setupcost + lostsalecost
        return totalcost, inventorycost, backordercost, setupcost, lostsalecost

    def DataFrameFromList(self):
        scenarioset = range(len(self.Scenarioset) )
        solquantity = [ [ self.ProductionQuantity[s][t][p]   for t in self.MRPInstance.TimeBucketSet for s in scenarioset] for p in self.MRPInstance.ProductSet ]
        solinventory = [[self.InventoryLevel[s][t][p]  for t in self.MRPInstance.TimeBucketSet for s in scenarioset ] for p in self.MRPInstance.ProductSet ]
        solproduction = [[self.Production[s][t][p]  for t in self.MRPInstance.TimeBucketSet for s in scenarioset ] for p in self.MRPInstance.ProductSet ]
        solbackorder = [[self.BackOrder[s][t][ self.MRPInstance.ProductWithExternalDemandIndex[p] ]  for t in self.MRPInstance.TimeBucketSet for s in scenarioset ] for p in self.MRPInstance.ProductWithExternalDemand ]

        iterables = [self.MRPInstance.TimeBucketSet, range(len(self.Scenarioset))]
        multiindex = pd.MultiIndex.from_product(iterables, names=['time', 'scenario'])
        prodquantitydf = pd.DataFrame(solquantity, index=self.MRPInstance.ProductName, columns=multiindex)
        prodquantitydf.index.name = "Product"
        inventorydf = pd.DataFrame(solinventory, index=self.MRPInstance.ProductName, columns=multiindex)
        inventorydf.index.name = "Product"
        productiondf = pd.DataFrame(solproduction, index=self.MRPInstance.ProductName, columns=multiindex)
        productiondf.index.name = "Product"
        nameproductwithextternaldemand = [self.MRPInstance.ProductName[p] for p in self.MRPInstance.ProductWithExternalDemand]
        bbackorderdf = pd.DataFrame(solbackorder, index=nameproductwithextternaldemand, columns=multiindex)
        bbackorderdf.index.name = "Product"

        return prodquantitydf, inventorydf, productiondf, bbackorderdf


    def ListFromDataFrame(self, prodquantitydf, inventorydf, productiondf, bbackorderdf):
        scenarioset = range(len(self.Scenarioset))
        self.ProductionQuantity = [ [ [ prodquantitydf.loc[  self.MRPInstance.ProductName[ p ], (t,s)]  for p in self.MRPInstance.ProductSet ]  for t in self.MRPInstance.TimeBucketSet ]for s in scenarioset ]
        self.InventoryLevel = [ [ [inventorydf.loc[  self.MRPInstance.ProductName[ p ], (t,s)] for p in self.MRPInstance.ProductSet]  for t in self.MRPInstance.TimeBucketSet] for s in scenarioset ]
        self.Production = [ [ [productiondf.loc[  self.MRPInstance.ProductName[ p ], (t,s)] for p in self.MRPInstance.ProductSet]  for t in self.MRPInstance.TimeBucketSet] for s in scenarioset ]
        self.BackOrder = [ [ [bbackorderdf.loc[  self.MRPInstance.ProductName[ p ], (t,s)] for p in self.MRPInstance.ProductWithExternalDemand]  for t in self.MRPInstance.TimeBucketSet] for s in scenarioset ]


    #constructor
    def __init__( self, instance = None, solquantity= None, solproduction= None, solinventory= None, solbackorder= None, scenarioset= None, scenriotree= None ):
        self.MRPInstance = instance


        #The set of scenario on which the solution is found
        self.Scenarioset = scenarioset
        self.ScenarioTree = scenriotree
        if not  self.Scenarioset is None:
            self.SenarioNrset = range(len(self.Scenarioset))

        #Create a multi index to store the scenarios and time
        # if  instance is not  None:
        #     iterables = [ self.MRPInstance.TimeBucketSet,   range( len( self.Scenarioset ) )  ]
        #     multiindex = pd.MultiIndex.from_product(iterables, names=['time', 'scenario'])
        #     self.ProductionQuantity = pd.DataFrame( solquantity, index = instance.ProductName, columns = multiindex  )
        #     self.ProductionQuantity.index.name = "Product"
        #     self.InventoryLevel = pd.DataFrame( solinventory, index = instance.ProductName, columns = multiindex )
        #     self.InventoryLevel.index.name = "Product"
        #     self.Production = pd.DataFrame( solproduction, index = instance.ProductName, columns = multiindex  )
        #     self.Production.index.name = "Product"
        #     nameproductwithextternaldemand = [ instance.ProductName[p] for p in instance.ProductWithExternalDemand ]
        #     self.BackOrder = pd.DataFrame( solbackorder,  index = nameproductwithextternaldemand, columns = multiindex  )
        #     self.BackOrder.index.name = "Product"
        # else:
        #     self.ProductionQuantity = None
        #     self.InventoryLevel = None
        #     self.Production = None
        #     self.BackOrder = None
        self.ProductionQuantity = solquantity
        self.InventoryLevel = solinventory
        self.Production = solproduction
        self.BackOrder = solbackorder
        self.InventoryCost = -1
        self.BackOrderCost = -1
        self.SetupCost = -1
        self.TotalCost =-1

        if instance is not None:
            self.ComputeCost()
        #The attribute below compute some statistic on the solution
        self.InSampleAverageInventory = []
        self.InSampleAverageBackOrder = []
        self.InSampleAverageOnTime = []
        self.InSampleAverageQuantity = []
        self.InSampleTotalDemand = -1
        self.InSampleTotalBackOrder = -1
        self.InSampleTotalLostSale = -1
        self.InSampleAverageDemand = -1
        self.InSampleAverageBackOrder = -1
        self.InSampleAverageLostSale = -1

        self.SValue = []

        # The objecie value as outputed by CPLEx,
        self.CplexCost =-1
        self.CplexGap = -1
        self.CplexTime = 0

    #This function compute some statistic on the current solution
    def ComputeStatistics( self ):


        self.InSampleAverageInventory = [ [ sum( self.InventoryLevel[w][t][p] for w in self.SenarioNrset)/  len( self.SenarioNrset )
                                           for p in  self.MRPInstance.ProductSet ]
                                            for t in self.MRPInstance.TimeBucketSet]

        self.InSampleAverageBackOrder =   [ [ sum( self.BackOrder[w][t][ self.MRPInstance.ProductWithExternalDemandIndex[p] ] for w in self.SenarioNrset)/  len( self.SenarioNrset )
                                              for p in self.MRPInstance.ProductWithExternalDemand]
                                                for t in self.MRPInstance.TimeBucketSet]


        self.InSampleAverageQuantity =  [ [ sum( self.ProductionQuantity[w][t][p] for w in self.SenarioNrset)/  len( self.SenarioNrset )
                                            for p in self.MRPInstance.ProductSet]
                                          for t in self.MRPInstance.TimeBucketSet]

        self.InSampleAverageSetup =  [ [ sum( self.Production[w][t][p] for w in self.SenarioNrset)/  len( self.SenarioNrset )
                                         for p in self.MRPInstance.ProductSet]
                                       for t in self.MRPInstance.TimeBucketSet]

        self.InSampleAverageOnTime = [ [ ( sum( max( [ self.Scenarioset[s].Demands[t][p] - self.BackOrder[s][t][ self.MRPInstance.ProductWithExternalDemandIndex[p]  ], 0 ] )
                                           for s in self.SenarioNrset )
                                             / len( self.SenarioNrset ) )
                                              for p in self.MRPInstance.ProductWithExternalDemand ]
                                              for t in self.MRPInstance.TimeBucketSet ]

        self.InSampleTotalDemandPerScenario = [ sum( sum( s.Demands[t ][p]
                                                              for p in self.MRPInstance.ProductSet )
                                                         for t in self.MRPInstance.TimeBucketSet   )
                                                    for s in self.Scenarioset ]

        totaldemand = sum( self.InSampleTotalDemandPerScenario )

        backordertime = range( self.MRPInstance.NrTimeBucket - 1)

        self.InSampleTotalOnTimePerScenario =  [  ( sum (  sum( max( [ self.Scenarioset[s].Demands[t][p] - self.BackOrder[s][t][ self.MRPInstance.ProductWithExternalDemandIndex[p]  ], 0 ] )
                                                    for p in self.MRPInstance.ProductWithExternalDemand )
                                                   for t in self.MRPInstance.TimeBucketSet  )
                                                   )
                                                for s in self.SenarioNrset]
        self.InSampleTotalBackOrderPerScenario = [  sum( self.BackOrder[w][t][ self.MRPInstance.ProductWithExternalDemandIndex[p] ]  for t in backordertime  for p in self.MRPInstance.ProductWithExternalDemand) for w in  self.SenarioNrset ]

        self.InSampleTotalLostSalePerScenario =  [  sum( self.BackOrder[w][self.MRPInstance.NrTimeBucket -1][ self.MRPInstance.ProductWithExternalDemandIndex[p] ] for p in self.MRPInstance.ProductWithExternalDemand) for w in  self.SenarioNrset ]

        nrscenario = len( self.Scenarioset )
        self.InSampleAverageDemand = sum( self.InSampleTotalDemandPerScenario[s] for s in self.SenarioNrset ) / nrscenario
        #self.InSamplePercenBackOrder =  100 * ( sum( self.InSampleTotalBackOrderPerScenario[s] for s in self.SenarioNrset )  ) / totaldemand
        #self.InSamplePercentLostSale = 100 * ( sum( self.InSampleTotalLostSalePerScenario[s] for s in self.SenarioNrset )  ) / totaldemand
        self.InSamplePercentOnTime = 100 * ( sum( self.InSampleTotalOnTimePerScenario[s] for s in self.SenarioNrset )  ) / totaldemand

    #This function print hthe statistic in an Excel file
    def PrintStatistics(self, testidentifier, filepostscript, offsetseed, nrevaluation, solutionseed):

        scenarioset = range(len(self.Scenarioset))

        d = datetime.now()
        date = d.strftime('%m_%d_%Y_%H_%M_%S')
        writer = pd.ExcelWriter("./Solutions/" + self.MRPInstance.InstanceName + "_Statistics_"+filepostscript+"_"+date+".xlsx",
                                engine='openpyxl')

        avginventorydf = pd.DataFrame(self.InSampleAverageInventory,
                                      columns=self.MRPInstance.ProductName,
                                      index=self.MRPInstance.TimeBucketSet)

        avginventorydf.to_excel(writer, "AverageInventory" )

        avgbackorderdf = pd.DataFrame(self.InSampleAverageBackOrder,
                                      columns= [ self.MRPInstance.ProductName[p] for p in self.MRPInstance.ProductWithExternalDemand] ,
                                      index=self.MRPInstance.TimeBucketSet)

        avgbackorderdf.to_excel(writer, "AverageBackOrder" )

        avgQuantitydf = pd.DataFrame(self.InSampleAverageQuantity,
                                      columns=self.MRPInstance.ProductName,
                                      index=self.MRPInstance.TimeBucketSet)

        avgQuantitydf.to_excel(writer, "AverageQuantity" )

        avgSetupdf = pd.DataFrame(self.InSampleAverageSetup,
                                      columns=self.MRPInstance.ProductName,
                                      index=self.MRPInstance.TimeBucketSet)

        avgSetupdf.to_excel(writer, "AverageSetup" )

        perscenariodf = pd.DataFrame([ self.InSampleTotalDemandPerScenario, self.InSampleTotalBackOrderPerScenario, self.InSampleTotalLostSalePerScenario ],
                                     index=[ "Total Demand", "Total Backorder", "Total Lost Sales" ],
                                     columns=scenarioset)

        perscenariodf.to_excel(writer, "Info Per scenario" )


        general = testidentifier+ [ self.InSampleAverageDemand,  offsetseed, nrevaluation, solutionseed ]
        columnstab = [ "Instance", "Distribution",  "Model", "Method", "ScenarioGeneration", "NrScenario", "ScenarioSeed" , "Average demand",  "offsetseed", "nrevaluation", "solutionseed" ]
        generaldf = pd.DataFrame(general, index=columnstab )
        generaldf.to_excel( writer, "General" )
        writer.save()

        #Compute the average inventory level at each level of the supply chain
        AverageStockAtLevel = [ ( sum( sum ( avginventorydf.loc[t,self.MRPInstance.ProductName[p]]
                                    for t in self.MRPInstance.TimeBucketSet )
                                        for p in self.MRPInstance.ProductSet if self.MRPInstance.Level[p] == l +1 ) )
                                / ( sum( 1 for p in self.MRPInstance.ProductSet if self.MRPInstance.Level[p] == l +1 )
                                    * self.MRPInstance.NrTimeBucket )
                                for l in range( self.MRPInstance.NrLevel ) ]

        demandofstagetstillbackorder = [[[[0 for p in self.MRPInstance.ProductWithExternalDemand] for nrperiodago in range(currentperiod+1)]  for currentperiod in self.MRPInstance.TimeBucketSet] for s in self.Scenarioset]

        #Compute the back order per period, and also how long the demand has been backordered
        #The portion $\tilde{B}_{p,t}^{n,\omega}$ of the demand due $n$ time periods ago, which is still back-ordered at time $t$ is computed as:
        #\tilde{B}_{p,t}^{n,\omega} = Max(\tilde{B}_{p,t-1}^{n-1,\omega}, B_{p,t}^{\omega} - \tilde{B}_{p,t}^{n-1,\omega})
        for s in  self.SenarioNrset:
            for p in self.MRPInstance.ProductWithExternalDemand:
                 for currentperiod in self.MRPInstance.TimeBucketSet:
                     for nrperiodago in range(currentperiod+1):
                         indexp = self.MRPInstance.ProductWithExternalDemandIndex[p]
                         if nrperiodago == 0:
                             demandprevinprev = self.Scenarioset[s].Demands[currentperiod][p]
                         elif currentperiod == 0:
                             demandprevinprev = 0
                         else:
                             demandprevinprev = demandofstagetstillbackorder[s][currentperiod - 1][nrperiodago - 1][indexp]

                         if nrperiodago == 0:
                             demandprevincurrent = 0
                         else:
                             demandprevincurrent = demandofstagetstillbackorder[s][currentperiod][nrperiodago == 0 - 1][indexp]

                         demandofstagetstillbackorder[s][currentperiod ][nrperiodago][indexp] = min( demandprevinprev,
                                                                                                max( self.BackOrder[s][currentperiod][indexp] - demandprevincurrent, 0 ) )


        #The lostsales $\bar{L}_{p,t}^{\omega}$ among the demand due at time $t$ is $\tilde{B}_{p,T}^{n,\omega}$.
        lostsaleamongdemandofstage = [[[ demandofstagetstillbackorder[s][self.MRPInstance.NrTimeBucket -1][nrperiodago ][self.MRPInstance.ProductWithExternalDemandIndex[p] ]
                                         for p in self.MRPInstance.ProductWithExternalDemand]
                                       for nrperiodago in range( self.MRPInstance.NrTimeBucket) ]
                                      for s in self.SenarioNrset]

        #The quantity $\bar{B}_{p,t}^{n,\omega}$  of demand of stage $t$ which is backordered during n periods can be computed by:
        #\bar{B}_{p,t}^{n,\omega} =\bar{B}_{p,t + n}^{n,\omega} -\bar{B}_{p,t+ n+ 1}^{n+1,\omega}
        portionbackoredduringtime = [[[[ demandofstagetstillbackorder[s][currentperiod + nrperiod][nrperiod][self.MRPInstance.ProductWithExternalDemandIndex[p] ] \
                                       - demandofstagetstillbackorder[s][currentperiod + nrperiod +1][nrperiod +1][self.MRPInstance.ProductWithExternalDemandIndex[p] ]
                                         if currentperiod + nrperiod + 1 < self.MRPInstance.NrTimeBucket
                                         else demandofstagetstillbackorder[s][currentperiod + nrperiod][nrperiod][self.MRPInstance.ProductWithExternalDemandIndex[p] ]
                                       for p in self.MRPInstance.ProductWithExternalDemand]
                                      for nrperiod in range( self.MRPInstance.NrTimeBucket - currentperiod )]
                                     for currentperiod in self.MRPInstance.TimeBucketSet]
                                    for s in self.SenarioNrset]

        #Avergae on the senario, product, period

        totaldemand = sum( self.Scenarioset[s].Demands[t][p]
                           for s in self.SenarioNrset
                           for p in self.MRPInstance.ProductWithExternalDemand
                           for t in self.MRPInstance.TimeBucketSet )

        nrbackorerxperiod = [  100 * ( sum( portionbackoredduringtime[s][currentperiod][t][self.MRPInstance.ProductWithExternalDemandIndex[p] ]
                                            for p in self.MRPInstance.ProductWithExternalDemand
                                                 for currentperiod in range(self.MRPInstance.NrTimeBucket )
                                                     for s in self.SenarioNrset
                                                        if (t < self.MRPInstance.NrTimeBucket -1 - currentperiod )  )\
                                             / totaldemand )
                                             for t in self.MRPInstance.TimeBucketSet ]

        nrlostsale = 100 * sum( lostsaleamongdemandofstage[s][currentperiod][self.MRPInstance.ProductWithExternalDemandIndex[p] ]
                                    for p in self.MRPInstance.ProductWithExternalDemand
                                      for currentperiod in self.MRPInstance.TimeBucketSet
                                        for s in self.SenarioNrset) \
                            / totaldemand

        self.ComputeCost()
        stochasticperiod = range(self.MRPInstance.NrTimeBucket - self.MRPInstance.NrTimeBucketWithoutUncertainty )
        totalcoststochasticperiod, \
        inventorycoststochasticperiod, \
        backordercoststochasticperiod, \
        setupcoststochasticperiod,\
        lostsalecoststochasticperiod = self.GetCostInInterval( stochasticperiod )
        kpistat = [ self.CplexCost,
                    self.CplexTime,
                    self.CplexGap,
                    self.SetupCost,
                    self.InventoryCost,
                    self.InSamplePercentOnTime,
                    self.BackOrderCost,
                    self.LostsaleCost,
                    inventorycoststochasticperiod,
                    setupcoststochasticperiod,
                    backordercoststochasticperiod
                    ] \
                  + AverageStockAtLevel + [0]*(5- self.MRPInstance.NrLevel) + nrbackorerxperiod + [0]*(50 - self.MRPInstance.NrTimeBucket)+[nrlostsale]

        data = testidentifier + [  filepostscript, len( self.Scenarioset ) ] + kpistat
        d = datetime.now()
        date = d.strftime('%m_%d_%Y_%H_%M_%S')
        myfile = open(r'./Test/Statistic/TestResult_%s_%r_%s.csv' % (
            self.MRPInstance.InstanceName, filepostscript, date), 'wb')
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        wr.writerow(data)
        myfile.close()

        return kpistat

    # This function return the current level of stock and back order based on the quantoty ordered and demands of previous perriod
    def GetCurrentStatus(self, prevdemand, prevquanity, time):
        projectedinventory = [ 0 for  p in self.MRPInstance.ProductSet ]
        projectedbackorder = [ 0 for p in self.MRPInstance.ProductWithExternalDemand ]
        currentbackorder = [ 0 for  p in self.MRPInstance.ProductWithExternalDemand ]
        currrentstocklevel = [ 0 for p in self.MRPInstance.ProductSet ]

        # sum of quantity and initial inventory minus demands
        projinventory = [ ( self.MRPInstance.StartingInventories[p]
                                  + sum( prevquanity[t][p] for t in range( max( time - self.MRPInstance.Leadtimes[p] +1, 0 ) ) )
                                  - sum(  prevquanity[t][q] * self.MRPInstance.Requirements[q][p] for t in range(time ) for q in self.MRPInstance.ProductSet)
                                  - sum( prevdemand[t][p] for t in range( time ) ) )
                                    for p in self.MRPInstance.ProductSet ]


        currentinventory = [ ( self.MRPInstance.StartingInventories[p]
                                  + sum( prevquanity[t][p] for t in range( max( time - self.MRPInstance.Leadtimes[p] , 0 ) ) )
                                  - sum(  prevquanity[t][q] * self.MRPInstance.Requirements[q][p] for t in range(time ) for q in self.MRPInstance.ProductSet)
                                  - sum( prevdemand[t][p] for t in range( time ) ) )
                                    for p in self.MRPInstance.ProductSet ]

        for p in self.MRPInstance.ProductSet:
             if projinventory[p] > - 0.0001 : projectedinventory[p] = projinventory[p]
             else:
                 if not self.MRPInstance.HasExternalDemand[p]:
                     print "inventory: %r " % (currentinventory)
                     raise NameError(" A product without external demand cannot have backorder")
                 projectedbackorder[ self.MRPInstance.ProductWithExternalDemandIndex[p] ] = -projinventory[p]

        if Constants.Debug:
            print "prevdemand: %r "%(prevdemand)
            print "prevquanity: %r "%(prevquanity)
            print "currentbackorder: %r "%(NameError)
            print "projected stock level in next period: %r "%(projectedinventory)

        return projectedbackorder, projectedinventory, currrentstocklevel


    def GetFeasibleNodesAtTime( self, time, currentlevelofinventory ):
        result =[]

        for n in self.ScenarioTree.Nodes:
            if n.Time == time and n.IsQuantityFeasible( currentlevelofinventory ):
                result.append(n)

        if Constants.Debug:
            nodesid = [ n.NodeNumber for n in result]
            print "Feasible nodes : %r"%nodesid
        return result

    def GetConsideredNodes(self, strategy, time,  currentlevelofinventory, previousnode = None ):
        result = []
        if time >0 and ( strategy == Constants.NearestNeighborBasedOnStateAC or strategy == Constants.NearestNeighborBasedOnDemandAC ) :
            result = previousnode.Branches
        else:
            result = self.GetFeasibleNodesAtTime( time, currentlevelofinventory)

        if Constants.Debug:
            nodesid = [n.NodeNumber for n in result]
            print "Cosidered nodes : %r" % nodesid
        return result

    def ComputeViolation( self, suggestedquantities, previousstocklevel ):
        result = [max( sum( self.MRPInstance.Requirements[q][p] * suggestedquantities[q] for q in self.MRPInstance.ProductSet ) - previousstocklevel[p]
                         , 0.0 )
                  for p in self.MRPInstance.ProductSet]


        return result


    #This function adjust the quantities, to respect the flow constraint
    def RepairQuantityToOrder(self, suggestedquantities, previousstocklevel):
        #Compute the viiolation of the flow constraint for each component
        violations = self.ComputeViolation( suggestedquantities, previousstocklevel )

        productmaxvioalation = np.argmax( violations )
        maxviolation =  violations[ productmaxvioalation ]

        #While some flow constraints are violated, adjust the quantity to repect the most violated constraint
        while( maxviolation > 0.00000000000000001 ) :
            if Constants.Debug:
                print " the max violation %r is from %r " %( maxviolation, productmaxvioalation )
            producyqithrequirement = [ p for p in self.MRPInstance.ProductSet if self.MRPInstance.Requirements[p][productmaxvioalation] > 0]
            nrproductrequiringcomponent = len(producyqithrequirement )
            totaldemand = sum( self.MRPInstance.Requirements[q][productmaxvioalation] * suggestedquantities[q] for q in self.MRPInstance.ProductSet )
            ratiodemande = [ self.MRPInstance.Requirements[q][productmaxvioalation] * suggestedquantities[q] / totaldemand for q in self.MRPInstance.ProductSet ]
            for p in producyqithrequirement:
                quantitytoremove =  (1.0*maxviolation) * ratiodemande[p]
                suggestedquantities[ p ] = max( suggestedquantities[ p ]  - quantitytoremove, 0 )

            if Constants.Debug:
                print " new quantities: %r " %( suggestedquantities )

            violations    = self.ComputeViolation(suggestedquantities, previousstocklevel)
            productmaxvioalation = np.argmax(violations)
            maxviolation = violations[productmaxvioalation]

    #This function return the quantity to order a time t, given the first t-1 demands
    def GetQuantityToOrder( self, strategy, time, previousdemands, previousquantity = [], previousnode = None ):
        error = 0
        projectedbackorder, projectedstocklevel, currrentstocklevel = self.GetCurrentStatus( previousdemands, previousquantity, time )
        considerednodes = self.GetConsideredNodes(strategy, time, projectedstocklevel, previousnode = previousnode )


        # Get the scenario with the closest demand
        smallestdistance = Constants.Infinity
        bestnode = None
        #Traverse all scneario
        for n in considerednodes:
            #Compute the distance to the given demand vector
            distance = 0
            if strategy == Constants.NearestNeighborBasedOnStateAC or strategy == Constants.NearestNeighborBasedOnState:
                distance = n.GetDistanceBasedOnStatus( projectedstocklevel, projectedbackorder )
            if strategy == Constants.NearestNeighborBasedOnDemand or strategy == Constants.NearestNeighborBasedOnDemandAC:
                if time > 0:
                    distance = n.GetDistanceBasedOnDemand( previousdemands[time -1] )


            if distance < smallestdistance :
                smallestdistance = distance
                bestnode  = n

        if bestnode == None:
            error = 1
            if Constants.Debug:
                raise NameError(" Nearest neighbor returned Null %r - %r "%(distance , smallestdistance))
        else:
            #Return the decision taken in the closest scenrio
            quantity = [ bestnode.QuantityToOrderNextTime[p] for p in self.MRPInstance.ProductSet ]
            #print "distance %r quantity %r"%(smallestdistance,quantity)
            if Constants.Debug:
                print "Chosen quantities for time %r : %r" %( time, quantity)

            #Make sure the chosen quantity is feasible:
            self.RepairQuantityToOrder( quantity , projectedstocklevel )
            if Constants.Debug:
                print "Quantities after repair for time %r : %r" % (time, quantity)
            return quantity, bestnode, error

            # This function return the quantity to order a time t, given the first t-1 demands

    def GetQuantityToOrderS(self, time, previousdemands, previousquantity=[]):

        projectedbackorder, projectedstocklevel, currrentstocklevel = self.GetCurrentStatus(previousdemands, previousquantity, time)

        quantity = [ 0  for p in self.MRPInstance.ProductSet]
        for p in self.MRPInstance.ProductSet:
            if self.Production[0][time][p] == 1:
                quantity[p] = self.SValue[time][p] - self.MRPInstance.StartingInventories[p] \
                                                   - sum( previousquantity[t][p]
                                                          - previousdemands[t][p]
                                                          - sum(previousquantity[t][q] * self.MRPInstance.Requirements[q][p] for q in self.MRPInstance.ProductSet )
                                                          for t in range( time ) )

        if Constants.Debug:
            print "Chosen quantities for time %r : %r" % (time, quantity)
        self.RepairQuantityToOrder(quantity, projectedstocklevel)
        if Constants.Debug:
            print "Quantities after repair for time %r : %r" % (time, quantity)

        error = 0
        return quantity, error

    #This function merge solution2 into self. Assume that solution2 has a single scenario
    def Merge( self, solution2 ):
        self.Scenarioset.append( solution2.Scenarioset[0] )
        self.SenarioNrset = range(len(self.Scenarioset))
        self.ProductionQuantity = self.ProductionQuantity + solution2.ProductionQuantity
        self.InventoryLevel = self.InventoryLevel + solution2.InventoryLevel
        self.Production = self.Production + solution2.Production
        self.BackOrder = self.BackOrder + solution2.BackOrder

    def ComputeAverageS( self ):
        S = [ [0 for p in self.MRPInstance.ProductSet ] for t in self.MRPInstance.TimeBucketSet ]

        for w in range( len(self.Scenarioset) ):
            s =self.Scenarioset[w]
            for n in s.Nodes:
                    t= n.Time
                    for p in self.MRPInstance.ProductSet:
                        if   t< self.MRPInstance.NrTimeBucket and  (self.Production[ w][ t ][ p ] == 1 ):
                            S[t][p] = S[t][p] + n.GetS( p) * s.Probability


        self.SValue = S

