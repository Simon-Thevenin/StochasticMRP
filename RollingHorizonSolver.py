from Constants import Constants
from ScenarioTree import ScenarioTree
import time
from MIPSolver import MIPSolver
from DecentralizedMRP import DecentralizedMRP
import copy

from MRPSolution import MRPSolution

class RollingHorizonSolver:

    def __init__(self, instance,  model, treestructure, seed, scenariogenerationmethod, windowsize, usesafetystock, owner ):
        self.GlobalInstance = instance
        self.WindowSize = self.GlobalInstance.MaxLeadTime + windowsize
        self.Owner = owner
        self.Seed = seed
        self.Treestructure =treestructure
        self.Model = model
        self.UseSafetyStock = usesafetystock
        self.ScenarioGenerationResolvePolicy = scenariogenerationmethod

        self.SubInstance = self.CreateSubInstances()
        if Constants.IsRule(self.Model):
            self.HeuristicSolvers = [DecentralizedMRP(instance) for instance in self.SubInstance]
            self.RollingHorizonMIPs = [None for instance in self.SubInstance ]
        else:
            self.RollingHorizonMIPs = self.DefineMIPsRollingHorizonSimulation()
            self.HeuristicSolvers = [None for instance in self.SubInstance]
            if Constants.Debug:
                print "define the second set of MIP for solving 2 stage as warm start"

            savetreestructure = copy.deepcopy(self.Treestructure)
            savemodel = self.Model
            savedheuristicyfix = self.Owner.YeuristicYfix
            self.Treestructure = [1] + [  500 ] + [1] *  ( self.WindowSize  + 1)
            self.Model = Constants.ModelYQFix
            self.Owner.YeuristicYfix = False
            self.RollingHorizonMIPWarmStarts = self.DefineMIPsRollingHorizonSimulation()
            self.Owner.YeuristicYfix =  savedheuristicyfix
            self.Treestructure = savetreestructure
            self.Model = savemodel

        self.Solution = MRPSolution.GetEmptySolution( instance )


    #This function define a set of MIP, each MIP correspond to a slice of the horizon
    def DefineMIPsRollingHorizonSimulation(self):
        result = []


        # For each subinstance, Create a tree, and generate a MIP
        for instance in self.SubInstance:
            treestructure =  copy.deepcopy(self.Treestructure)
            if self.Model == Constants.ModelYFix:
                treestructure =  [1] * (instance.NrTimeBucketWithoutUncertaintyBefore+1)  + treestructure + [0]
            else:
                treestructure = treestructure[:-1] + [1] * instance.NrTimeBucketWithoutUncertaintyBefore + [0]

            if len( treestructure )> instance.NrTimeBucket + 2:
                treestructure = treestructure[:instance.NrTimeBucket + 1] + [0]
            scenariotree = ScenarioTree(instance=instance, branchperlevel=treestructure, seed = self.Seed,
                                        averagescenariotree=self.Owner.EvaluateAverage,
                                        scenariogenerationmethod=self.ScenarioGenerationResolvePolicy,
                                        model=self.Model)

            logfilename = "%s_%s_%r_%r_%r"%(instance.InstanceName, self.Model, len(result), scenariotree.TreeStructure, self.UseSafetyStock)

            givensetups = []

            if self.Owner.YeuristicYfix:
                givensetups = [ [ 1 for p in self.GlobalInstance.ProductSet ] for t in self.GlobalInstance.TimeBucketSet ]

            mipsolver = MIPSolver(instance, self.Model, scenariotree,
                                  False,
                                  implicitnonanticipativity = True,
                                  evaluatesolution = False,
                                  usesafetystock = self.UseSafetyStock,
                                  rollinghorizon = True,
                                  logfile = logfilename,
                                  yfixheuristic = self.Owner.YeuristicYfix,
                                  usesafetystockgrave =  self.Owner.UseSafetyStockGrave,
                                  givensetups = givensetups)
            mipsolver.BuildModel()
            result.append( mipsolver )


        return result


    # Create the set of subinstance to solve in a rolling horizon approach
    def CreateSubInstances( self ):
            """ :type result: [ {MRPInstance} ]"""
            nrshift = self.GlobalInstance.NrTimeBucket  - self.GlobalInstance.NrTimeBucketWithoutUncertaintyBefore


            result = [None for i in range(nrshift)]

            startwindow = -1
            previousnrperiodwithoutuncertaintybefore = 0
            for i in range(nrshift):
                startwindow += 1 + previousnrperiodwithoutuncertaintybefore
                nrperiodwithoutuncertaintybefore = max(0, self.GlobalInstance.NrTimeBucketWithoutUncertaintyBefore - startwindow)
                endwindow = startwindow + self.WindowSize + nrperiodwithoutuncertaintybefore

                result[i] = copy.deepcopy(self.GlobalInstance)
                result[i].NrTimeBucket = min(self.WindowSize + nrperiodwithoutuncertaintybefore, self.GlobalInstance.NrTimeBucket-startwindow)
                actualend = startwindow + result[i].NrTimeBucket
                result[i].ForecastedAverageDemand = [self.GlobalInstance.ForecastedAverageDemand[startwindow + t]
                                                     for t in range(result[i].NrTimeBucket)]
                result[i].ForcastedStandardDeviation = [self.GlobalInstance.ForcastedStandardDeviation[startwindow + t]
                                                        for t in range(result[i].NrTimeBucket) ]
                result[i].NrTimeBucketWithoutUncertaintyBefore = max(0,
                                                                     self.GlobalInstance.NrTimeBucketWithoutUncertaintyBefore - startwindow)

                result[i].MaximumQuanityatT = [self.GlobalInstance.MaximumQuanityatT[startwindow + t]
                                                     for t in range(result[i].NrTimeBucket)]

                result[i].ComputeIndices()

                result[i].ActualEndOfHorizon = actualend == self.GlobalInstance.NrTimeBucket

                previousnrperiodwithoutuncertaintybefore = nrperiodwithoutuncertaintybefore

            return result

    #This function simulate the use of the stochastic optimization approach for given scenario
    def ApplyRollingHorizonSimulation(self, scenario):
        self.Solution = MRPSolution.GetEmptySolution( self.GlobalInstance)

        lastInventory = [ 0 for p in self.GlobalInstance.ProductSet]

        timetodecide = 0
        decisionstage = 0
        for instance in self.SubInstance:


            if Constants.Debug:
                print " Solve instance with time window [ %r, %r]"%( timetodecide, timetodecide + self.WindowSize )

            timedemandknownuntil = timetodecide - 1

            startinginventory = self.GetStartInventoryPlusQuantityOnOrder(timetodecide ,   scenario)

            mip = None
            wronginventory = False
            for  p in self.GlobalInstance.ProductSet:
                if ( not self.GlobalInstance.HasExternalDemand[p] ) \
                        and ( lastInventory[p]  < startinginventory[0][p] - 0.01 or lastInventory[p]  > startinginventory[0][p] +0.01  ) \
                        and not Constants.PrintOnlyFirstStageDecision:
                     wronginventory =  True

                if wronginventory:
                    print startinginventory
                    print lastInventory
                    raise NameError( "Inventory computation is wrong for product %s, real: %s computed: %s" %(p, lastInventory[p], startinginventory[p] ) )

            if Constants.IsRule( self.Model ):
                #update the starting Inventory in the instance
                for p in instance.ProductSet:
                    instance.StartingInventories[p] = startinginventory[0][p]
                    for t in range (instance.NrTimeBucket ):
                        if  t==0 or t  >= self.GlobalInstance.Leadtimes[p] -1  :
                            instance.Delivery[t][p] = 0
                        else:

                            instance.Delivery[t][p] = startinginventory[t][p] - startinginventory[t-1][p]

                solution = self.HeuristicSolvers[decisionstage].SolveWithSimpleRule( self.Model)

            else:
                if self.Owner.YeuristicYfix:
                    mipwarmstart = self.RollingHorizonMIPWarmStarts[decisionstage]
                    mipwarmstart.UpdateStartingInventory(startinginventory)
                    mipwarmstart.ModifyBigMForScenario( startinginventory[0])
                    #mipwarmstart.Cplex.write("lpfile.lp")
                    solutionwarmstart = mipwarmstart.Solve( False )

                    array = [mipwarmstart.GetIndexProductionVariable(p, t, 0) for p in instance.ProductSet for t in
                             instance.TimeBucketSet]
                    values = mipwarmstart.Cplex.solution.get_values(array)
                    mip = self.RollingHorizonMIPs[decisionstage]
                    mip.GivenSetup = [[values[p * (len(instance.TimeBucketSet)) + t]
                                       for p in instance.ProductSet] for t in instance.TimeBucketSet]

                mip = self.RollingHorizonMIPs[decisionstage]
                # Update the starting inventory, and the known Y values

                mip.UpdateStartingInventory(startinginventory)




                if self.Owner.YeuristicYfix:
                    mip.UpdateSetup(mip.GivenSetup)
                    mip.ModifyMIPForSetup(mip.GivenSetup)
                else:
                    if self.Model == Constants.ModelYFix:
                        mip.WarmStartGivenSetupConstraints()
                    mip.ModifyBigMForScenario(startinginventory[0])
                # Solve the MIP
                #mip.Cplex.write("lpfile%s.lp"%decisionstage)
                #print "solve the problem:"
                solution = mip.Solve( False )
                #print solution.Production
            # Save the relevant values
            self.CopyFirstStageDecision( solution,  timetodecide, instance, mip )

            timetodecide += 1 + instance.NrTimeBucketWithoutUncertaintyBefore
            decisionstage += 1
            if timetodecide < self.GlobalInstance.NrTimeBucket and not Constants.PrintOnlyFirstStageDecision:
                lastInventory =  [ solution.InventoryLevel[0][ mip.Instance.NrTimeBucketWithoutUncertaintyBefore+1][p]
                                   + mip.Scenarios[0].Demands[mip.Instance.NrTimeBucketWithoutUncertaintyBefore+1][p]
                                   + sum( solution.ProductionQuantity[0][mip.Instance.NrTimeBucketWithoutUncertaintyBefore+1][q]
                                          * self.GlobalInstance.Requirements[q][p]  for q in self.GlobalInstance.ProductSet)

                                   for p in self.GlobalInstance.ProductSet]


        if Constants.Debug:
            print "non rounded solution:"
            print self.Solution.ProductionQuantity

        quantity = [[  self.Solution.ProductionQuantity[0][t][p] for p in self.GlobalInstance.ProductSet] for t in self.GlobalInstance.TimeBucketSet]
        setups = [[ round(self.Solution.Production[0][t][p],0)  for p in self.GlobalInstance.ProductSet] for t in self.GlobalInstance.TimeBucketSet]


        return setups, quantity

    def GetStartInventoryPlusQuantityOnOrder(self, timetodecide ,   scenario):

        result = [ [ 0 for p in self.GlobalInstance.ProductSet ] for t in range(self.GlobalInstance.MaimumLeadTime) ]

        startinventory = self.GetEndingInventoryAt(timetodecide ,   scenario)

        for p in self.GlobalInstance.ProductSet:
            sumdelivery = 0
            for t in range(  self.GlobalInstance.MaimumLeadTime ):
                if t > 0  and t < self.GlobalInstance.Leadtimes[p]:
                    productiontime = timetodecide + t - self.GlobalInstance.Leadtimes[p]
                    sumdelivery += self.Solution.ProductionQuantity[0][productiontime][p]
                    result[t][p] =   sumdelivery
                if t == 0:
                    result[t][p] = startinventory[p]

        return result

        #This function return the ending inventory at time t
    def GetEndingInventoryAt(self, t,  scenario):
        prevquanity = [ [ self.Solution.ProductionQuantity[0][t1][p1]
                          for p1 in self.GlobalInstance.ProductSet ]
                        for t1 in self.GlobalInstance.TimeBucketSet ]
        prevdemand = [ [ scenario.Demands[t1][p1]
                         for p1 in self.GlobalInstance.ProductSet ]
                       for t1 in self.GlobalInstance.TimeBucketSet ]
        projectedbackorder, projininventory, echeoninv, Endininventory = self.Solution.GetCurrentStatus(prevdemand,
                                                                                                prevquanity,
                                                                                                t)
        #Remove starting inventory to not count it twice
        Endininventory = [ Endininventory[p] - self.GlobalInstance.StartingInventories[p] for p in self.GlobalInstance.ProductSet ]

        return Endininventory


    #This function save the frist stage decision in the solution of the MIP
    def CopyFirstStageDecision(self, solution, time, instance, mip ):

        if  instance.NrTimeBucketWithoutUncertaintyBefore  > 0:
            periodstocopy =  range(instance.NrTimeBucketWithoutUncertaintyBefore)  + [instance.NrTimeBucketWithoutUncertaintyBefore ]
        else:
            periodstocopy = [time]

        if Constants.IsRule(self.Model):
            for tau in periodstocopy:
                #Copy the Setup decision for the first day:
                for p in self.GlobalInstance.ProductSet:

                        self.Solution.Production[0][tau][p] = solution.Production[0][tau - time ][p]
                        self.Solution.ProductionQuantity[0][tau][p] = solution.ProductionQuantity[0][tau - time][p]
        else:
            array = [mip.GetIndexProductionVariable(p, tau - time, 0) for p in  self.GlobalInstance.ProductSet for tau in periodstocopy]
            productionvalues = mip.Cplex.solution.get_values(array)
            array = [mip.GetIndexQuantityVariable(p, tau - time, 0) for p in self.GlobalInstance.ProductSet for tau in periodstocopy]
            quantityvalues = mip.Cplex.solution.get_values(array)
            for tau in periodstocopy:
                # Copy the Setup decision for the first day:
                for p in self.GlobalInstance.ProductSet:
                    self.Solution.Production[0][tau][p] = productionvalues[(tau - time) + len( periodstocopy) * p]
                    if   self.Solution.Production[0][tau][p] == 0:
                        self.Solution.ProductionQuantity[0][tau][p] = 0
                    else:
                        self.Solution.ProductionQuantity[0][tau][p] = quantityvalues[(tau - time) + len( periodstocopy) * p]
