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

class MRPSolution:

    def GetSolutionFileName(self, description):
        result ="./Solutions/"+  description + "_Solution.xlsx"
        return result
    #This function print the solution in an Excel file in the folde "Solutions"
    def PrintToExcel(self, description):
        writer = pd.ExcelWriter( self.GetSolutionFileName( description ), engine='openpyxl')
        #givenquantty = [[self.ProductionQuantity.ix[p, t].get_value(0) for p in self.MRPInstance.ProductSet]
        #                for t in self.MRPInstance.TimeBucketSet]
        #toprint = pd.DataFrame( givenquantty )

        self.ProductionQuantity.to_excel(writer, 'ProductionQuantity')
        self.Production.to_excel(writer, 'Production')
        self.InventoryLevel.to_excel(writer, 'InventoryLevel')
        self.BackOrder.to_excel(writer, 'BackOrder')

        general = [  self.MRPInstance.InstanceName, self.MRPInstance.Distribution, self.ScenarioTree.Owner.Model, self.CplexCost, self.CplexTime, self.CplexGap  ]
        columnstab = ["Name", "Distribution", "Model", "CplexCost", "CplexTime", "CplexGap"]
        generaldf = pd.DataFrame( general, index=columnstab )
        generaldf.to_excel(writer, "Generic")

        scenariotreeinfo = [self.MRPInstance.InstanceName, self.ScenarioTree.Seed, self.ScenarioTree.TreeStructure, self.ScenarioTree.AverageScenarioTree, self.ScenarioTree.ScenarioGenerationMethod]
        columnstab = ["Name", "Seed", "TreeStructure", "AverageScenarioTree", "ScenarioGenerationMethod" ]
        scenariotreeinfo = pd.DataFrame( scenariotreeinfo, index=columnstab)
        scenariotreeinfo.to_excel(writer, "ScenarioTree")


        writer.save()

    #This function read the instance from the excel file
    def ReadFromExcel(self, description):
        wb2 = opxl.load_workbook( self.GetSolutionFileName( description ))

        # The supplychain is defined in the sheet named "01_LL" and the data are in the sheet "01_SD"
        self.ProductionQuantity = Tool.ReadMultiIndexDataFrame(self.GetSolutionFileName( description ), "ProductionQuantity")
        self.Production = Tool.ReadMultiIndexDataFrame(self.GetSolutionFileName( description ), "Production")
        self.InventoryLevel = Tool.ReadMultiIndexDataFrame(self.GetSolutionFileName( description ), "InventoryLevel")
        self.BackOrder = Tool.ReadMultiIndexDataFrame(self.GetSolutionFileName( description ), "BackOrder")
        instanceinfo = Tool.ReadDataFrame(wb2, "Generic")
        scenariotreeinfo =  Tool.ReadDataFrame(wb2, "ScenarioTree")

        self.MRPInstance = MRPInstance()
        self.MRPInstance.ReadInstanceFromExelFile( instanceinfo.get_value( 'Name', 0 ), instanceinfo.get_value( 'Distribution', 0 ), )

        scenariogenerationm = scenariotreeinfo.get_value('ScenarioGenerationMethod', 0)
        model = instanceinfo.get_value( 'Model', 0 )
        RQMCForYQfix = (model == Constants.ModelYQFix and scenariogenerationm == Constants.RQMC )

        self.ScenarioTree = ScenarioTree ( instance = self.MRPInstance,
                                           branchperlevel =  literal_eval(scenariotreeinfo.get_value( 'TreeStructure', 0 )),
                                           seed = int( scenariotreeinfo.get_value( 'Seed', 0 ) ),
                                           averagescenariotree =  scenariotreeinfo.get_value( 'AverageScenarioTree', 0 ),
                                           scenariogenerationmethod =  scenariotreeinfo.get_value( 'ScenarioGenerationMethod', 0 ),
                                           generateRQMCForYQfix = RQMCForYQfix )

        self.CplexCost = instanceinfo.get_value( 'CplexCost', 0 )
        self.CplexTime = instanceinfo.get_value( 'CplexTime', 0 )
        self.CplexGap = instanceinfo.get_value( 'CplexGap', 0 )

        self.Scenarioset = self.ScenarioTree.GetAllScenarios( False )

        self.ComputeCost()

        if model <> Constants.ModelYQFix:
            self.ScenarioTree.FillQuantityToOrderFromMRPSolution(self, self.Scenarioset)
            # for s in range( len(self.Scenarioset) ):
            #     print "Scenario with demand:%r" % self.Scenarioset[s].Demands
            #     print "quantity %r" % [ [ self.ProductionQuantity.loc[self.MRPInstance.ProductName[p], (time, s)] for p in
            #                            self.MRPInstance.ProductSet ] for time in self.MRPInstance.TimeBucketSet]

    #This function prints a solution
    def Print(self):
        print "production ( cost: %r): \n %r" % ( self.SetupCost , self.Production );
        print "production quantities: \n %r" % self.ProductionQuantity ;
        print "inventory levels at the end of the periods: ( cost: %r ) \n %r" % ( self.InventoryCost, self.InventoryLevel );
        print "backorder quantities:  ( cost: %r ) \n %r" % ( self.BackOrderCost, self.BackOrder );

    #This funciton conpute the different costs (inventory, backorder, setups) associated with the solution.
    def ComputeCost(self):
        #multiply by inventory cost per product -> get a vector with cost per time unit and scenario
        inventorycostpertimeandscenar =  self.InventoryLevel.transpose().dot( self.MRPInstance.InventoryCosts )
        setupcostpertimeandscenar = self.Production.transpose().dot( self.MRPInstance.SetupCosts )
        backorderproductwithexternaldemand = [ self.MRPInstance.BackorderCosts[p]  for p in self.MRPInstance.ProductWithExternalDemand ]

        #backordervariable = self.BackOrder.loc[ 0 : ( self.MRPInstance.NrTimeBucket -1 ) ]
        backordercostpertimeandscenar = self.BackOrder.transpose().dot(backorderproductwithexternaldemand)
        #backordercostpertimeandscenar = backordervariable.transpose().dot( backorderproductwithexternaldemand )

        lostsalewithexternaldemand = [ self.MRPInstance.LostSaleCost[p] for p in
                                              self.MRPInstance.ProductWithExternalDemand]

        lostsalevariable = self.BackOrder.iloc[ :, self.BackOrder.columns.get_level_values(0) == ( self.MRPInstance.NrTimeBucket -1 ) ]
        lostsalecosttimeandscenar = lostsalevariable.transpose().dot( lostsalewithexternaldemand )

        #Reshap the vector to get matirces
        inventorycostpertimeandscenar = inventorycostpertimeandscenar.values.reshape( self.MRPInstance.NrTimeBucket, len(  self.Scenarioset ) );
        setupcostpertimeandscenar = setupcostpertimeandscenar.values.reshape( self.MRPInstance.NrTimeBucket, len(  self.Scenarioset ) );
        backordercostpertimeandscenar = backordercostpertimeandscenar.values.reshape( self.MRPInstance.NrTimeBucket, len(  self.Scenarioset ) );
        lostsalecosttimeandscenar = lostsalecosttimeandscenar.values.reshape( 1, len(  self.Scenarioset ));


        #multiply by the probability of each scenatio
        proabailities = [ s.Probability for s in self.Scenarioset ]
        inventorycostpertime = inventorycostpertimeandscenar.dot( proabailities )
        setupcostpertime = setupcostpertimeandscenar.dot( proabailities )
        backordercostpertime = backordercostpertimeandscenar.dot( proabailities )
        lostsalecostpertime = lostsalecosttimeandscenar.dot( proabailities )
        gammas = [ math.pow(self.MRPInstance.Gamma, t) for t in self.MRPInstance.TimeBucketSet ]
        netpresentvalueinventorycostpertime = inventorycostpertime.transpose().dot( gammas )
        netpresentvaluesetupcostpertime = setupcostpertime.transpose().dot( gammas )
        gammadonotconsiderlastperiod = gammas
        gammadonotconsiderlastperiod[ (  self.MRPInstance.NrTimeBucket -1 ) ] = 0
        netpresentvaluebackordercostpertime = backordercostpertime.transpose().dot( gammadonotconsiderlastperiod )
        lastgamma = [ math.pow( self.MRPInstance.Gamma, self.MRPInstance.NrTimeBucket -1 ) ]
        netpresentvaluelostsalecostpertime = lostsalecostpertime.transpose().dot( lastgamma )

        self.InventoryCost = netpresentvalueinventorycostpertime
        self.BackOrderCost = netpresentvaluebackordercostpertime
        self.SetupCost = netpresentvaluesetupcostpertime
        self.LostsaleCost = netpresentvaluelostsalecostpertime
        self.TotalCost =  self.InventoryCost + self.BackOrderCost +  self.SetupCost + self.LostsaleCost



    #constructor
    def __init__( self, instance = None, solquantity= None, solproduction= None, solinventory= None, solbackorder= None, scenarioset= None, scenriotree= None ):
        self.MRPInstance = instance


        #The set of scenario on which the solution is found
        self.Scenarioset = scenarioset
        self.ScenarioTree = scenriotree

        #Create a multi index to store the scenarios and time
        if  instance is not  None:
            iterables = [ self.MRPInstance.TimeBucketSet,   range( len( self.Scenarioset ) )  ]
            multiindex = pd.MultiIndex.from_product(iterables, names=['time', 'scenario'])
            self.ProductionQuantity = pd.DataFrame( solquantity, index = instance.ProductName, columns = multiindex  )
            self.ProductionQuantity.index.name = "Product"
            self.InventoryLevel = pd.DataFrame( solinventory, index = instance.ProductName, columns = multiindex )
            self.InventoryLevel.index.name = "Product"
            self.Production = pd.DataFrame( solproduction, index = instance.ProductName, columns = multiindex  )
            self.Production.index.name = "Product"
            nameproductwithextternaldemand = [ instance.ProductName[p] for p in instance.ProductWithExternalDemand ]
            self.BackOrder = pd.DataFrame( solbackorder,  index = nameproductwithextternaldemand, columns = multiindex  )
            self.BackOrder.index.name = "Product"
        else:
            self.ProductionQuantity = None
            self.InventoryLevel = None
            self.Production = None
            self.BackOrder = None

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

        # The objecie value as outputed by CPLEx,
        self.CplexCost =-1
        self.CplexGap = -1
        self.CplexTime = 0

    #This function compute some statistic on the current solution
    def ComputeStatistics( self ):

        scenarioset = range( len( self.Scenarioset ) )

        self.InSampleAverageInventory = Tool.ComputeAverageOnIndex2( self.InventoryLevel,
                                                                     self.MRPInstance.ProductSet,
                                                                     self.MRPInstance.ProductName,
                                                                     self.MRPInstance.TimeBucketSet,
                                                                     scenarioset  )

        self.InSampleAverageBackOrder =  Tool.ComputeAverageOnIndex2( self.BackOrder,
                                                                      self.MRPInstance.ProductWithExternalDemand,
                                                                      self.MRPInstance.ProductName,
                                                                      self.MRPInstance.TimeBucketSet,
                                                                      scenarioset )

        self.InSampleAverageQuantity =  Tool.ComputeAverageOnIndex2( self.ProductionQuantity,
                                                                     self.MRPInstance.ProductSet,
                                                                     self.MRPInstance.ProductName,
                                                                     self.MRPInstance.TimeBucketSet,
                                                                     scenarioset  )

        self.InSampleAverageSetup =  Tool.ComputeAverageOnIndex2(     self.Production,
                                                                     self.MRPInstance.ProductSet,
                                                                     self.MRPInstance.ProductName,
                                                                     self.MRPInstance.TimeBucketSet,
                                                                     scenarioset  )

        self.InSampleAverageOnTime = [ [ ( sum( max( [ self.Scenarioset[s].Demands[t][p] - self.BackOrder.loc[  self.MRPInstance.ProductName[ p ], (t,s)], 0 ] )
                                           for s in scenarioset )
                                             / len( scenarioset ) )
                                              for p in self.MRPInstance.ProductWithExternalDemand ]
                                              for t in self.MRPInstance.TimeBucketSet ]

        self.InSampleTotalDemandPerScenario = [ sum( sum( s.Demands[t ][p]
                                                              for p in self.MRPInstance.ProductSet )
                                                         for t in self.MRPInstance.TimeBucketSet   )
                                                    for s in self.Scenarioset ]

        backordertime = range( self.MRPInstance.NrTimeBucket - 1)

        self.InSampleTotalOnTimePerScenario =  [  ( sum (  sum( max( [ self.Scenarioset[s].Demands[t][p] - self.BackOrder.loc[  self.MRPInstance.ProductName[ p ], (t,s)], 0 ] )
                                                    for p in self.MRPInstance.ProductWithExternalDemand )
                                                   for t in self.MRPInstance.TimeBucketSet  )
                                                   )
                                                for s in scenarioset]
        self.InSampleTotalBackOrderPerScenario = Tool.ComputeSumOnIndex1Column( self.BackOrder,
                                                                                      self.MRPInstance.ProductWithExternalDemand,
                                                                                      self.MRPInstance.ProductName,
                                                                                      backordertime,
                                                                                      scenarioset )
        self.InSampleTotalLostSalePerScenario =    Tool.ComputeSumOnIndex1Column( self.BackOrder,
                                                                                      self.MRPInstance.ProductWithExternalDemand,
                                                                                      self.MRPInstance.ProductName,
                                                                                      [ self.MRPInstance.NrTimeBucket -1  ],
                                                                                      scenarioset  )
        nrscenario = len( self.Scenarioset )
        self.InSampleAverageDemand = sum( self.InSampleTotalDemandPerScenario[s] for s in scenarioset ) / nrscenario
        self.InSamplePercenBackOrder =  100 * ( sum( self.InSampleTotalBackOrderPerScenario[s] for s in scenarioset ) / nrscenario ) / self.InSampleAverageDemand
        self.InSamplePercentLostSale = 100 * ( sum( self.InSampleTotalLostSalePerScenario[s] for s in scenarioset ) / nrscenario ) / self.InSampleAverageDemand
        self.InSamplePercentOnTime = 100 * ( sum( self.InSampleTotalOnTimePerScenario[s] for s in scenarioset ) / nrscenario ) / self.InSampleAverageDemand

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


        general = testidentifier+ [ self.InSampleAverageDemand, self.InSamplePercenBackOrder, self.InSamplePercentLostSale, offsetseed, nrevaluation, solutionseed ]
        columnstab = [ "Instance", "Distribution",  "Model",  "ScenarioGeneration", "NrScenario", "ScenarioSeed" , "Average demand", "avg back order", "avg lostsale", "offsetseed", "nrevaluation", "solutionseed" ]
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

        self.ComputeCost()

        kpistat = [ self.CplexCost,
                    self.CplexTime,
                    self.CplexGap,
                    self.SetupCost,
                    self.InventoryCost,
                    self.InSamplePercentOnTime,
                    self.InSamplePercenBackOrder,
                    self.InSamplePercentLostSale
                    ] + AverageStockAtLevel

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
        currentbackorder = [ 0 for  p in self.MRPInstance.ProductWithExternalDemand ]
        currrentstocklevel = [ 0 for p in self.MRPInstance.ProductSet ]

        # sum of quantity and initial inventory minus demands
        inventory = [ ( self.MRPInstance.StartingInventories[p]
                      + sum( prevquanity[t][p] for t in range( max( time - self.MRPInstance.Leadtimes[p] +2, 0 ) ) )
                      - sum(  prevquanity[t][q] * self.MRPInstance.Requirements[q][p] for t in range(time) for q in self.MRPInstance.ProductSet)
                      - sum( prevdemand[t][p] for t in range( time ) ) )
                        for p in self.MRPInstance.ProductSet ]

        for p in self.MRPInstance.ProductSet:
             if inventory[p] > - 0.0001 : currrentstocklevel[p] = inventory[p]
             else:
                 if not self.MRPInstance.HasExternalDemand[p]:
                     print "inventory: %r " % (inventory)
                     raise NameError(" A product without external demand cannot have backorder")
                 currentbackorder[ self.MRPInstance.ProductWithExternalDemandIndex[p] ] = -inventory[p]

        if Constants.Debug:
            print "prevdemand: %r "%(prevdemand)
            print "prevquanity: %r "%(prevquanity)
            print "currentbackorder: %r "%(currentbackorder)
            print "projected stock level in next period: %r "%(currrentstocklevel)

        return currentbackorder, currrentstocklevel


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

    #This function return the quantity to order a time t, given the first t-1 demands
    def GetQuantityToOrder( self, strategy, time, previousdemands, previousquantity = [], previousnode = None ):
        error = 0
        currentbackorder, currrentstocklevel = self.GetCurrentStatus( previousdemands, previousquantity, time )
        considerednodes = self.GetConsideredNodes(strategy, time, currrentstocklevel, previousnode = previousnode )


        # Get the scenario with the closest demand
        smallestdistance = Constants.Infinity
        bestnode = None
        #Traverse all scneario
        for n in considerednodes:
            #Compute the distance to the given demand vector
            distance = 0
            if strategy == Constants.NearestNeighborBasedOnStateAC or strategy == Constants.NearestNeighborBasedOnState:
                distance = n.GetDistanceBasedOnStatus( currrentstocklevel, currentbackorder )
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
            if Constants.Debug:
                print "Chosen quantities for time %r : %r" %( time, quantity)
            return quantity, bestnode, error

    #This function merge solution2 into self. Assume that solution2 has a single scenario
    def Merge( self, solution2 ):
        self.Scenarioset.append( solution2.Scenarioset[0] )

        newindex = pd.MultiIndex.from_product( [ self.MRPInstance.TimeBucketSet, [ len( self.Scenarioset ) -1 ] ], names = ['time', 'scenario'] )

        #self.ProductionQuantity = pd.DataFrame(solquantity, index=instance.ProductName, columns=multiindex)
        #self.InventoryLevel = pd.DataFrame(solinventory, index=instance.ProductName, columns=multiindex)
        #self.Production = pd.DataFrame(solproduction, index=instance.ProductName, columns=multiindex)
        #nameproductwithextternaldemand = [instance.ProductName[p] for p in instance.ProductWithExternalDemand]
        #self.BackOrder = pd.DataFrame(solbackorder, index=nameproductwithextternaldemand, columns=multiindex)
        solution2.ProductionQuantity.columns = newindex
        self.ProductionQuantity = pd.merge(    self.ProductionQuantity.reset_index(),
                                           solution2.ProductionQuantity.reset_index(),
                                           on=['Product'],
                                           how='outer'
                                           ).set_index(["Product"])

        self.ProductionQuantity.columns = pd.MultiIndex.from_product(
            [ range(len(self.Scenarioset)), self.MRPInstance.TimeBucketSet], names=['scenario', 'time'])


        solution2.InventoryLevel.columns = newindex
        self.InventoryLevel = pd.merge(    self.InventoryLevel.reset_index(),
                                           solution2.InventoryLevel.reset_index(),
                                           on=['Product'],
                                           how='outer'
                                           ).set_index(["Product"])

        self.InventoryLevel.columns = pd.MultiIndex.from_product(
            [ range(len(self.Scenarioset)), self.MRPInstance.TimeBucketSet], names=['scenario', 'time'])
    #    self.InventoryLevel.columns =  self.InventoryLevel.columns.swaplevel()
    #    self.InventoryLevel.sortlevel(0, axis=1, inplace=True)

        solution2.Production.columns = newindex
        self.Production = pd.merge(self.Production.reset_index(),
                                           solution2.Production.reset_index(),
                                           on=['Product'],
                                           how='outer'
                                           ).set_index(["Product"])

        self.Production.columns = pd.MultiIndex.from_product(
            [ range(len(self.Scenarioset)), self.MRPInstance.TimeBucketSet ], names=['scenario', 'time'])


        solution2.BackOrder.columns = newindex
        self.BackOrder = pd.merge(self.BackOrder.reset_index(),
                                   solution2.BackOrder.reset_index(),
                                   on=['Product'],
                                   how='outer'
                                   ).set_index(["Product"])

        self.BackOrder.columns = pd.MultiIndex.from_product(
            [ range(len(self.Scenarioset)), self.MRPInstance.TimeBucketSet ], names=['scenario', 'time'])

    #After having merged two solution, this function reshape the dataframe to have them in 3 dimension
    def ReshapeAfterMerge( self ):
        self.InventoryLevel.columns =  self.InventoryLevel.columns.swaplevel()
        self.InventoryLevel.sortlevel(0, axis=1, inplace=True)
        self.BackOrder.columns = self.BackOrder.columns.swaplevel()
        self.BackOrder.sortlevel(0, axis=1, inplace=True)
        self.Production.columns = self.Production.columns.swaplevel()
        self.Production.sortlevel(0, axis=1, inplace=True)
        self.ProductionQuantity.columns =  self.ProductionQuantity.columns.swaplevel()
        self.ProductionQuantity.sortlevel(0, axis=1, inplace=True)