import pandas as pd
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
        if Constants.PrintSolutionFileInTMP:
            result = "/tmp/thesim/Solutions/" + description + "_Solution.xlsx"
        else:
            result ="./Solutions/"+  description + "_Solution.xlsx"
        return result

    def GetSolutionPickleFileNameStart(self, description, dataframename):
        if Constants.PrintSolutionFileInTMP:
            result = "/tmp/thesim/Solutions/" + description + "_" + dataframename
        else:
            result ="./Solutions/"+  description + "_" + dataframename
        return result

    def GetGeneralInfoDf(self):
        model = ""
        if not self.ScenarioTree.Owner is None:
            model = self.ScenarioTree.Owner.Model
        else:
            model = "Rule"
        general = [self.MRPInstance.InstanceName, self.MRPInstance.Distribution, model,
                   self.CplexCost, self.CplexTime, self.TotalTime, self.CplexGap, self.CplexNrConstraints, self.CplexNrVariables, self.IsPartialSolution]
        columnstab = ["Name", "Distribution", "Model", "CplexCost", "CplexTime", "TotalTime", "CplexGap", "CplexNrConstraints",
                      "CplexNrVariables", "IsPartialSolution"]
        generaldf = pd.DataFrame(general, index=columnstab)
        return generaldf
    # This function print the solution different pickle files
    def PrintToPickle(self, description):
            prodquantitydf, inventorydf, productiondf, bbackorderdf = self.DataFrameFromList()

            prodquantitydf.to_pickle( self.GetSolutionPickleFileNameStart(description, 'ProductionQuantity') )
            productiondf.to_pickle( self.GetSolutionPickleFileNameStart(description,  'Production') )
            inventorydf.to_pickle( self.GetSolutionPickleFileNameStart(description,  'InventoryLevel') )
            bbackorderdf.to_pickle( self.GetSolutionPickleFileNameStart(description,  'BackOrder') )

            generaldf = self.GetGeneralInfoDf()
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

        generaldf = self.GetGeneralInfoDf()
        generaldf.to_excel(writer, "Generic")

        scenariotreeinfo = [self.MRPInstance.InstanceName, self.ScenarioTree.Seed, self.ScenarioTree.TreeStructure, self.ScenarioTree.AverageScenarioTree, self.ScenarioTree.ScenarioGenerationMethod]
        columnstab = ["Name", "Seed", "TreeStructure", "AverageScenarioTree", "ScenarioGenerationMethod" ]
        scenariotreeinfo = pd.DataFrame( scenariotreeinfo, index=columnstab)
        scenariotreeinfo.to_excel(writer, "ScenarioTree")


        writer.save()

    def ReadExcelFiles(self, description, index = "", indexbackorder = ""):
        # The supplychain is defined in the sheet named "01_LL" and the data are in the sheet "01_SD"
        prodquantitydf = Tool.ReadMultiIndexDataFrame(self.GetSolutionFileName(description), "ProductionQuantity" )
        productiondf = Tool.ReadMultiIndexDataFrame(self.GetSolutionFileName(description), "Production" )
        inventorydf = Tool.ReadMultiIndexDataFrame(self.GetSolutionFileName(description), "InventoryLevel" )
        bbackorderdf = Tool.ReadMultiIndexDataFrame(self.GetSolutionFileName(description), "BackOrder" )

        wb2 = opxl.load_workbook(self.GetSolutionFileName(description))
        instanceinfo = Tool.ReadDataFrame(wb2, "Generic")
        scenariotreeinfo = Tool.ReadDataFrame(wb2, "ScenarioTree")

        prodquantitydf.index = index
        productiondf.index = index
        inventorydf.index = index
        bbackorderdf.index = [ index[p] for p in indexbackorder]
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
            wb2 = opxl.load_workbook(self.GetSolutionFileName(description))
            instanceinfo = Tool.ReadDataFrame(wb2, "Generic")
            self.MRPInstance = MRPInstance()
            self.MRPInstance.ReadInstanceFromExelFile(instanceinfo.get_value('Name', 0) )
            prodquantitydf, productiondf, inventorydf, bbackorderdf, instanceinfo, scenariotreeinfo = self.ReadExcelFiles( description , index=self.MRPInstance.ProductName, indexbackorder=self.MRPInstance.ProductWithExternalDemand)

        else:
            prodquantitydf, productiondf, inventorydf, bbackorderdf, instanceinfo, scenariotreeinfo = self.ReadPickleFiles( description )

        self.MRPInstance = MRPInstance()
        if Constants.Debug:
            print "Load instance:%r"% instanceinfo.get_value('Name', 0)
        self.MRPInstance.ReadInstanceFromExelFile(instanceinfo.get_value('Name', 0) )


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
                                           model = model)

        self.IsPartialSolution = instanceinfo.get_value('IsPartialSolution', 0)
        self.CplexCost = instanceinfo.get_value( 'CplexCost', 0 )
        self.CplexTime = instanceinfo.get_value( 'CplexTime', 0 )
        self.TotalTime = instanceinfo.get_value( 'TotalTime', 0 )
        self.CplexGap = instanceinfo.get_value( 'CplexGap', 0 )
        self.CplexNrConstraints = instanceinfo.get_value('CplexNrConstraints', 0)
        self.CplexNrVariables = instanceinfo.get_value('CplexNrVariables', 0)

        self.Scenarioset = self.ScenarioTree.GetAllScenarios( False )
        if  self.IsPartialSolution:
            self.Scenarioset = [ self.Scenarioset [ 0 ] ]
        self.SenarioNrset = range(len(self.Scenarioset))
        self.ListFromDataFrame(prodquantitydf, inventorydf, productiondf, bbackorderdf)
        if not self.IsPartialSolution:
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
             self.TotalCost, self.InventoryCost, self.BackOrderCost,  self.SetupCost, self.LostsaleCost, self.VariableCost = self.GetCostInInterval(  self.MRPInstance.TimeBucketSet )


    #This function return the costs encountered in a specific time interval
    def GetCostInInterval(self, timerange):

        inventorycost = 0
        backordercost = 0
        setupcost = 0
        lostsalecost = 0
        variablecost = 0
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

                    variablecost += self.ProductionQuantity[w][t][p] \
                                          * self.MRPInstance.VariableCost[p] \
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

                totalcost = inventorycost + backordercost + setupcost + lostsalecost + variablecost
        return totalcost, inventorycost, backordercost, setupcost, lostsalecost, variablecost

    def GetConsideredTimeBucket(self):
        result = self.MRPInstance.TimeBucketSet
        if self.IsPartialSolution:
            result = range(self.MRPInstance.NrTimeBucketWithoutUncertaintyBefore +1  )
        return result

    def GetConsideredScenarioset(self):
        result = self.Scenarioset
        if self.IsPartialSolution:
            result = [ 0 ]
        return result

    def DataFrameFromList(self):
        scenarioset = range(len(self.Scenarioset) )
        timebucketset = self.GetConsideredTimeBucket()
        solquantity = [ [ self.ProductionQuantity[s][t][p]   for t in timebucketset for s in scenarioset] for p in self.MRPInstance.ProductSet ]
        solinventory = [[self.InventoryLevel[s][t][p]  for t in timebucketset for s in scenarioset ] for p in self.MRPInstance.ProductSet ]
        solproduction = [[self.Production[s][t][p]  for t in self.MRPInstance.TimeBucketSet for s in scenarioset ] for p in self.MRPInstance.ProductSet ]
        solbackorder = [[self.BackOrder[s][t][ self.MRPInstance.ProductWithExternalDemandIndex[p] ]  for t in timebucketset for s in scenarioset ] for p in self.MRPInstance.ProductWithExternalDemand ]

        iterables = [timebucketset, range(len(self.Scenarioset))]
        multiindex = pd.MultiIndex.from_product(iterables, names=['time', 'scenario'])
        prodquantitydf = pd.DataFrame(solquantity, index=self.MRPInstance.ProductName, columns=multiindex)
        prodquantitydf.index.name = "Product"
        inventorydf = pd.DataFrame(solinventory, index=self.MRPInstance.ProductName, columns=multiindex)
        inventorydf.index.name = "Product"
        #Production variables are decided at stage 1 for the complete horizon
        iterablesproduction = [ range(len(self.MRPInstance.TimeBucketSet)) , range(len(self.Scenarioset) )]
        multiindexproduction = pd.MultiIndex.from_product(iterablesproduction, names=['time', 'scenario'])
        productiondf = pd.DataFrame(solproduction, index=self.MRPInstance.ProductName, columns=multiindexproduction)
        productiondf.index.name = "Product"
        nameproductwithextternaldemand = [self.MRPInstance.ProductName[p] for p in self.MRPInstance.ProductWithExternalDemand]
        bbackorderdf = pd.DataFrame(solbackorder, index=nameproductwithextternaldemand, columns=multiindex)
        bbackorderdf.index.name = "Product"

        return prodquantitydf, inventorydf, productiondf, bbackorderdf


    def ListFromDataFrame(self, prodquantitydf, inventorydf, productiondf, bbackorderdf):
        scenarioset = range(len(self.Scenarioset))
        timebucketset = self.GetConsideredTimeBucket()
        self.ProductionQuantity = [ [ [ prodquantitydf.loc[  str(self.MRPInstance.ProductName[ p ]), (t,s)]  for p in self.MRPInstance.ProductSet ]  for t in timebucketset ]for s in scenarioset ]
        self.InventoryLevel = [ [ [inventorydf.loc[  self.MRPInstance.ProductName[ p ], (t,s)] for p in self.MRPInstance.ProductSet]  for t in timebucketset] for s in scenarioset ]
        self.Production = [ [ [productiondf.loc[  self.MRPInstance.ProductName[ p ], (t,s)] for p in self.MRPInstance.ProductSet]  for t in self.MRPInstance.TimeBucketSet] for s in scenarioset ]
        self.BackOrder = [ [ [bbackorderdf.loc[  self.MRPInstance.ProductName[ p ], (t,s)] for p in self.MRPInstance.ProductWithExternalDemand]  for t in timebucketset] for s in scenarioset ]




    #constructor
    def __init__( self, instance = None, solquantity= None, solproduction= None, solinventory= None, solbackorder= None, scenarioset= None, scenriotree= None, partialsolution = False ):
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
        self.LostsaleCost =-1
        self.VariableCost = -1
        self.InSamplePercentOnTime = -1
        self.SetupCost = -1
        self.TotalCost =-1
        self.IsPartialSolution = partialsolution
        self.NotCompleteSolution = False

        if instance is not None and not self.IsPartialSolution:
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
        self.TotalTime = 0
        self.CplexNrConstraints = -1
        self.CplexNrVariables = -1


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
        self.InSamplePercentOnTime = 100 * ( sum( self.InSampleTotalOnTimePerScenario[s] for s in self.SenarioNrset )  ) / totaldemand


    #This function print detailed statistics about the obtained solution (avoid using it as it consume memory)
    def PrintDetailExcelStatistic(self, filepostscript, offsetseed, nrevaluation, solutionseed, testidentifier, evaluationmethod):

        scenarioset = range(len(self.Scenarioset))

        d = datetime.now()
        date = d.strftime('%m_%d_%Y_%H_%M_%S')
        writer = pd.ExcelWriter(
            "./Solutions/" + self.MRPInstance.InstanceName + "_Statistics_" + filepostscript + "_" + date + ".xlsx",
            engine='openpyxl')

        avginventorydf = pd.DataFrame(self.InSampleAverageInventory,
                                      columns=self.MRPInstance.ProductName,
                                      index=self.MRPInstance.TimeBucketSet)

        avginventorydf.to_excel(writer, "AverageInventory")

        avgbackorderdf = pd.DataFrame(self.InSampleAverageBackOrder,
                                      columns=[self.MRPInstance.ProductName[p] for p in
                                               self.MRPInstance.ProductWithExternalDemand],
                                      index=self.MRPInstance.TimeBucketSet)

        avgbackorderdf.to_excel(writer, "AverageBackOrder")

        avgQuantitydf = pd.DataFrame(self.InSampleAverageQuantity,
                                     columns=self.MRPInstance.ProductName,
                                     index=self.MRPInstance.TimeBucketSet)

        avgQuantitydf.to_excel(writer, "AverageQuantity")

        avgSetupdf = pd.DataFrame(self.InSampleAverageSetup,
                                  columns=self.MRPInstance.ProductName,
                                  index=self.MRPInstance.TimeBucketSet)

        avgSetupdf.to_excel(writer, "AverageSetup")

        perscenariodf = pd.DataFrame([self.InSampleTotalDemandPerScenario, self.InSampleTotalBackOrderPerScenario,
                                      self.InSampleTotalLostSalePerScenario],
                                     index=["Total Demand", "Total Backorder", "Total Lost Sales"],
                                     columns=scenarioset)

        perscenariodf.to_excel(writer, "Info Per scenario")

        general = testidentifier + [self.InSampleAverageDemand, offsetseed, nrevaluation, solutionseed, evaluationmethod]
        columnstab = ["Instance", "Model", "Method", "ScenarioGeneration", "NrScenario", "ScenarioSeed",
                      "EVPI", "Average demand", "offsetseed", "nrevaluation", "solutionseed", "evaluationmethod"]
        generaldf = pd.DataFrame(general, index=columnstab)
        generaldf.to_excel(writer, "General")
        writer.save()


    #This function print the statistic in an Excel file
    def PrintStatistics(self, testidentifier, filepostscript, offsetseed, nrevaluation, solutionseed, evaluationduration, insample, evaluationmethod):

        inventorycoststochasticperiod = -1
        setupcoststochasticperiod = -1
        backordercoststochasticperiod =-1

        # Initialize the average inventory level at each level of the supply chain
        AverageStockAtLevel = [-1 for l in range(self.MRPInstance.NrLevel)]
        nrbackorerxperiod = [ - 1 for t in self.MRPInstance.TimeBucketSet]

        nrlostsale = -1
        #To compute every statistic Constants.PrintOnlyFirstStageDecision should be False
        if (not Constants.PrintOnlyFirstStageDecision) or (not insample):

            avginventorydf = pd.DataFrame(self.InSampleAverageInventory,
                                          columns=self.MRPInstance.ProductName,
                                          index=self.MRPInstance.TimeBucketSet)

            if Constants.PrintDetailsExcelFiles:
                self.PrintDetailExcelStatistic( filepostscript, offsetseed, nrevaluation, solutionseed, testidentifier, evaluationmethod )

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
            stochasticperiod = range(self.MRPInstance.NrTimeBucketWithoutUncertaintyBefore, self.MRPInstance.NrTimeBucket - self.MRPInstance.NrTimeBucketWithoutUncertaintyAfter )

            totalcoststochasticperiod, \
            inventorycoststochasticperiod, \
            backordercoststochasticperiod, \
            setupcoststochasticperiod,\
            lostsalecoststochasticperiod, \
            variablecost= self.GetCostInInterval( stochasticperiod )

        kpistat = [ self.CplexCost,
                    self.CplexTime,
                    self.CplexGap,
                    self.CplexNrConstraints,
                    self.CplexNrVariables,
                    self.TotalTime,
                    self.SetupCost,
                    self.InventoryCost,
                    self.InSamplePercentOnTime,
                    self.BackOrderCost,
                    self.LostsaleCost,
                    self.VariableCost,
                    inventorycoststochasticperiod,
                    setupcoststochasticperiod,
                    backordercoststochasticperiod,
                    evaluationduration
                    ] \
                  + AverageStockAtLevel + [0]*(5- self.MRPInstance.NrLevel) + nrbackorerxperiod + [0]*(49 - self.MRPInstance.NrTimeBucket)+[nrlostsale]

        data = testidentifier + [  filepostscript, len( self.Scenarioset ) ] + kpistat
        if Constants.PrintDetailsExcelFiles:
            d = datetime.now()
            date = d.strftime('%m_%d_%Y_%H_%M_%S')
            myfile = open(r'./Test/Statistic/TestResult_%s_%r_%s.csv' % (self.MRPInstance.InstanceName, filepostscript, date), 'w')
            wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
            wr.writerow(data)
            myfile.close()

        return kpistat

    # This function return the current level of stock and back order based on the quantoty ordered and demands of previous perriod
    def GetCurrentStatus(self, prevdemand, prevquanity, time):
        projectedinventory = [ 0 for  p in self.MRPInstance.ProductSet ]
        projectedbackorder = [ 0 for p in self.MRPInstance.ProductWithExternalDemand ]
        currentbackorder = [ 0 for  p in self.MRPInstance.ProductWithExternalDemand ]
        currentinventory = [ 0 for p in self.MRPInstance.ProductSet ]

        # sum of quantity and initial inventory minus demands
        projinventory = [ ( self.MRPInstance.StartingInventories[p]
                                  + sum( prevquanity[t][p] for t in range( max( time - self.MRPInstance.Leadtimes[p] + 1 , 0 ) ) )
                                  - sum( prevquanity[t][q] * self.MRPInstance.Requirements[q][p] for t in range(time +1 ) for q in self.MRPInstance.ProductSet)
                                  - sum( prevdemand[t][p] for t in range( time + 1) ) )
                                    for p in self.MRPInstance.ProductSet ]

        currentinventory = [ ( self.MRPInstance.StartingInventories[p]
                                  + sum( prevquanity[t][p] for t in range( max( time - self.MRPInstance.Leadtimes[p] + 1 , 0 ) ) )
                                  - sum( prevquanity[t][q] * self.MRPInstance.Requirements[q][p] for t in range(time +1 ) for q in self.MRPInstance.ProductSet)
                                  - sum( prevdemand[t][p] for t in range( time ) ) )
                                    for p in self.MRPInstance.ProductSet ]

        for p in self.MRPInstance.ProductSet:
             if projinventory[p] > - 0.0001 : projectedinventory[p] = projinventory[p]
             else:
                 if not self.MRPInstance.HasExternalDemand[p] and not self.NotCompleteSolution:
                     print "inventory: %r " % (projinventory)
                     raise NameError(" A product without external demand cannot have backorder")
                     projectedbackorder[ self.MRPInstance.ProductWithExternalDemandIndex[p] ] = -projinventory[p]


        return projectedbackorder, projinventory, currentinventory


    def GetFeasibleNodesAtTime( self, time, currentlevelofinventory ):
        result =[]

        for n in self.ScenarioTree.Nodes:
            if n.Time == time and n.IsQuantityFeasible( currentlevelofinventory ):
                result.append(n)

        if Constants.Debug:
            nodesid = [ n.NodeNumber for n in result]
            print "Feasible nodes : %r"%nodesid
        return result

    def GetNodesAtTime( self, time, currentlevelofinventory ):
        result =[]

        for n in self.ScenarioTree.Nodes:
            if n.Time == time :
                result.append(n)

        if Constants.Debug:
            nodesid = [ n.NodeNumber for n in result]
            print "Nodes at time t : %r"%nodesid
        return result


    def GetConsideredNodes(self, strategy, time,  currentlevelofinventory, previousnode = None ):
        result = []
        if time >0 and ( strategy == Constants.NearestNeighborBasedOnStateAC or strategy == Constants.NearestNeighborBasedOnDemandAC ) :
            result = previousnode.Branches
        else:
            result = self.GetNodesAtTime( time, currentlevelofinventory)

        if Constants.Debug:
            nodesid = [n.NodeNumber for n in result]
            print "Cosidered nodes : %r" % nodesid
        return result

    def ComputeProductViolation( self, suggestedquantities, previousstocklevel ):
        result = [max( sum( self.MRPInstance.Requirements[q][p] * suggestedquantities[q] for q in self.MRPInstance.ProductSet ) - previousstocklevel[p]
                         , 0.0 )
                  for p in self.MRPInstance.ProductSet]


        return result

    def ComputeResourceViolation( self, suggestedquantities, previousstocklevel ):
        result = [max( sum( self.MRPInstance.ProcessingTime[q][k] * suggestedquantities[q] for q in self.MRPInstance.ProductSet ) - self.MRPInstance.Capacity[k]
                         , 0.0 )
                  for k in self.MRPInstance.ResourceSet]

        return result


    def getProductionCostraintSlack(self,  suggestedquantities, previousstocklevel ):
        result = [ max(previousstocklevel[p] - sum(self.MRPInstance.Requirements[q][p] * suggestedquantities[q] for q in self.MRPInstance.ProductSet),
                       0.0) for p in self.MRPInstance.ProductSet]
        return result

    def getCapacityCostraintSlack(self,  suggestedquantities ):
        result = [ max(self.MRPInstance.Capacity[k] - sum( self.MRPInstance.ProcessingTime[q][k] * suggestedquantities[q] for q in self.MRPInstance.ProductSet ),
                       0.0)   for k in self.MRPInstance.ResourceSet]


        return result

    def ComputeAvailableFulliment( self, product,  productionslack, capacityslack ):
        maxcomponent = min( productionslack[p]/ self.MRPInstance.Requirements[product][p]  if self.MRPInstance.Requirements[product][p] > 0 else Constants.Infinity
                         for p  in self.MRPInstance.ProductSet  )

        maxresource =  min( capacityslack[k]/self.MRPInstance.ProcessingTime[product][k]  if self.MRPInstance.ProcessingTime[product][k]> 0 else Constants.Infinity
                          for k  in self.MRPInstance.ResourceSet )
        result = min(maxcomponent, maxresource)
        return result

    #This function adjust the quantities, to respect the flow constraint
    def RepairQuantityToOrder(self, suggestedquantities, previousstocklevel):

        idealquuantities = [suggestedquantities[p] for p in self.MRPInstance.ProductSet]
        #Compute the viiolation of the flow constraint for each component
        productviolations = self.ComputeProductViolation( suggestedquantities, previousstocklevel )
        productmaxvioalation = np.argmax( productviolations )
        maxproductviolation =  productviolations[ productmaxvioalation ]

        resourceviolations = self.ComputeResourceViolation( suggestedquantities, previousstocklevel )
        resourcemaxvioalation = np.argmax( resourceviolations )
        maxresourceviolation =  resourceviolations[ resourcemaxvioalation ]
        maxviolation = max(maxresourceviolation, maxproductviolation )
        isproductviolation = maxviolation == maxproductviolation
        #While some flow constraints are violated, adjust the quantity to repect the most violated constraint
        while( maxviolation > 0.000001 ) :
            if Constants.Debug:
                print " the max violation %r is from %r " %( maxviolation, productmaxvioalation )

            if isproductviolation:
                producyqithrequirement = [ p for p in self.MRPInstance.ProductSet if self.MRPInstance.Requirements[p][productmaxvioalation] > 0]
                totaldemand = sum( self.MRPInstance.Requirements[q][productmaxvioalation] * suggestedquantities[q] for q in self.MRPInstance.ProductSet )
                ratiodemande = [ self.MRPInstance.Requirements[q][productmaxvioalation] * suggestedquantities[q] / totaldemand for q in self.MRPInstance.ProductSet ]
            else:
                producyqithrequirement = [p for p in self.MRPInstance.ProductSet if
                                          self.MRPInstance.ProcessingTime[p][resourcemaxvioalation] > 0]
                totaldemand = sum( self.MRPInstance.ProcessingTime[q][resourcemaxvioalation] * suggestedquantities[q] for q in self.MRPInstance.ProductSet)
                ratiodemande = [ self.MRPInstance.ProcessingTime[q][resourcemaxvioalation] * suggestedquantities[q] / totaldemand for q in self.MRPInstance.ProductSet]

            for p in producyqithrequirement:
                quantitytoremove =  (1.0*maxviolation) * ratiodemande[p]
                suggestedquantities[ p ] = max( suggestedquantities[ p ]  - quantitytoremove, 0 )

            #if Constants.Debug:
            #    print " new quantities: %r " %( suggestedquantities )

            productviolations    = self.ComputeProductViolation(suggestedquantities, previousstocklevel)
            productmaxvioalation = np.argmax(productviolations)
            maxproductviolation = productviolations[productmaxvioalation]

            resourceviolations = self.ComputeResourceViolation(suggestedquantities, previousstocklevel)
            resourcemaxvioalation = np.argmax(resourceviolations)
            maxresourceviolation = resourceviolations[resourcemaxvioalation]
            maxviolation = max(maxresourceviolation, maxproductviolation)
            isproductviolation = maxviolation == maxproductviolation

        for p in self.MRPInstance.ProductSet:
            productionslack = self.getProductionCostraintSlack(suggestedquantities, previousstocklevel)
            capacityslack = self.getCapacityCostraintSlack(suggestedquantities)
            suggestedquantities[p] = suggestedquantities[p] + min( idealquuantities[p] - suggestedquantities[p],
                                                                       self.ComputeAvailableFulliment(p, productionslack, capacityslack) )

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
        #print smallestdistance
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

        previousdemands2 = previousdemands+[[0 for p in  self.MRPInstance.ProductSet]]
        projectedbackorder, projectedstocklevel, currrentstocklevel = self.GetCurrentStatus(previousdemands2, previousquantity, time)

        quantity = [ 0  for p in self.MRPInstance.ProductSet]

        level = [ self.MRPInstance.Level[p] for p in self.MRPInstance.ProductSet]
        levelset = sorted(set(level), reverse=False)
        for l in levelset:
            prodinlevel = [p for p in self.MRPInstance.ProductSet if self.MRPInstance.Level[p]== l]
            for p in prodinlevel:
                if self.Production[0][time][p] >= 0.99:
                          quantity[p] = max( self.SValue[time][p] - self.MRPInstance.StartingInventories[p] \
                                                       - sum( previousquantity[t][p]
                                                              - previousdemands[t][p]
                                                              - sum(previousquantity[t][q] * self.MRPInstance.Requirements[q][p] for q in self.MRPInstance.ProductSet ) #external demand
                                                              for t in range( time ) ) \
                                                        + sum(quantity[q] * self.MRPInstance.Requirements[q][p]
                                                               for q in self.MRPInstance.ProductSet)
                                             , 0)  # external demand of the current period
                          #print "ATTTENTION REMOVE tAHT if IT DOESNOT WORK %r %r"%(self.InventoryLevel, self.MRPInstance.TotalRequirement)
                          # quantity[p] =  max( self.SValue[time][p]
                          #                     -  sum( projectedstocklevel[q] * self.MRPInstance.TotalRequirement[q][p]
                          #                              for q in self.MRPInstance.ProductSet if self.MRPInstance.HasExternalDemand[q])
                          #                    , 0) # self.Instance.StartingInventories[p]


                          # maxl =  max(levelset)
       # prodinlevel = [p for p in self.MRPInstance.ProductSet if not self.MRPInstance.Level[p] == maxl]
       # for p in prodinlevel:
       #     if self.Production[0][time][p] >= 0.99:
       #         quantity[p] = 10000


        #if Constants.Debug:
        #    print "Chosen quantities for time %r : %r" % (time, quantity)
        self.RepairQuantityToOrder(quantity, projectedstocklevel)
        #if Constants.Debug:
        #    print "Quantities after repair for time %r : %r" % (time, quantity)

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
        probatime = [ [0 for p in self.MRPInstance.ProductSet ] for t in self.MRPInstance.TimeBucketSet ]

        for w in range( len(self.Scenarioset) ):
            s =self.Scenarioset[w]
            for n in s.Nodes:
                    t= n.Time
                    for p in self.MRPInstance.ProductSet:
                        if   t< self.MRPInstance.NrTimeBucket and  (self.Production[ w][ t ][ p ] >=0.9 ):
                            #if n.GetS( p) > S[t][p]:
                            #    S[t][p] = n.GetS( p)
                            S[t][p] = S[t][p] + n.GetS( p) * s.Probability
                            probatime[t][p] = probatime[t][p] + s.Probability


        self.SValue = [ [ S[t][p]/ probatime[t][p] if probatime[t][p] > 0 else 0.0
                          for p in self.MRPInstance.ProductSet ] for t in self.MRPInstance.TimeBucketSet ]

        if Constants.Debug:
            print "The value of S is: %r" % (self.SValue)


    #return the scenario tree of the average demand
    @staticmethod
    def GetAverageDemandScenarioTree(instance):
        scenariotree = ScenarioTree( instance,
                                     [1]*(instance.NrTimeBucket+1) + [0],
                                     0,
                                     averagescenariotree=True,
                                     scenariogenerationmethod=Constants.MonteCarlo,
                                     model = "YQFix" )

        return scenariotree

    #Create an empty solution (all decisions = 0) for the problem
    @staticmethod
    def GetEmptySolution( instance ):
        scenariotree = MRPSolution.GetAverageDemandScenarioTree( instance )
        scenarioset = scenariotree.GetAllScenarios(False)
        production = [ [ [  0 for p in instance.ProductSet ] for t in instance.TimeBucketSet ] for w in scenarioset ]
        quanitity = [ [ [  0 for p in instance.ProductSet ] for t in instance.TimeBucketSet ] for w in scenarioset ]
        stock = [ [ [  0 for p in instance.ProductSet ] for t in instance.TimeBucketSet ] for w in scenarioset ]
        backorder = [ [ [  0 for p in instance.ProductWithExternalDemand ] for t in instance.TimeBucketSet ] for w in scenarioset ]
        result = MRPSolution( instance=instance,
                              scenriotree=scenariotree,
                              scenarioset=scenarioset,
                              solquantity=quanitity,
                              solproduction=production,
                              solbackorder=backorder,
                              solinventory=stock)

        result.NotCompleteSolution = True
        return result