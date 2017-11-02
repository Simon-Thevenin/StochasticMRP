import cplex
import pandas as pd
from MRPSolution import MRPSolution
import time
import numpy as np
import math
from Constants import Constants
from Tool import Tool
from ScenarioTreeNode import ScenarioTreeNode
from DecentralizedMRP import DecentralizedMRP
import itertools
class MIPSolver(object):
    M = cplex.infinity

    # constructor

    def __init__(self,
                 instance,
                 model,
                 scenariotree,
                 evpi = False,
                 implicitnonanticipativity = False,
                 givenquantities = [],
                 givensetups=[],
                 fixsolutionuntil = -1,
                 evaluatesolution = False,
                 yfixheuristic = False,
                 demandknownuntil = -1,
                 mipsetting = "",
                 warmstart = False,
                 usesafetystock = False,
                 maxquantities = [],
                 minsetup = []):

        # Define some attributes and functions which help to et the index of the variable.
        # the attributs nrquantiyvariables, nrinventoryvariable, nrproductionvariable, and nrbackordervariable gives the number
        # of variable of each type
        self.NrQuantiyVariables = 0
        self.NrInventoryVariable = 0
        self.NrProductionVariable = 0
        self.NrBackorderVariable = 0
        # The variable startquantityvariable, startinventoryvariable, startprodustionvariable, and startbackordervariable gives
        # the index at which each variable type start
        self.StartQuantityVariable = 0
        self.StartInventoryVariable = 0
        self.StartProductionVariable = 0
        self.StartBackorderVariable = 0

        # The attribut below correspond to the index of the variable when the non atticiaptivity constraint
        #  are not added and the noon requireed variables are not added
        self.NrQuantiyVariablesWithoutNonAnticipativity = 0
        self.NrInventoryVariableWithoutNonAnticipativity = 0
        self.NrProductionVariableWithoutNonAnticipativity = 0
        self.NrBackorderVariableWithoutNonAnticipativity = 0
        self.StartQuantityVariableWithoutNonAnticipativity = 0
        self.StartInventoryVariableWithoutNonAnticipativity = 0
        self.StartProductionVariableWithoutNonAnticipativity = 0
        self.StartBackorderVariableWithoutNonAnticipativity = 0

        self.Instance = instance
        #Takes value in _Fix, Y_Fix, YQFix
        self.Model = model
        #self.UseNonAnticipativity = usenonaticipativity
        #If non anticipativity constraints are added, they can be implicit or explicit.
        self.UseImplicitNonAnticipativity = implicitnonanticipativity
        #self.UseNonAnticipativity
        self.EVPI = evpi
        self.MipSetting = mipsetting
        #The set of scenarios used to solve the instance
        self.DemandScenarioTree = scenariotree
        self.DemandScenarioTree.Owner = self
        self.NrScenario = len( [ n for n in self.DemandScenarioTree.Nodes if len( n.Branches ) == 0 ] )
        # DemandKnownUntil is used fgor the YQFix model, when the first period are considered known.
        self.DemandKnownUntil = demandknownuntil
        self.YFixHeuristic= yfixheuristic
        self.UseSafetyStock = usesafetystock
        self.ComputeIndices()
        self.Scenarios =  scenariotree.GetAllScenarios( True )

        self.GivenQuantity = givenquantities

        self.GivenSetup = givensetups
        self.FixSolutionUntil =  fixsolutionuntil
        self.WamStart = warmstart

        self.ScenarioSet = range( self.NrScenario )
        self.Cplex = cplex.Cplex()

        self.EvaluateSolution = evaluatesolution

        #This list is filled after the resolution of the MIP
        self.SolveInfo = []

        #This list will contain the set of constraint number for each flow constraint
        self.FlowConstraintNR = []

        self.QuantityConstraintNR = []

        self.MaxQuantities = maxquantities
        self.MinSetup = minsetup

        if len(self.MaxQuantities) == 0:
            self.MaxQuantities = [1000000000 for p in self.Instance.ProductSet]

            # Compute the start of index and the number of variables for the considered instance
    def ComputeIndices( self ):

            scenariotimeproduct = self.Instance.NrProduct * self.Instance.NrTimeBucket * self.NrScenario
            self.NrQuantiyVariables = scenariotimeproduct
            d = max( self.DemandKnownUntil, 0)
            self.NrInventoryVariable = scenariotimeproduct -  d * self.Instance.NrProduct * ( self.NrScenario -1 )
            self.NrProductionVariable = scenariotimeproduct
            self.NrBackorderVariable = len( self.Instance.ProductWithExternalDemand ) * self.Instance.NrTimeBucket * self.NrScenario - self.DemandKnownUntil * len( self.Instance.ProductWithExternalDemand ) * ( self.NrScenario -1 )
            self.StartQuantityVariable = 0
            self.StartInventoryVariable = self.StartQuantityVariable + self.NrQuantiyVariables
            self.StartProdustionVariable = self.StartInventoryVariable + self.NrInventoryVariable
            self.StartBackorderVariable = self.StartProdustionVariable + self.NrProductionVariable

            # The indices of the variable in the case where the non anticipativity constraints are created explicitely
            #Quantity variable are define from the first node to the penultimate
            self.NrQuantiyVariablesWithoutNonAnticipativity =  self.Instance.NrProduct * ( self.DemandScenarioTree.NrNode - 1  - self.NrScenario )
            # There is no decision regarding inventories at node 1
            nodeproductafterfirstperiod = self.Instance.NrProduct * ( self.DemandScenarioTree.NrNode - 2 )
            self.NrInventoryVariableWithoutNonAnticipativity = nodeproductafterfirstperiod
            self.NrProductionVariableWithoutNonAnticipativity =  self.Instance.NrProduct * ( self.DemandScenarioTree.NrNode - 1  - self.NrScenario )
            #In the case where the YQ model is used, reduce the number of production variable
            if self.Model == Constants.ModelYFix or self.Model == Constants.ModelYQFix :
                self.NrProductionVariableWithoutNonAnticipativity = self.Instance.NrProduct * self.Instance.NrTimeBucket

            if self.Model == Constants.ModelYQFix :
                self.NrQuantiyVariablesWithoutNonAnticipativity = self.Instance.NrProduct * self.Instance.NrTimeBucket

            self.NrBackorderVariableWithoutNonAnticipativity = len( self.Instance.ProductWithExternalDemand ) * ( self.DemandScenarioTree.NrNode - 2)
            self.StartQuantityVariableWithoutNonAnticipativity = 0
            self.StartInventoryVariableWithoutNonAnticipativity = self.StartQuantityVariableWithoutNonAnticipativity + self.NrQuantiyVariablesWithoutNonAnticipativity
            self.StartProductionVariableWithoutNonAnticipativity = self.StartInventoryVariableWithoutNonAnticipativity + self.NrInventoryVariableWithoutNonAnticipativity
            self.StartBackorderVariableWithoutNonAnticipativity = self.StartProductionVariableWithoutNonAnticipativity + self.NrProductionVariableWithoutNonAnticipativity

            # The indices of the variable in the case where a the model with YQ are decided at stage 0 is solved
            producttime = self.Instance.NrProduct * self.Instance.NrTimeBucket
            self.NrQuantiyVariablesYQFix = producttime
            self.NrProductionVariablesYQFix = producttime
            self.StartQuantityVariablYQFix = 0
            self.StartInventoryVariableYQFix = self.StartQuantityVariablYQFix + self.NrQuantiyVariablesYQFix
            self.StartProdustionVariableYQFix = self.StartInventoryVariableYQFix + self.NrInventoryVariable

            self.StartBackorderVariableYQFix = self.StartProdustionVariableYQFix + self.NrProductionVariablesYQFix

            # The indices of the variable in the case where a one stage problem is solved
            self.NrProductionVariablesYFix = producttime
            self.StartQuantityVariablYFix = 0

            self.StartInventoryVariableYFix = self.StartQuantityVariablYQFix + self.NrQuantiyVariables
            self.StartProdustionVariableYFix = self.StartInventoryVariableYFix + self.NrInventoryVariable
            if self.UseImplicitNonAnticipativity:
                self.StartProdustionVariableYFix =  self.StartProductionVariableWithoutNonAnticipativity
            self.StartBackorderVariableYFix = self.StartProdustionVariableYFix + self.NrProductionVariablesYFix

    # This function returns the name of the quantity variable for product p and time t
    def GetNameQuantityVariable(self, p, t, w):
        scenarioindex = -1

        if  not self.UseImplicitNonAnticipativity:
            scenarioindex = w
        elif self.Model == Constants.ModelYQFix:
            scenarioindex = 0
        else:
            scenarioindex = self.Scenarios[w].QuanitityVariable[t][p]

        return "q_p_t_s_%d_%d_%d" % (p, t, scenarioindex)

    # This function returns the name of the inventory variable for product p and time t
    def GetNameInventoryVariable(self, p, t, w):
        scenarioindex = -1;

        if not self.UseImplicitNonAnticipativity:
            scenarioindex = w
        else:
            scenarioindex = self.Scenarios[w].InventoryVariable[t][p]

        return "i_%d_%d_%d" % (p, t, scenarioindex)

    # This function returns the name of the production variable for product p and time t
    def GetNameProductionVariable( self, p, t, w ):
        scenarioindex = -1;
        if  not  self.UseImplicitNonAnticipativity:
            scenarioindex = w
        elif self.Model == Constants.ModelYQFix or self.Model == Constants.ModelYFix:
                scenarioindex = 0
        else:
            scenarioindex = self.Scenarios[w].ProductionVariable[t][p]

        return "p_%d_%d_%d" % (p, t, scenarioindex)

    # This function returns the name of the backorder variable for product p and time t
    def GetNameBackOrderQuantity(self, p, t, w):
        scenarioindex = -1;
        if not  self.UseImplicitNonAnticipativity:
            scenarioindex = w
        else:
            scenarioindex = self.Scenarios[w].BackOrderVariable[t][self.Instance.ProductWithExternalDemandIndex[p]]

        return "b_%d_%d_%d" % (p, t, scenarioindex)

    # the function GetIndexQuantityVariable returns the index of the variable Q_{p, t}. Quantity of product p produced at time t
    def GetIndexQuantityVariable( self, p, t, w ):

        if  not  self.UseImplicitNonAnticipativity:
            return self.GetStartQuantityVariable() + w * (self.Instance.NrTimeBucket) * self.Instance.NrProduct + t * self.Instance.NrProduct + p
        elif self.Model == Constants.ModelYQFix:
            return self.GetStartQuantityVariable() + t * self.Instance.NrProduct + p
        else:
            return self.Scenarios[w].QuanitityVariable[t][p];

    # the function GetIndexInventoryVariable returns the index of the variable I_{p, t}. Inventory of product p produced at time t
    def GetIndexInventoryVariable( self, p, t, w ):
        if  not  self.UseImplicitNonAnticipativity:
            return self.GetStartInventoryVariable() + w * self.Instance.NrTimeBucket * self.Instance.NrProduct + t * self.Instance.NrProduct + p
        else:
            return self.Scenarios[w].InventoryVariable[t][p];

    # the function GetIndexProductionVariable returns the index of the variable Y_{p, t, w}.
    # This variable equal to one is product p is produced at time t, 0 otherwise
    def GetIndexProductionVariable( self, p, t, w ):
        if  not  self.UseImplicitNonAnticipativity:
            return self.GetStartProductionVariable() + w * self.Instance.NrTimeBucket * self.Instance.NrProduct + t * self.Instance.NrProduct + p
        elif self.Model == Constants.ModelYQFix or self.Model == Constants.ModelYFix:
            return self.GetStartProductionVariable() + t * self.Instance.NrProduct + p
        else:
            return self.Scenarios[w].ProductionVariable[t][p];

    # the function GetIndexBackorderVariable returns the index of the variable B_{p, t}. Quantity of product p produced backordered at time t
    def GetIndexBackorderVariable( self, p, t, w ):
        if not  self.UseImplicitNonAnticipativity:
            return self.GetStartBackorderVariable() \
                   + w * self.Instance.NrTimeBucket * len( self.Instance.ProductWithExternalDemand )  \
                   + t * len( self.Instance.ProductWithExternalDemand ) + self.Instance.ProductWithExternalDemandIndex[p]
        else:
            return self.Scenarios[w].BackOrderVariable[t][self.Instance.ProductWithExternalDemandIndex[p]];

            # the function GetIndexBackorderVariable returns the index of the variable B_{p, t}. Quantity of product p produced backordered at time t

    #def GetIndexTotalCost(self):
    #    if not self.UseImplicitNonAnticipativity: return self.StartBackorderVariable + self.NrBackorderVariableWithoutNonAnticipativity
    #    if self.Model == Constants.ModelYQFix: return self.StartBackorderVariableYQFix + self.NrBackorderVariableWithoutNonAnticipativity
    #    if self.Model == Constants.ModelYFix: return self.StartBackorderVariableYFix + self.NrBackorderVariableWithoutNonAnticipativity
    #    if self.Model == Constants.Model_Fix: return self.StartBackorderVariable + self.NrBackorderVariableWithoutNonAnticipativity

    def GetIndexKnownDemand(self, p):
        return self.GetStartKnownDemand() + self.Instance.ProductWithExternalDemandIndex.index(p)

    def GetStartKnownDemand(self):
        if not self.UseImplicitNonAnticipativity: return self.StartBackorderVariable + self.NrBackorderVariableWithoutNonAnticipativity
        if self.Model == Constants.ModelYQFix: return self.StartBackorderVariableWithoutNonAnticipativity + self.NrBackorderVariableWithoutNonAnticipativity
        if self.Model == Constants.ModelYFix: return self.StartBackorderVariableYFix + self.NrBackorderVariableWithoutNonAnticipativity
        if self.Model == Constants.Model_Fix: return self.StartBackorderVariable + self.NrBackorderVariableWithoutNonAnticipativity

    #return the index at which the backorder variables starts
    def GetStartBackorderVariable( self ):
        if not self.UseImplicitNonAnticipativity:return self.StartBackorderVariable
        if self.Model == Constants.ModelYQFix: return self.StartBackorderVariableYQFix
        if self.Model == Constants.ModelYFix: return self.StartBackorderVariableYFix
        if self.Model == Constants.Model_Fix: return self.StartBackorderVariable

    #return the index at which the production variables starts
    def GetStartProductionVariable( self ):
        if not self.UseImplicitNonAnticipativity:return self.StartProdustionVariable
        if self.Model == Constants.ModelYQFix: return self.StartProdustionVariableYQFix
        if self.Model == Constants.ModelYFix: return self.StartProdustionVariableYFix
        if self.Model == Constants.Model_Fix: return self.StartProdustionVariable

    #retunr the index at which the inventory variables starts
    def GetStartInventoryVariable( self ):
        if not self.UseImplicitNonAnticipativity:return self.StartInventoryVariable
        if self.Model == Constants.ModelYQFix: return self.StartInventoryVariableYQFix
        if self.Model == Constants.ModelYFix: return self.StartInventoryVariableWithoutNonAnticipativity
        if self.Model == Constants.Model_Fix: return self.StartInventoryVariable

    #return the index at which the quantity variable starts
    def GetStartQuantityVariable( self ):
        if self.Model == Constants.ModelYQFix: return self.StartQuantityVariablYQFix
        if self.Model == Constants.ModelYFix: return self.StartQuantityVariablYFix
        if self.Model == Constants.Model_Fix: return self.StartQuantityVariable

    #return the number of quantity variables
    def GetNrQuantityVariable( self ):
        if self.Model == Constants.ModelYQFix and  self.UseImplicitNonAnticipativity:
            return self.NrQuantiyVariablesYQFix
        else:
            return self.NrQuantiyVariables

    #return the number of production variables
    def GetNrProductionVariable( self ):
        if not self.UseImplicitNonAnticipativity:return self.NrProductionVariable
        if self.Model == Constants.ModelYQFix: return self.NrProductionVariablesYQFix
        if self.Model == Constants.ModelYFix: return self.NrProductionVariablesYFix
        if self.Model == Constants.Model_Fix: return self.NrProductionVariable

        # return the number of quantity variables

    def GetNrInventoryVariable(self):
        if self.Model == Constants.ModelYQFix and self.UseImplicitNonAnticipativity:
            return self.NrInventoryVariable
        else:
            return self.NrInventoryVariableWithoutNonAnticipativity

    # This function define the variables
    def CreateVariable( self ):
        # Define the cost vector for each variable. As the numbber of variable changes when non anticipativity is used the cost are created differently
        if  not  self.UseImplicitNonAnticipativity:
            inventorycosts = [ self.Instance.InventoryCosts[p]
                               * self.Scenarios[w].Probability
                               * math.pow( self.Instance.Gamma, t)
                              for w in self.ScenarioSet
                                 for t in self.Instance.TimeBucketSet
                                    for p in self.Instance.ProductSet ]

            setupcosts = [ self.Instance.SetupCosts[p]
                           * self.Scenarios[w].Probability
                           * math.pow(self.Instance.Gamma, t)
                          for w in self.ScenarioSet
                           for t in self.Instance.TimeBucketSet
                           for p in self.Instance.ProductSet]

            backordercosts = [self.Instance.BackorderCosts[p]
                              * self.Scenarios[w].Probability
                              * math.pow(self.Instance.Gamma, t)
                              if t < self.Instance.NrTimeBucket -1
                              else
                              self.Instance.LostSaleCost[p]
                              * self.Scenarios[w].Probability
                              * math.pow(self.Instance.Gamma, t)
                              for w in self.ScenarioSet
                                for t in self.Instance.TimeBucketSet
                                   for p in self.Instance.ProductWithExternalDemand]


            nrinventoryvariable = self.NrInventoryVariable;
            nrbackordervariable = self.NrBackorderVariable;
            nrproductionvariable = self.NrProductionVariable;
            nrquantityvariable = self.NrQuantiyVariables;


        # Define only the required variables
        else:
            nrquantityvariable = self.NrQuantiyVariablesWithoutNonAnticipativity
            nrinventoryvariable = self.NrInventoryVariableWithoutNonAnticipativity
            nrbackordervariable = self.NrBackorderVariableWithoutNonAnticipativity
            nrproductionvariable = self.NrProductionVariableWithoutNonAnticipativity
            inventorycosts = [0] * nrinventoryvariable
            setupcosts = [0] * nrproductionvariable
            backordercosts = [0] * nrbackordervariable
            for w in self.ScenarioSet:
                for t in self.Instance.TimeBucketSet:
                    for p in self.Instance.ProductSet:
                        # Add the cost of the cariable representing multiple scenarios
                        inventorycostindex = self.Scenarios[w].InventoryVariable[t][p] - self.StartInventoryVariableWithoutNonAnticipativity
                        inventorycosts[inventorycostindex] = inventorycosts[inventorycostindex] \
                                                             + self.Instance.InventoryCosts[p] * self.Scenarios[w].Probability * np.power( self.Instance.Gamma, t )

                        if self.Model <> Constants.ModelYFix and self.Model <> Constants.ModelYQFix :
                            setupcostindex = self.Scenarios[w].ProductionVariable[t][
                                                 p] - self.StartProductionVariableWithoutNonAnticipativity

                            setupcosts[setupcostindex] = setupcosts[setupcostindex] \
                                                         + self.Instance.SetupCosts[p] \
                                                           * self.Scenarios[w].Probability \
                                                           * np.power(self.Instance.Gamma, t)

                        if self.Instance.HasExternalDemand[p]:
                            backordercostindex = self.Scenarios[w].BackOrderVariable[t][
                                                     self.Instance.ProductWithExternalDemandIndex[p] ] - self.StartBackorderVariableWithoutNonAnticipativity
                            if t < self.Instance.NrTimeBucket -1 :
                                backordercosts[backordercostindex] = backordercosts[backordercostindex] \
                                                                     + self.Instance.BackorderCosts[p] \
                                                                       * self.Scenarios[w].Probability \
                                                                       * np.power(self.Instance.Gamma, t)
                            else: backordercosts[backordercostindex] = backordercosts[backordercostindex] \
                                                                       + self.Instance.LostSaleCost[p] \
                                                                         * self.Scenarios[w].Probability \
                                                                         *np.power(self.Instance.Gamma, t)
                            #print backordercosts

            if self.Model == Constants.ModelYQFix:
                nrquantityvariable = self.NrQuantiyVariablesYQFix
                nrproductionvariable = self.NrProductionVariablesYQFix
            if self.Model == Constants.ModelYFix:
                nrproductionvariable = self.NrProductionVariablesYFix

            if self.Model == Constants.ModelYQFix or self.Model == Constants.ModelYFix:
                setupcosts = [ self.Instance.SetupCosts[p]
                               * sum( self.Scenarios[w].Probability for w in self.ScenarioSet)
                               * np.power(self.Instance.Gamma, t)
                              for t in self.Instance.TimeBucketSet for p in self.Instance.ProductSet ]

                        # the variable quantity_prod_time_scenario_p_t_w indicated the quantity of product p produced at time t in scneario w
        upperbound = [self.M] * nrquantityvariable
        if len( self.GivenSetup) > 0 and (self.EvaluateSolution or self.YFixHeuristic):
            for w in self.ScenarioSet:
                for t in self.Instance.TimeBucketSet:
                    for p in self.Instance.ProductSet:
                        upperbound[self.GetIndexQuantityVariable(p,t,w)] =  (self.GivenSetup[t][p]) * self.M

        self.Cplex.variables.add(obj=[0.0] * nrquantityvariable,
                                lb=[0.0] * nrquantityvariable,
                                ub= upperbound)

        # the variable inventory_prod_time_scenario_p_t_w indicated the inventory level of product p at time t in scneario w
        self.Cplex.variables.add(obj= inventorycosts,
                                 #obj=[0.0] * nrinventoryvariable,
                                lb=[0.0] * nrinventoryvariable,
                                ub=[self.M] * nrinventoryvariable)

        # the variable production_prod_time_scenario_p_t_w equals 1 if a lot of product p is produced at time t in scneario w
        if self.EvaluateSolution or self.YFixHeuristic:
            self.Cplex.variables.add(obj= setupcosts,
                                     #[0.0] * nrproductionvariable,
                                     lb=[0.0] * nrproductionvariable,
                                     ub=[1.0] * nrproductionvariable
                                     )
        else:
            self.Cplex.variables.add(obj=setupcosts,
                                     #[0.0] * nrproductionvariable,
                                     #lb=[0.0] * nrproductionvariable,
                                     #ub=[1.0] * nrproductionvariable,
                                     types= ['B']*nrproductionvariable
                                     )

        # the variable backorder_prod_time_scenario_p_t_w gives the amount of product p backordered at time t in scneario w
        self.Cplex.variables.add( obj=backordercosts, #
                                  #[0.0] * nrbackordervariable,
                                  lb=[0.0] * nrbackordervariable,
                                  ub=[self.M] * nrbackordervariable)

        #Add a variable which represents the known demand:
        if self.DemandKnownUntil >= 0:
            nrknowndemand = len( self.Instance.ProductWithExternalDemand )
            value = [ sum( self.Scenarios[0].Demands[tau][p] for tau in range(self.DemandKnownUntil +1 ))  for p in self.Instance.ProductWithExternalDemand ]
            print "KnownDemandValue:%r - %r"%(value, self.DemandKnownUntil  )
            self.Cplex.variables.add(obj=[0.0] * nrknowndemand,
                                     lb=value,
                                     ub=value)

        # self.Cplex.variables.add(obj=[1.0],
        #                           lb=[0.0],
        #                           ub=[self.M] )
        #
        # self.Cplex.variables.add(obj=[1.0],
        #                          lb=[0.0],
        #                           ub=[self.M] )
        #
        # self.CreateTotalCostConstraint()

        # Define the variable name.
        # Usefull for debuging purpose. Otherwise, disable it, it is time consuming.
        if Constants.Debug:
            quantityvars = []
            inventoryvars = []
            productionvars = []
            backordervars = []
            for p in self.Instance.ProductSet:
                for t in self.Instance.TimeBucketSet:
                    for w in self.ScenarioSet:
                        quantityvars.append( ( (int)(self.GetIndexQuantityVariable(p, t, w)), self.GetNameQuantityVariable(p, t, w) ) )
                        productionvars.append( ( (int)(self.GetIndexProductionVariable(p, t, w)), self.GetNameProductionVariable(p, t, w) ) )
                        inventoryvars.append( ( (int)(self.GetIndexInventoryVariable(p, t, w) ), self.GetNameInventoryVariable(p, t, w) ) )
                        if self.Instance.HasExternalDemand[p] :
                            backordervars.append( ( (int)( self.GetIndexBackorderVariable(p, t, w) ), self.GetNameBackOrderQuantity(p, t, w) ) )

            quantityvars = list( set( quantityvars ) )
            productionvars = list( set( productionvars ) )
            inventoryvars = list( set( inventoryvars ) )
            backordervars = list( set( backordervars ) )
            varnames = quantityvars + inventoryvars + productionvars + backordervars
            self.Cplex.variables.set_names(varnames)

    # Print a constraint (usefull for debugging)
    def PrintConstraint( vars, coeff, righthandside):
        print "Add the following constraint:"
        print "----------------Var-----------------------------"
        print vars
        print "----------------Coeff-----------------------------"
        print coeff
        print "----------------Rhs-----------------------------"
        print righthandside

    # To evaluate the solution obtained with the expected demand, the solution quanitity are constraint to be equal to some values
    # This function creates the Capacity constraint
    def CreateCopyGivenQuantityConstraints( self ):
        AlreadyAdded = [ False for v in range( self.GetNrQuantityVariable() ) ]
        self.QuantityConstraintNR = [[["" for t in self.Instance.TimeBucketSet] for p in self.Instance.ProductSet] for w in
                                 self.ScenarioSet]

        # Capacity constraint
        for p in self.Instance.ProductSet:
            for t in self.Instance.TimeBucketSet:
                for w in self.ScenarioSet:
                    indexvariable = self.GetIndexQuantityVariable(p, t, w)
                    if not AlreadyAdded[indexvariable] \
                            and (t <= self.FixSolutionUntil):
                        vars = [indexvariable]
                        AlreadyAdded[indexvariable] = True
                        coeff = [1.0]
                        #righthandside =  [ float(  Decimal( "%r"%(self.GivenQuantity[t][p])  ).quantize(Decimal('0.0001'), rounding= ROUND_HALF_DOWN )  ) ]

                        righthandside = [ self.GivenQuantity[t][p] ]
                        #print "Value: %+18.16e" % self.GivenQuantity[t][p]
                        # PrintConstraint( vars, coeff, righthandside )
                        #righthandside[0] = righthandside[0]  + 0.1
                        #righthandside[0] = righthandside[0]
                        self.Cplex.linear_constraints.add( lin_expr=[cplex.SparsePair(vars, coeff)],
                                                           senses=["E"],
                                                           rhs=righthandside ,
                                                           names = ["LQuantitya%da%da%d"%(p,t,w)])
                        #righthandside[0] = righthandside[0]  - 0.1
                        #self.Cplex.linear_constraints.add( lin_expr=[cplex.SparsePair(vars, coeff)],
                        #                                   senses=["G"],
                        #                                   rhs=righthandside ,
                        #                                   names = ["GQuantitya%da%da%d"%(p,t,w)])
                        self.QuantityConstraintNR[w][p][t] = "Quantitya%da%da%d"%(p,t,w)

    def CreateCopyGivenSetupConstraints(self):
         AlreadyAdded = [False for v in range(self.GetNrProductionVariable())]
         # Setup equal to the given ones
         for p in self.Instance.ProductSet:
             for t in self.Instance.TimeBucketSet:
                 for w in self.ScenarioSet:
                      indexvariable = self.GetIndexProductionVariable(p, t, w)
                      indexinarray = indexvariable - self.GetStartProductionVariable()

                      if not AlreadyAdded[indexinarray]:
                            vars = [indexvariable]
                            AlreadyAdded[indexinarray] = True
                            coeff = [1.0]
                            righthandside = [round(self.GivenSetup[t][p], 2)]
                            # PrintConstraint( vars, coeff, righthandside )
                            self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                              senses=["E"],
                                                              rhs=righthandside)

    def WarmStartGivenSetupConstraints(self):
         AlreadyAdded = [False for v in range(self.GetNrProductionVariable())]
         vars=[]
         righthandside = []
         # Setup equal to the given ones
         for p in self.Instance.ProductSet:
              for t in self.Instance.TimeBucketSet:
                  for w in self.ScenarioSet:
                      indexvariable = self.GetIndexProductionVariable(p, t, w)
                      indexinarray = indexvariable - self.GetStartProductionVariable()

                      if not AlreadyAdded[indexinarray]:
                          vars = vars + [indexvariable]
                          AlreadyAdded[indexinarray] = True
                          righthandside = righthandside + [round(self.GivenSetup[t][p], 0)]
         self.Cplex.MIP_starts.add(cplex.SparsePair(vars, righthandside), self.Cplex.MIP_starts.effort_level.solve_fixed )


    # Demand and materials requirement: set the value of the invetory level and backorder quantity according to
    #  the quantities produced and the demand
    def CreateFlowConstraints( self ):
        if self.UseSafetyStock:
           decentralized = DecentralizedMRP( self.Instance )
           safetystock  = decentralized.ComputeSafetyStock()
           print safetystock


        self.FlowConstraintNR = [[[ "" for t in self.Instance.TimeBucketSet]  for p in self.Instance.ProductSet] for w in self.ScenarioSet]
        AlreadyAdded = [ False for w in range(self.GetNrInventoryVariable())  ]

        for p in self.Instance.ProductSet:
            for w in self.ScenarioSet:
                # To speed up the creation of the model, only the variable and coffectiant which were not in the previous constraints are added (See the model definition)
                righthandside = [ -1 * self.Instance.StartingInventories[p]]
                quantityvar = []
                quantityvarceoff = []
                dependentdemandvar = []
                dependentdemandvarcoeff = []
                for t in self.Instance.TimeBucketSet:
                    indexinventoryvar = self.GetIndexInventoryVariable(p, t, w) - self.GetStartInventoryVariable()
                    backordervar = []

                    if t == self.DemandKnownUntil -1:
                            #reset right hand side because the demand afterward is saved in a variable to accelerate the update of the MIP
                            righthandside[0] = 0
                    else:
                            righthandside[0] = righthandside[0] + self.Scenarios[w].Demands[t][p]


                    if self.UseSafetyStock:
                            righthandside[0] = righthandside[0] + safetystock[t][p]

                    if self.Instance.HasExternalDemand[p]:
                            backordervar = [self.GetIndexBackorderVariable(p, t, w)]

                    if t - self.Instance.Leadtimes[p] >= 0:
                            quantityvar = quantityvar + [ self.GetIndexQuantityVariable(p, t - self.Instance.Leadtimes[p], w)]
                            quantityvarceoff = quantityvarceoff + [1]

                    dependentdemandvar = dependentdemandvar + [ self.GetIndexQuantityVariable(q, t, w) for q in
                                                                    self.Instance.RequieredProduct[p] ]

                    dependentdemandvarcoeff = dependentdemandvarcoeff + [-1 * self.Instance.Requirements[q][p] for q in
                                                                             self.Instance.RequieredProduct[p] ]
                    inventoryvar = [ self.GetIndexInventoryVariable(p, t, w) ]

                    knondemand = []
                    knondemandcoeff = []
                    if self.DemandKnownUntil>=0 and t >= (self.DemandKnownUntil-1) and self.Instance.HasExternalDemand[p]:
                            knondemand = [self.GetIndexKnownDemand(p)]
                            knondemandcoeff = [-1]

                    vars = inventoryvar + backordervar + quantityvar + dependentdemandvar + knondemand
                    coeff = [-1] * len(inventoryvar) \
                                + [1] * len(backordervar) \
                                + quantityvarceoff \
                                + dependentdemandvarcoeff \
                                + knondemandcoeff

                    if len(vars) > 0:
                            if  not AlreadyAdded[indexinventoryvar]:
                                AlreadyAdded[indexinventoryvar] = True
                                self.Cplex.linear_constraints.add( lin_expr=[cplex.SparsePair(vars, coeff)],
                                                                       senses=["E"],
                                                                       rhs=righthandside,
                                                                       names = ["Flowa%da%da%d"%(p,t,w)])
                    self.FlowConstraintNR[w][p][t] = "Flowa%da%da%d"%(p,t,w)

                    # This function creates the  indicator constraint to se the production variable to 1 when a positive quantity is produce

    def CreateLSInequalities( self ):
        for p in self.Instance.ProductWithExternalDemand:
            for w in self.ScenarioSet:
                for l in range(self.Instance.Leadtimes[p] , self.Instance.NrTimeBucket):
                    for r in range(l+1):
                            #SSet = itertools.combinations( range(l+1), r)
                            S = range(r, l+1)
                            vars = [ self.GetIndexQuantityVariable(p, t - self.Instance.Leadtimes[p], w) for t in S ] \
                                    + [ self.GetIndexProductionVariable(p, t - self.Instance.Leadtimes[p], w) for t in S ] \
                                    + [ self.GetIndexInventoryVariable(p, l, w ) ]
                            coeff = [ 1 for t in S ] \
                                    + [ -  sum( self.Scenarios[w].Demands[tau][p] for tau in range( t,l +1 ) ) for t in S ] \
                                    + [ - 1 ]

                            self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                                          senses=["L"],
                                                                          rhs=[0])  #

    # This function creates the  indicator constraint to se the production variable to 1 when a positive quantity is produce
    def CreateProductionConstraints( self ):
        n = self.GetNrQuantityVariable()
        AlreadyAdded = [ [ False ] * n  for w in range( self.GetNrProductionVariable() ) ]

        BigM = [MIPSolver.GetBigMValue(self.Instance, self.Scenarios, p)  for p in self.Instance.ProductSet ]

        for t in self.Instance.TimeBucketSet:
            if t > self.FixSolutionUntil or not  self.EvaluateSolution:
                for p in self.Instance.ProductSet:
                    for w in self.ScenarioSet:
                        indexQ = self.GetIndexQuantityVariable(p, t, w)
                        indexP = self.GetIndexProductionVariable(p, t, w) - self.GetStartProductionVariable()
                        if not AlreadyAdded[indexP][indexQ]:
                            #AlreadyAdded[indexP][indexQ] = True
                            #ic_dict = {}
                            #ic_dict["lin_expr"] = cplex.SparsePair(ind=[indexQ],
                            #                                       val=[1.0])
                            #ic_dict["rhs"] = 0.0
                            #ic_dict["sense"] = "E"
                            #ic_dict["indvar"] = self.GetIndexProductionVariable(p, t, w)
                            #ic_dict["complemented"] = 1
                            #self.Cplex.indicator_constraints.add( **ic_dict )


                            vars = [indexQ, self.GetIndexProductionVariable(p, t, w) ]
                            AlreadyAdded[indexP][indexQ] = True
                            coeff = [ -1.0, BigM[p] ]
                            righthandside = [ 0.0 ]

                            self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                              senses=["G"],
                                                             rhs=righthandside)#

    # This function add the objective function as a variable
    def CreateTotalCostConstraint(self):

        nextvar= 0
        for productset in [ self.Instance.ProductWithExternalDemand, self.Instance.ProductWithoutExternalDemand ]:
            print productset
            vars = [self.GetIndexTotalCost() + nextvar]
            nextvar = nextvar +1
            coeff = [1]

            for p in productset:
                for t in self.Instance.TimeBucketSet:
                    vars = vars + [self.GetIndexProductionVariable(p, t, 0)]
                    coeff = coeff + [-1 *np.power(self.Instance.Gamma, t) * self.Instance.SetupCosts[p] ]

            indice = len(coeff)

            nrinventory =  len( productset ) * (self.DemandScenarioTree.NrNode - 2)
            nribackorder = self.NrBackorderVariableWithoutNonAnticipativity
            if nextvar == 2: #(components)
                nribackorder = 0
            indicecoeffiunventory = [-1 for w in range(self.NrInventoryVariableWithoutNonAnticipativity)]

            indicecoeffbackorders = [-1 for w in range(self.NrBackorderVariableWithoutNonAnticipativity)]

            coeff = coeff + [ 0 for i in range(nrinventory + nribackorder)  ]
            for p in productset:
                for t in self.Instance.TimeBucketSet:
                    for w in self.ScenarioSet:
                         multiplier = -1 * self.Scenarios[w].Probability * np.power(self.Instance.Gamma, t)

                         indexI =  self.GetIndexInventoryVariable(p, t, w) - self.StartInventoryVariableWithoutNonAnticipativity
                         if indicecoeffiunventory[indexI]  == -1:
                            vars = vars + [ self.GetIndexInventoryVariable(p, t, w)]
                            indicecoeffiunventory[ indexI ] = indice
                            indice = indice + 1
                         if self.Instance.HasExternalDemand[p]:
                             print "has backorder"
                             indexB =  self.GetIndexBackorderVariable(p, t, w) - self.StartBackorderVariableWithoutNonAnticipativity
                             if indicecoeffbackorders[indexB] == -1:
                                 vars = vars + [self.GetIndexBackorderVariable(p, t, w)]
                                 indicecoeffbackorders[indexB] = indice
                                 indice = indice + 1
                             if t == self.Instance.NrTimeBucket -1:
                                 coeff[indicecoeffbackorders[indexB]] = coeff[indicecoeffbackorders[indexB]] + multiplier * \
                                                                                                               self.Instance.LostSaleCost[
                                                                                                                   p]
                             else:
                                coeff[indicecoeffbackorders[indexB]] = coeff[indicecoeffbackorders[indexB]] + multiplier * \
                                                                                                       self.Instance.BackorderCosts[
                                                                                                           p]

                         coeff[indicecoeffiunventory[indexI]] = coeff[indicecoeffiunventory[indexI]] + multiplier * self.Instance.InventoryCosts[p]


            righthandside = [0]
            print coeff
            self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                           senses=["E"],
                                                           rhs=righthandside)

        vars = [self.GetIndexTotalCost()]
        coeff = [1]
        righthandside = [0]
        for p in self.Instance.ProductWithExternalDemand:
             for t in self.Instance.TimeBucketSet:
                    if t + self.Instance.Leadtimes[p] < self.Instance.NrTimeBucket:
                        demand = np.power(self.Instance.Gamma, t + self.Instance.Leadtimes[p] -1)  \
                                * self.Instance.InventoryCosts[p] \
                                * sum( self.Scenarios[w].Demands[t + self.Instance.Leadtimes[p] ][p]  * self.Scenarios[w].Probability
                                      for w in self.ScenarioSet )
                    else: demand=0
                    vars = vars + [  self.GetIndexProductionVariable(p, t , 0)]
                    coeficient = - np.power(self.Instance.Gamma, t) * self.Instance.SetupCosts[p]
                    for w in self.ScenarioSet:
                        if t + self.Instance.Leadtimes[p] < self.Instance.NrTimeBucket:
                            coeficient = coeficient + demand
                    coeff = coeff + [   (coeficient )   ]
                    righthandside[0] = righthandside[0] + demand

        self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                           senses=["G"],
                                           rhs=righthandside)



    # This function creates the Capacity constraint
    def CreateCapacityConstraints( self ):
        AlreadyAdded = [False for v in range(self.GetNrQuantityVariable())  ]

        secenarioset = [0]
        if self.Model <> Constants.ModelYQFix :
            secenarioset = self.ScenarioSet
        # Capacity constraint
        if self.Instance.NrResource > 0:
            for k in range( self.Instance.NrResource ):
                AlreadyAdded = [False for v in range(self.GetNrQuantityVariable())]

                for t in self.Instance.TimeBucketSet:
                    for w in secenarioset:
                        indexQ = self.GetIndexQuantityVariable(0, t, w)
                        if not AlreadyAdded[indexQ]:
                            AlreadyAdded[indexQ] = True
                            vars = [ self.GetIndexQuantityVariable(p, t, w) for p in self.Instance.ProductSet ]
                            coeff = [ self.Instance.ProcessingTime[p][k] for p in self.Instance.ProductSet ]
                            righthandside = [ self.Instance.Capacity[k] ]
                            self.Cplex.linear_constraints.add( lin_expr=[cplex.SparsePair(vars, coeff)],
                                                               senses=["L"],
                                                               rhs=righthandside )



