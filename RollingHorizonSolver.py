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
            self.Treestructure = [ 1, 500 ] + [1] *   self.WindowSize
            self.Model = Constants.ModelYQFix
            self.RollingHorizonMIPWarmStarts = self.DefineMIPsRollingHorizonSimulation()
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
                result[i].ForecastedAverageDemand = [self.GlobalInstance.ForecastedAverageDemand[startwindow + t]
                                                     for t in range(result[i].NrTimeBucket)]
                result[i].ForcastedStandardDeviation = [self.GlobalInstance.ForcastedStandardDeviation[startwindow + t]
                                                        for t in range(result[i].NrTimeBucket) ]
                result[i].NrTimeBucketWithoutUncertaintyBefore = max(0,
                                                                     self.GlobalInstance.NrTimeBucketWithoutUncertaintyBefore - startwindow)
                result[i].ComputeIndices()

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

            startinginventory = self.GetEndingInventoryAt(timetodecide ,   scenario)
            mip = None
            wronginventory = False
            for  p in self.GlobalInstance.ProductSet:
                if ( not self.GlobalInstance.HasExternalDemand[p] ) \
                        and ( lastInventory[p]  < startinginventory[p] - 0.01 or lastInventory[p]  > startinginventory[p] +0.01  ) \
                        and not Constants.PrintOnlyFirstStageDecision:
                     wronginventory =  True

                if wronginventory:
                    print startinginventory
                    print lastInventory
                    raise NameError( "Inventory computation is wrong for product %s, real: %s computed: %s" %(p, lastInventory[p], startinginventory[p] ) )

            if Constants.IsRule( self.Model ):
                #update the starting Inventory in the instance
                for p in instance.ProductSet:
                    instance.StartingInventories[p] = startinginventory[p]

                solution = self.HeuristicSolvers[decisionstage].SolveWithSimpleRule( self.Model)

            else:
                mipwarmstart = self.RollingHorizonMIPWarmStarts[decisionstage]
                mipwarmstart.UpdateStartingInventory(startinginventory)
                solutionwarmstart = mipwarmstart.Solve( False )

                mip = self.RollingHorizonMIPs[decisionstage]
                # Update the starting inventory, and the known Y values
                mip.UpdateStartingInventory(startinginventory)
                array = [mipwarmstart.GetIndexProductionVariable(p, t, 0) for p in instance.ProductSet for t in instance.TimeBucketSet ]
                values= mipwarmstart.Cplex.solution.get_values(array)

                mip.GivenSetup = [[values[p * (len(instance.TimeBucketSet) ) + t  ]
                                     for p in instance.ProductSet] for t in instance.TimeBucketSet]

                if self.Model == Constants.ModelYFix:
                    mip.WarmStartGivenSetupConstraints
                else:
                    mip.UpdateSetup(mip.GivenSetup)
                # Solve the MIP
                solution = mip.Solve( False )

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





    #This function return the ending inventory at time t
    def GetEndingInventoryAt(self, t,  scenario):
        prevquanity = [ [ self.Solution.ProductionQuantity[0][t1][p1]
                          for p1 in self.GlobalInstance.ProductSet ]
                        for t1 in self.GlobalInstance.TimeBucketSet ]
        prevdemand = [ [ scenario.Demands[t1][p1]
                         for p1 in self.GlobalInstance.ProductSet ]
                       for t1 in self.GlobalInstance.TimeBucketSet ]
        projectedbackorder, projininventory, Endininventory = self.Solution.GetCurrentStatus(prevdemand,
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
                    self.Solution.ProductionQuantity[0][tau][p] = quantityvalues[(tau - time) + len( periodstocopy) * p]