#                        self.CreateSafetyStockConstraints()
                        # This function creates the Capacity constraint

    # def CreateSafetyStockConstraints(self):
    #      AlreadyAdded = [False for v in range(self.GetNrQuantityVariable())]
    #      for p in self.Instance.ProductWithExternalDemand:
    #         for t in self.Instance.TimeBucketSet:
    #             for w in self.ScenarioSet:
    #                 indexI = self.GetIndexInventoryVariable(p, t, w)
    #                 #if not AlreadyAdded[indexI]:
    #                    # AlreadyAdded[indexI] = True
    #                 vars = [indexI ]
    #                 coeff = [ 1.0 ]
    #                 righthandside = [ ScenarioTreeNode.TransformInverse([[0.99]],
    #                                                                    1,
    #                                                                    1,
    #                                                                    self.Instance.Distribution,
    #                                                                    [self.Instance.ForecastedAverageDemand[t][p]],
    #                                                                    [self.Instance.ForcastedStandardDeviation[t][p]] )[0][0] ]
    #                 self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff) ],
    #                                                                           senses=["G"],
    #                                                                           rhs=righthandside)

    # This function creates the non anticipitativity constraint
    def CreateNonanticipativityConstraints( self ):
        AlreadyAdded = [ [ False for v in range( self.GetNrQuantityVariable() ) ]  for w in range( self.GetNrQuantityVariable() ) ]
        considertimebucket = self.Instance.TimeBucketSet;
         # Non anticipitativity only for period 1 for now
        for w1 in self.ScenarioSet:
            for w2 in range(w1 + 1, self.NrScenario):
                for p in self.Instance.ProductSet:
                    for t in considertimebucket:
                        IndexQuantity1 = self.GetIndexQuantityVariable(p, t, w1)
                        IndexQuantity2 = self.GetIndexQuantityVariable(p, t, w2)
                        if self.Scenarios[w1].QuanitityVariable[t][p] == self.Scenarios[w2].QuanitityVariable[t][p] \
                                and not AlreadyAdded[IndexQuantity1][IndexQuantity2]:
                            AlreadyAdded[IndexQuantity1][IndexQuantity2] = True
                            AlreadyAdded[IndexQuantity2][IndexQuantity1] = True
                            if not ( self.Model == Constants.ModelYQFix ):
                                vars = [ self.GetIndexQuantityVariable(p, t, w1), self.GetIndexQuantityVariable(p, t, w2) ]
                                coeff = [1.0, -1.0]
                                righthandside = [0.0]

                                # PrintConstraint( vars, coeff, righthandside )
                                self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                         senses=["E"],
                                                         rhs=righthandside)

                            if not ( self.Model == Constants.ModelYQFix or self.Model == Constants.ModelYFix ):
                                vars = [ self.GetIndexProductionVariable(p, t, w1), self.GetIndexProductionVariable(p, t, w2) ]
                                coeff = [1.0, -1.0]
                                righthandside = [0.0]

                                # PrintConstraint( vars, coeff, righthandside )
                                self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                                  senses=["E"],
                                                                  rhs=righthandside)
                            # if self.Instance.HasExternalDemand[p] and not (self.Model == Constants.ModelYQFix):
                            #     vars = [ self.GetIndexBackorderVariable(p, t, w1), self.GetIndexBackorderVariable(p, t, w2) ]
                            #     coeff = [1.0, -1.0]
                            #     righthandside = [0.0]
                            #     # PrintConstraint( vars, coeff, righthandside )
                            #     self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                            #                              senses=["E"],
                            #                              rhs=righthandside)
                            #
                            # vars = [ self.GetIndexInventoryVariable(p, t, w1), self.GetIndexInventoryVariable(p, t, w2) ]
                            # coeff = [1.0, -1.0]
                            # righthandside = [0.0]
                            # # PrintConstraint( vars, coeff, righthandside )
                            # self.Cplex.linear_constraints.add(  lin_expr=[cplex.SparsePair(vars, coeff)],
                            #                                     senses=["E"],
                            #                                     rhs=righthandside )


                                # This function creates the non anticipitativity constraint
    #For debug purpose, transfor the multi stage in two stage by adding the required constraints
    def CreateTwostageFromMultistageConstraints(self):
        AlreadyAdded = [[False for v in range(self.GetNrQuantityVariable())] for w in
                        range(self.GetNrQuantityVariable())]
        for w1 in self.ScenarioSet:
               for w2 in  self.ScenarioSet:
                    for p in self.Instance.ProductSet:
                           for t in self.Instance.TimeBucketSet:
                               IndexQuantity1 = self.GetIndexQuantityVariable(p, t, w1)
                               IndexQuantity2 = self.GetIndexQuantityVariable(p, t, w2)

                               if  not AlreadyAdded[IndexQuantity1][IndexQuantity2] and IndexQuantity1<>IndexQuantity2:
                                   AlreadyAdded[IndexQuantity1][IndexQuantity2] = True
                                   AlreadyAdded[IndexQuantity2][IndexQuantity1] = True
                                   vars = [IndexQuantity1,IndexQuantity2]
                                   coeff = [1.0, -1.0]
                                   righthandside = [0.0]

                                   # PrintConstraint( vars, coeff, righthandside )
                                   self.Cplex.linear_constraints.add(
                                                            lin_expr=[cplex.SparsePair(vars, coeff)],
                                                            senses=["E"],
                                                            rhs=righthandside)



    # Define the constraint of the model
    def CreateConstraints( self ):
        if Constants.Debug:
            print "Creat flow constraints ..."
        self.CreateFlowConstraints()
        #if len(self.GivenQuantity) == 0:
        if Constants.Debug:
            print "Creat production constraints ..."
        if not ( self.EvaluateSolution or self.YFixHeuristic ):
            self.CreateProductionConstraints()
        if Constants.Debug:
            print "Creat capacity constraints ..."
        self.CreateCapacityConstraints()
        if  not self.UseImplicitNonAnticipativity and not self.EVPI:
            if Constants.Debug:
                print "Creat non anticipativity  constraints ..."
            self.CreateNonanticipativityConstraints( )
        if self.EvaluateSolution or self.YFixHeuristic:
            if Constants.Debug:
                print "Creat given setup and given setup..."
            self.CreateCopyGivenSetupConstraints()

        if self.WamStart:
            print "Use warm start"
            self.WarmStartGivenSetupConstraints()

        #if self.UseSafetyStock:
        #    self.CreateSafetyStockConstraints()
        #print "start create LS ...."
        #self.CreateLSInequalities()
        #print "end create LS ...."
        if self.EvaluateSolution:
            if self.Model == Constants.ModelYQFix or self.Model == Constants.ModelYFix:
                if Constants.Debug:
                    print "Creat given setup and given quantity..."
                self.CreateCopyGivenQuantityConstraints( )

        #print "Attention remove the constraint which transfor Multi stages in two stages"
        #self.CreateTwostageFromMultistageConstraints()


    #This function build the CPLEX model
    def BuildModel( self ):
        #Create the variabbles and constraints
        if Constants.Debug:
            print "start to creat variables ..."
        self.CreateVariable()
        if Constants.Debug:
            print "start to creat constraints ..."
        self.CreateConstraints()



    def TuneCplexParamter(self):
       # self.Cplex.parameters.mip.strategy.probe.set(3)
        if self.MipSetting == "Probing00":
            self.Cplex.parameters.mip.strategy.probe.set(-1)
        elif self.MipSetting == "Probing0":
            self.Cplex.parameters.mip.strategy.probe.set(0)
        elif self.MipSetting == "Probing1":
            self.Cplex.parameters.mip.strategy.probe.set(1)
        elif self.MipSetting == "Probing2":
            self.Cplex.parameters.mip.strategy.probe.set(2)
        elif self.MipSetting == "Probing3":
            self.Cplex.parameters.mip.strategy.probe.set(3)
        elif self.MipSetting == "CutFactor10":
            self.Cplex.parameters.mip.limits.cutsfactor.set(10)
        elif self.MipSetting == "emphasis0":
            self.Cplex.parameters.emphasis.mip.set(0)
        elif self.MipSetting == "emphasis1":
            self.Cplex.parameters.emphasis.mip.set(1)
        elif self.MipSetting == "emphasis2":
            self.Cplex.parameters.emphasis.mip.set(2)
        elif self.MipSetting == "emphasis3":
            self.Cplex.parameters.emphasis.mip.set(3)
        elif self.MipSetting == "emphasis4":
            self.Cplex.parameters.emphasis.mip.set(4)
        elif self.MipSetting == "localbranching":
            self.Cplex.parameters.mip.strategy.lbheur.set(1)
        elif self.MipSetting == "heuristicfreq10":
            self.Cplex.parameters.mip.strategy.heuristicfreq.set(10)
        elif self.MipSetting == "feasibilitypomp0":
            self.Cplex.parameters.mip.strategy.fpheur.set(0)
        elif self.MipSetting == "feasibilitypomp1":
            self.Cplex.parameters.mip.strategy.fpheur.set(1)
        elif self.MipSetting == "feasibilitypomp2":
            self.Cplex.parameters.mip.strategy.fpheur.set(2)
        elif self.MipSetting == "BB":
            self.Cplex.parameters.mip.strategy.search.set(1)
        elif self.MipSetting == "flowcovers1":
            self.Cplex.parameters.mip.cuts.flowcovers.set(1)
        elif self.MipSetting == "flowcovers2":
            self.Cplex.parameters.mip.cuts.flowcovers.set(2)
        elif self.MipSetting == "pathcut1":
            self.Cplex.parameters.mip.cuts.pathcut.set(1)
        elif self.MipSetting == "pathcut2":
            self.Cplex.parameters.mip.cuts.pathcut.set(2)
        elif self.MipSetting == "gomory1":
            self.Cplex.parameters.mip.cuts.gomory.set(1)
        elif self.MipSetting == "gomor2":
            self.Cplex.parameters.mip.cuts.gomory.set(2)
        elif self.MipSetting == "zerohalfcut1":
            self.Cplex.parameters.mip.cuts.zerohalfcut.set(1)
        elif self.MipSetting == "zerohalfcut2":
            self.Cplex.parameters.mip.cuts.zerohalfcut.set(2)
        elif self.MipSetting == "mircut1":
            self.Cplex.parameters.mip.cuts.mircut.set(1)
        elif self.MipSetting == "mircut2":
            self.Cplex.parameters.mip.cuts.mircut.set(2)
        elif self.MipSetting == "implied1":
            self.Cplex.parameters.mip.cuts.implied.set(1)
        elif self.MipSetting == "implied2":
            self.Cplex.parameters.mip.cuts.implied.set(2)
        elif self.MipSetting == "gubcovers1":
            self.Cplex.parameters.mip.cuts.gubcovers.set(1)
        elif self.MipSetting == "gubcovers2":
            self.Cplex.parameters.mip.cuts.gubcovers.set(2)
        elif self.MipSetting == "disjunctive1":
            self.Cplex.parameters.mip.cuts.disjunctive.set(1)
        elif self.MipSetting == "disjunctive2":
            self.Cplex.parameters.mip.cuts.disjunctive.set(2)
        elif self.MipSetting == "disjunctive3":
            self.Cplex.parameters.mip.cuts.disjunctive.set(3)
        elif self.MipSetting == "covers1":
            self.Cplex.parameters.mip.cuts.covers.set(1)
        elif self.MipSetting == "covers2":
            self.Cplex.parameters.mip.cuts.covers.set(2)
        elif self.MipSetting == "covers3":
            self.Cplex.parameters.mip.cuts.covers.set(3)
        elif self.MipSetting == "cliques1":
            self.Cplex.parameters.mip.cuts.cliques.set(1)
        elif self.MipSetting == "cliques2":
            self.Cplex.parameters.mip.cuts.cliques.set(2)
        elif self.MipSetting == "cliques3":
            self.Cplex.parameters.mip.cuts.cliques.set(3)
        elif self.MipSetting == "allcutmax":
            self.Cplex.parameters.mip.cuts.cliques.set(3)
            self.Cplex.parameters.mip.cuts.covers.set(3)
            self.Cplex.parameters.mip.cuts.disjunctive.set(3)
            self.Cplex.parameters.mip.cuts.gubcovers.set(2)
            self.Cplex.parameters.mip.cuts.implied.set(2)
            self.Cplex.parameters.mip.cuts.mircut.set(2)
            self.Cplex.parameters.mip.cuts.zerohalfcut.set(2)
            self.Cplex.parameters.mip.cuts.gomory.set(2)
            self.Cplex.parameters.mip.cuts.pathcut.set(2)
            self.Cplex.parameters.mip.cuts.flowcovers.set(2)
        elif self.MipSetting == "variableselect00":
            self.Cplex.parameters.mip.strategy.variableselect.set(-1)
        elif self.MipSetting == "variableselect1":
            self.Cplex.parameters.mip.strategy.variableselect.set(1)
        elif self.MipSetting == "variableselect2":
            self.Cplex.parameters.mip.strategy.variableselect.set(2)
        elif self.MipSetting == "variableselect3":
            self.Cplex.parameters.mip.strategy.variableselect.set(3)
        elif self.MipSetting == "variableselect4":
            self.Cplex.parameters.mip.strategy.variableselect.set(4)
        elif self.MipSetting == "BranchUp":
            self.Cplex.parameters.mip.strategy.branch.set(-1)
        elif self.MipSetting == "BranchDefault":
            self.Cplex.parameters.mip.strategy.branch.set(0)
        elif self.MipSetting == "BranchDown":
            self.Cplex.parameters.mip.strategy.branch.set(1)
        elif self.MipSetting == "NoOtherCuts":
            self.Cplex.parameters.mip.cuts.cliques.set(-1)
            self.Cplex.parameters.mip.cuts.covers.set(-1)
            self.Cplex.parameters.mip.cuts.disjunctive.set(-1)
            self.Cplex.parameters.mip.cuts.gubcovers.set(-1)
            self.Cplex.parameters.mip.cuts.implied.set(-1)
            self.Cplex.parameters.mip.cuts.zerohalfcut.set(-1)
            self.Cplex.parameters.mip.cuts.flowcovers.set(-1)
        elif self.MipSetting == "cutmax":
             self.Cplex.parameters.mip.cuts.gomory.set(2)
             self.Cplex.parameters.mip.cuts.pathcut.set(2)
             self.Cplex.parameters.mip.cuts.mircut.set(2)
             self.Cplex.parameters.mip.cuts.cliques.set(-1)
             self.Cplex.parameters.mip.cuts.covers.set(-1)
             self.Cplex.parameters.mip.cuts.disjunctive.set(-1)
             self.Cplex.parameters.mip.cuts.gubcovers.set(-1)
             self.Cplex.parameters.mip.cuts.implied.set(-1)
             self.Cplex.parameters.mip.cuts.zerohalfcut.set(-1)
             self.Cplex.parameters.mip.cuts.flowcovers.set(-1)


    #This function set the parameter of CPLEX, run Cplex, and return a solution
    def Solve( self, createsolution = True ):
        start_time = time.time()
        # Our aim is to minimize cost.
        self.Cplex.objective.set_sense(self.Cplex.objective.sense.minimize)
        if Constants.Debug:
            self.Cplex.write("mrp.lp")
        else:
            #name = "mrp_log%r_%r_%r" % ( self.Instance.InstanceName, self.Model, self.DemandScenarioTree.Seed )
            self.Cplex.set_log_stream( None )
            self.Cplex.set_results_stream( None )
            self.Cplex.set_warning_stream( None )
            self.Cplex.set_error_stream( None )

        # tune the paramters
        self.Cplex.parameters.timelimit.set( Constants.AlgorithmTimeLimit )
        self.Cplex.parameters.mip.limits.treememory.set( 700000000.0 )
        self.Cplex.parameters.threads.set(1)
        self.TuneCplexParamter()


        if self.YFixHeuristic:
            self.Cplex.parameters.lpmethod.set(self.Cplex.parameters.lpmethod.values.barrier)
            self.Cplex.parameters.threads.set(1)

        end_modeling = time.time();

        #solve the problem
        #if self.Model == Constants.ModelYFix:
        #    self.Cplex.parameters.benders.strategy.set(3)
        self.Cplex.solve()


        buildtime = end_modeling - start_time;
        solvetime = time.time() - end_modeling;

        # Handle the results
        sol = self.Cplex.solution
        if Constants.Debug:
            print "CPLEx Solve Time: %r   CPLEX build time %s  feasible %s" % (solvetime, buildtime, sol.is_primal_feasible())

        if sol.is_primal_feasible():
            if createsolution:

                Solution = self.CreateMRPSolution(sol, solvetime)
                #costperscenarios, averagecost, std_devcost = self.ComputeCostPerScenario()

                if Constants.Debug:
                    print "fill solve information......"

                modelname = self.Model
                if self.UseSafetyStock:
                    modelname = modelname + "SS"

                self.SolveInfo = [ self.Instance.InstanceName,
                                   modelname,
                                   Solution.CplexCost,
                                Solution.CplexCost,
                                sol.status[sol.get_status()],
                                buildtime,
                                solvetime,
                                Solution.CplexGap,
                                #sol.progress.get_num_iterations(),
                                #sol.progress.get_num_nodes_processed(),
                                self.Cplex.variables.get_num(),
                                self.Cplex.linear_constraints.get_num(),
                                Solution.InventoryCost,
                                Solution.BackOrderCost,
                                Solution.SetupCost,
                                #averagecost,
                                #std_devcost,
                                self.Instance.NrLevel,
                                self.Instance.NrProduct,
                                self.Instance.NrTimeBucket,
                                self.DemandScenarioTree.Seed,
                                self.NrScenario,
                                self.Instance.MaxLeadTime,
                                self.Instance.BranchingStrategy,
                                self.DemandScenarioTree.Distribution ]
            else:
                Solution = None

            return Solution

        else:
            print("No solution available.")
            self.Cplex.conflict.refine(self.Cplex.conflict.all_constraints());
            conflict = self.Cplex.conflict.get()
            conflicting = [ i for i in range( len( conflict ) ) if conflict[i] == 3 ]
            groups = self.Cplex.conflict.get_groups(conflicting )
            print "Conflicts: %r"% groups, conflicting
            for i in groups:
                (a,((b,c),)) =i
                print "Constraint %r, %r:"%(c,self.Cplex.linear_constraints.get_names([c]) )

    #This function print the scenario of the instance in an excel file
    def PrintScenarioToFile( self ):
        writer = pd.ExcelWriter( "./Instances/" + self.Instance.InstanceName + "_Scenario.xlsx",
                                        engine='openpyxl' )
        for s in self.Scenarios:
            s.PrintScenarioToExcel( writer )
        writer.save()


    def CreateMRPSolution(self, sol, solvetime):
        if Constants.Debug:
            print "Start to create a solution..."
        scenarioset = self.ScenarioSet
        scenarios = self.Scenarios
        timebucketset = self.Instance.TimeBucketSet
        partialsol = Constants.PrintOnlyFirstStageDecision and self.Model == Constants.ModelYFix and not self.EvaluateSolution
        if partialsol:
            scenarioset = [0]
            timebucketset = range( self.Instance.NrTimeBucketWithoutUncertaintyBefore +1 )
            scenarios = [self.Scenarios[0]]
            partialsol = True
        if Constants.Debug:
            print "read  quanity..."
        objvalue = sol.get_objective_value()
        array = [self.GetIndexQuantityVariable(p, t, w) for p in self.Instance.ProductSet for t in timebucketset for w
                 in scenarioset];
        # testarray = [ "p:%st:%sw:%s"%(p, t, w)  for p in self.Instance.ProductSet for t in self.Instance.TimeBucketSet for w in self.ScenarioSet ]
        if Constants.Debug:
            print "call cplex..."
        solquantity = sol.get_values(array)
        if Constants.Debug:
            print "transform to 3d array......"
        solquantity = Tool.Transform3d(solquantity, self.Instance.NrProduct, len(timebucketset), len(scenarioset))

        if Constants.Debug:
            print "read  setup..."
        # here self.Instance.TimeBucketSet is used because the setups are decided for the complete time horizon in YFix
        array = [self.GetIndexProductionVariable(p, t, w) for p in self.Instance.ProductSet for t in
                 self.Instance.TimeBucketSet for w in scenarioset]
        solproduction = sol.get_values(array)
        if Constants.Debug:
            print "transform to 3d array......"

        solproduction = Tool.Transform3d(solproduction, self.Instance.NrProduct, len(self.Instance.TimeBucketSet),
                                         len(scenarioset))

        if Constants.Debug:
            print "read  inventory..."

        array = [self.GetIndexInventoryVariable(p, t, w) for p in self.Instance.ProductSet for t in timebucketset for w
                 in scenarioset]
        solinventory = sol.get_values(array)
        if Constants.Debug:
            print "transform to 3d array......"

        solinventory = Tool.Transform3d(solinventory, self.Instance.NrProduct, len(timebucketset), len(scenarioset))

        if Constants.Debug:
            print "read  backorders..."
        array = [self.GetIndexBackorderVariable(p, t, w)
                 for p in self.Instance.ProductWithExternalDemand for t in timebucketset for w in scenarioset]
        solbackorder = sol.get_values(array)
        if Constants.Debug:
            print "transform to 3d array......"
        solbackorder = Tool.Transform3d(solbackorder, len(self.Instance.ProductWithExternalDemand), len(timebucketset),
                                        len(scenarioset))

        if Constants.Debug:
            print "update scenario tree......"

        if self.Model <> Constants.ModelYQFix:
            self.DemandScenarioTree.FillQuantityToOrder(sol)

        if Constants.Debug:
            print "Create soluton object......"
        Solution = MRPSolution(self.Instance, solquantity, solproduction, solinventory, solbackorder, scenarios,
                               self.DemandScenarioTree, partialsolution=partialsol)
        Solution.CplexCost = objvalue
        Solution.CplexGap = 0
        Solution.CplexNrVariables = self.Cplex.variables.get_num()
        Solution.CplexNrConstraints = self.Cplex.linear_constraints.get_num()
        if not self.EvaluateSolution and not self.YFixHeuristic:
            Solution.CplexGap = sol.MIP.get_mip_relative_gap()
        Solution.CplexTime = solvetime
        return Solution

    #This function compute the cost per scenario
    def ComputeCostPerScenario( self ):
        # Compute the cost per scenario:
        costperscenarion = [ sum( self.Cplex.solution.get_values( [self.GetIndexInventoryVariable(p, t, w)] )[0]
                                * self.Instance.InventoryCosts[p] * math.pow( self.Instance.Gamma, t )
                                + self.Cplex.solution.get_values( [self.GetIndexProductionVariable(p, t, w)] )[0]
                                * self.Instance.SetupCosts[p] * math.pow( self.Instance.Gamma, t )
                                for p in self.Instance.ProductSet
                                for t in range(self.Instance.NrTimeBucket ))
                            for w in self.ScenarioSet]


        costperscenarion = [costperscenarion[w]
                            + sum(  self.Cplex.solution.get_values([self.GetIndexBackorderVariable(p, t, w)])[0]
                                     * self.Instance.BackorderCosts[p] * math.pow(self.Instance.Gamma, t)
                                    for p in self.Instance.ProductWithExternalDemand
                                        for t in range(self.Instance.NrTimeBucket -1 ))
                                           for w in self.ScenarioSet ]

        costperscenarion = [costperscenarion[w]
                            + sum(  self.Cplex.solution.get_values([self.GetIndexBackorderVariable(p, self.Instance.NrTimeBucket - 1, w)])[0]
                                    * self.Instance.LostSaleCost[p] * math.pow( self.Instance.Gamma, self.Instance.NrTimeBucket - 1)
                                    for p in self.Instance.ProductWithExternalDemand)
                                                    for w in self.ScenarioSet ]

        Sum = sum(costperscenarion[w] for w in self.ScenarioSet)
        Average = Sum / self.NrScenario
        sumdeviation = sum(math.pow((costperscenarion[w] - Average), 2) for s in self.ScenarioSet)
        std_dev = math.sqrt( (sumdeviation / self.NrScenario ) )


        return costperscenarion, Average, std_dev

    #This function return the upperbound on hte quantities infered from the demand
    @staticmethod
    def GetBigMDemValue( instance, scenarioset, p ):
        #mdem = 10000000
        if instance.HasExternalDemand[ p ] :
            mdem = ( sum( max( s.Demands[t][p] for s in scenarioset ) for t in instance.TimeBucketSet ) )
        else :
            mdem = sum( instance.Requirements[q][p] * MIPSolver.GetBigMDemValue( instance, scenarioset, q ) for q in instance.RequieredProduct[p] )


        return mdem

    #This function return the value of the big M variable
    @staticmethod
    def GetBigMValue( instance, scenarioset, p ):
        mdem = MIPSolver.GetBigMDemValue(instance, scenarioset, p)

        #compute m based on the capacity of the resource
        mres = min( instance.Capacity[k] / instance.ProcessingTime[p][k]  if instance.ProcessingTime[p][k] > 0  else Constants.Infinity for k in range( instance.NrResource ) )
        m = min( [ mdem, mres ] )
        return m

    def ModifyMipForScenarioTree(self, scenariotree):
        self.DemandScenarioTree = scenariotree
        self.DemandScenarioTree.Owner = self
        self.NrScenario = len([n for n in self.DemandScenarioTree.Nodes if len(n.Branches) == 0])
        self.ComputeIndices()
        self.Scenarios = scenariotree.GetAllScenarios(True)
        self.ScenarioSet = range(self.NrScenario)
        # Redefine the flow conservation constraint
        constrainttuples = []
        for p in self.Instance.ProductWithExternalDemand:
            for w in self.ScenarioSet:
                righthandside = -1 * self.Instance.StartingInventories[p]
                for t in self.Instance.TimeBucketSet:
                    righthandside = righthandside + self.Scenarios[w].Demands[t][p]
                    constrnr = self.FlowConstraintNR[w][p][t]
                    constrainttuples.append((constrnr, righthandside))

        self.Cplex.linear_constraints.set_rhs(constrainttuples)
    #This function modify the MIP tosolve the scenario tree given in argument.
    #It is assumed that both the initial scenario tree and the new one have a single scenario
    def ModifyMipForScenario(self, demanduptotime, time):
        self.DemandScenarioTree = None #not up to date anymore
        #self.DemandScenarioTree.Owner = self
        #self.NrScenario = len([n for n in self.DemandScenarioTree.Nodes if len(n.Branches) == 0])
        #self.ComputeIndices()
        #self.Scenarios = scenariotree.GetAllScenarios(True)
        #self.ScenarioSet = range(self.NrScenario)
        #Redefine the flow conservation constraint
        constrainttuples=[]
        for p in self.Instance.ProductWithExternalDemand:
           #for w in self.ScenarioSet:
                righthandside = -1 * self.Instance.StartingInventories[p]
                for t in self.Instance.TimeBucketSet:
                    if t< time -1:
                        self.Scenarios[0].Demands[t][p] = demanduptotime[t][p]
                        righthandside = righthandside + self.Scenarios[0].Demands[t][p]
                        constrnr = self.FlowConstraintNR[0][p][t]
                        constrainttuples.append( ( constrnr, righthandside) )
                    if t == time -1:
                        self.Scenarios[0].Demands[t][p] = demanduptotime[t][p]
                        righthandside = 0
                        constrnr = self.FlowConstraintNR[0][p][t]
                        constrainttuples.append((constrnr, righthandside))
                        self.Cplex.linear_constraints.set_rhs( constrainttuples )

        knowndemandtuples = [ ( self.GetIndexKnownDemand(p),  sum(demanduptotime[t][p] for t in range( time )) )  for p in self.Instance.ProductWithExternalDemand]
        self.Cplex.variables.set_lower_bounds(knowndemandtuples)
        self.Cplex.variables.set_upper_bounds(knowndemandtuples)
        # This function modify the MIP tosolve the scenario tree given in argument.
        # It is assumed that both the initial scenario tree and the new one have a single scenario

    #This function modify the MIP to fix the quantities given in argument
    def ModifyMipForFixQuantity(self, givenquanities, fixuntil = -1 ):
            timeset = self.Instance.TimeBucketSet
            if fixuntil > -1:
                timeset = range( fixuntil )
            # Redefine the flow conservation constraint
            constrainttuples = []

            # Capacity constraint
            for p in self.Instance.ProductSet:
                for t in timeset:
                            righthandside = givenquanities[t][p]#
                            constrnr = "L"+self.QuantityConstraintNR[0][p][t]
                            constrainttuples.append((constrnr, righthandside))


            self.Cplex.linear_constraints.set_rhs( constrainttuples )