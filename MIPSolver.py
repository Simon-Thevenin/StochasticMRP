import cplex
import pandas as pd
import openpyxl as opxl
from MRPInstance import MRPInstance
from MRPSolution import MRPSolution
from ScenarioTreeNode import ScenarioTreeNode
import time
import sys
import numpy as np
import csv
import math
from datetime import datetime
import cPickle as pickle

class MIPSolver(object):
    M = cplex.infinity
    ModelYQFix = "YQFix"
    ModelYFix = "YFix"
    Model_Fix = "_Fix"
    # constructor

    def __init__(self,
                 instance,
                 model,
                 scenariotree,
                 usenonaticipativity = True,
                 implicitnonanticipativity = False,
                 givensolution = [],
                 fixsolutionuntil = -1,
                 evaluatesolution = False,
                 debug = False  ):

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
        self.UseNonAnticipativity = usenonaticipativity
        #If non anticipativity constraints are added, they can be implicit or explicit.
        self.UseImplicitNonAnticipativity = implicitnonanticipativity
        self.UseNonAnticipativity

        #The set of scenarios used to solve the instance
        self.DemandScenarioTree = scenariotree
        self.DemandScenarioTree.Owner = self
        self.NrScenario = len( [ n for n in self.DemandScenarioTree.Nodes if len( n.Branches ) == 0 ] )
        self.ComputeIndices()
        self.Scenarios =  scenariotree.GetAllScenarios()

        self.GivenSolution = givensolution
        self.FixSolutionUntil =  fixsolutionuntil


        self.ScenarioSet = range( self.NrScenario )
        self.Cplex = cplex.Cplex()
        self.Debug = debug

        self.EvaluateSolution = evaluatesolution

        #This list is filled after the resolution of the MIP
        self.SolveInfo = []
        #Compute the index of the variable if two stage is used
        # self.NrQuantiyVariablesTwoStages  = 0
        # self.NrInventoryVariableTwoStages = 0
        # self.NrProductionVariableTwoStages = 0
        # self.NrBackorderVariableTwoStages = 0
        # self.StartQuantityVariableTwoStages = 0
        # self.StartInventoryVariableTwoStages = 0
        # self.StartProdustionVariableTwoStages = 0
        # self.StartBackorderVariableTwoStages = 0

        # Compute the start of index and the number of variables for the considered instance
    def ComputeIndices( self ):

            scenariotimeproduct = self.Instance.NrProduct * self.Instance.NrTimeBucket * self.NrScenario
            self.NrQuantiyVariables = scenariotimeproduct
            self.NrInventoryVariable =scenariotimeproduct
            self.NrProductionVariable = scenariotimeproduct
            self.NrBackorderVariable = len( self.Instance.ProductWithExternalDemand ) * self.Instance.NrTimeBucket * self.NrScenario
            self.StartQuantityVariable = 0
            self.StartInventoryVariable = self.StartQuantityVariable + self.NrQuantiyVariables
            self.StartProdustionVariable = self.StartInventoryVariable + self.NrInventoryVariable
            self.StartBackorderVariable = self.StartProdustionVariable + self.NrProductionVariable

            # The indices of the variable in the case where the non anticipativity constraints are created explicitely
            nodeproduct = self.Instance.NrProduct * ( self.DemandScenarioTree.NrNode - 1)
            self.NrQuantiyVariablesWithoutNonAnticipativity =  nodeproduct# remove the root node
            self.NrInventoryVariableWithoutNonAnticipativity = nodeproduct
            self.NrProductionVariableWithoutNonAnticipativity = nodeproduct
            self.NrBackorderVariableWithoutNonAnticipativity = len( self.Instance.ProductWithExternalDemand ) * ( self.DemandScenarioTree.NrNode - 1)
            self.StartQuantityVariableWithoutNonAnticipativity = 0
            self.StartInventoryVariableWithoutNonAnticipativity = self.StartQuantityVariableWithoutNonAnticipativity + self.NrQuantiyVariablesWithoutNonAnticipativity
            self.StartProductionVariableWithoutNonAnticipativity = self.StartInventoryVariableWithoutNonAnticipativity + self.NrInventoryVariableWithoutNonAnticipativity
            self.StartBackorderVariableWithoutNonAnticipativity = self.StartProductionVariableWithoutNonAnticipativity + self.NrProductionVariableWithoutNonAnticipativity

            # The indices of the variable in the case where the a two stage problem is solved
            #self.NrQuantiyVariablesTwoStages = self.NrProduct + self.NrProduct * (
            #self.NrTimeBucket - 1) * self.NrScenario
            #self.NrInventoryVariableTwoStages = self.NrProduct + self.NrProduct * (
            #self.NrTimeBucket - 1) * self.NrScenario
            #self.NrProductionVariableTwoStages = self.NrProduct + self.NrProduct * (
            #self.NrTimeBucket - 1) * self.NrScenario
            #self.NrBackorderVariableTwoStages = self.NrProduct + self.NrProduct * (
            #self.NrTimeBucket - 1) * self.NrScenario
            #self.StartQuantityVariableTwoStages = 0
            #self.StartInventoryVariableTwoStages = self.StartQuantityVariableTwoStages + self.NrQuantiyVariablesTwoStages
            #self.StartProdustionVariableTwoStages = self.StartInventoryVariableTwoStages + self.NrInventoryVariableTwoStages
            #self.StartBackorderVariableTwoStages = self.StartProdustionVariableTwoStages + self.NrProductionVariableTwoStages

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
            self.StartBackorderVariableYFix = self.StartProdustionVariableYFix + self.NrProductionVariablesYFix


    # This function returns the name of the quantity variable for product p and time t
    def GetNameQuantityVariable(self, p, t, w):
        scenarioindex = -1

        if self.Model == MIPSolver.ModelYQFix:
            scenarioindex = 0
        elif self.UseNonAnticipativity:
            scenarioindex = w
        else:
            scenarioindex = self.Scenarios[w].QuanitityVariable[t][p]

        return "q_p_t_s_%d_%d_%d" % (p, t, scenarioindex)


    # This function returns the name of the inventory variable for product p and time t
    def GetNameInventoryVariable(self, p, t, w):
        scenarioindex = -1;

        if self.UseNonAnticipativity:
            scenarioindex = w
        else:
            scenarioindex = self.Scenarios[w].InventoryVariable[t][p]

        return "i_%d_%d_%d" % (p, t, scenarioindex)


    # This function returns the name of the production variable for product p and time t
    def GetNameProductionVariable(self, p, t, w):
        scenarioindex = -1;
        if self.UseNonAnticipativity:
            if self.Model == MIPSolver.ModelYQFix or self.Model == MIPSolver.ModelYFix:
                scenarioindex = 0
            else:
                scenarioindex = w
        else:
            scenarioindex = self.Scenarios[w].ProductionVariable[t][p]

        return "p_%d_%d_%d" % (p, t, scenarioindex)


    # This function returns the name of the backorder variable for product p and time t
    def GetNameBackOrderQuantity(self, p, t, w):
        scenarioindex = -1;
        if self.UseNonAnticipativity:
            scenarioindex = w
        else:
            scenarioindex = self.Scenarios[w].BackOrderVariable[t][p]

        return "b_%d_%d_%d" % (p, t, scenarioindex)


    # the function GetIndexQuantityVariable returns the index of the variable Q_{p, t}. Quantity of product p produced at time t
    def GetIndexQuantityVariable(self, p, t, w):
        if self.Model == MIPSolver.ModelYQFix:
            return self.GetStartQuantityVariable() + t * self.Instance.NrProduct + p
        elif self.UseNonAnticipativity:
            return self.GetStartQuantityVariable() + w * (self.Instance.NrTimeBucket) * self.Instance.NrProduct + t * self.Instance.NrProduct + p
        else:
            return self.Scenarios[w].QuanitityVariable[t][p];


    # the function GetIndexInventoryVariable returns the index of the variable I_{p, t}. Inventory of product p produced at time t
    def GetIndexInventoryVariable(self, p, t, w):
        if self.UseNonAnticipativity:
            return self.GetStartInventoryVariable() + w * self.Instance.NrTimeBucket * self.Instance.NrProduct + t * self.Instance.NrProduct + p
        else:
            return self.Scenarios[w].InventoryVariable[t][p];


    # the function GetIndexProductionVariable returns the index of the variable Y_{p, t, w}.
    # This variable equal to one is product p is produced at time t, 0 otherwise
    def GetIndexProductionVariable(self, p, t, w):
        if self.Model == MIPSolver.ModelYQFix or self.Model == MIPSolver.ModelYFix:
            return self.GetStartProductionVariable() + t * self.Instance.NrProduct + p
        elif self.UseNonAnticipativity:
            return self.StartProdustionVariable + w * self.Instance.NrTimeBucket * self.Instance.NrProduct + t * self.Instance.NrProduct + p
        else:
            return self.Scenarios[w].ProductionVariable[t][p];


    # the function GetIndexBackorderVariable returns the index of the variable B_{p, t}. Quantity of product p produced backordered at time t
    def GetIndexBackorderVariable(self, p, t, w):
        if self.UseNonAnticipativity:
            return self.GetStartBackorderVariable() \
                   + w * self.Instance.NrTimeBucket * len( self.Instance.ProductWithExternalDemand )  \
                   + t * len( self.Instance.ProductWithExternalDemand ) + self.Instance.ProductWithExternalDemandIndex[p]
        else:
            return self.Scenarios[w].BackOrderVariable[t][p];

    #return the index at which the backorder variables starts
    def GetStartBackorderVariable( self ):
        if self.Model == MIPSolver.ModelYQFix: return self.StartBackorderVariableYQFix
        if self.Model == MIPSolver.ModelYFix: return self.StartBackorderVariableYFix
        if self.Model == MIPSolver.Model_Fix: return self.StartBackorderVariable

    #return the index at which the production variables starts
    def GetStartProductionVariable( self ):
        if self.Model == MIPSolver.ModelYQFix: return self.StartProdustionVariableYQFix
        if self.Model == MIPSolver.ModelYFix: return self.StartProdustionVariableYFix
        if self.Model == MIPSolver.Model_Fix: return self.StartProductionVariable

    #retunr the index at which the inventory variables starts
    def GetStartInventoryVariable( self ):
        if self.Model == MIPSolver.ModelYQFix: return self.StartInventoryVariableYQFix
        if self.Model == MIPSolver.ModelYFix: return self.StartInventoryVariableYFix
        if self.Model == MIPSolver.Model_Fix: return self.StartInventoryVariable

    #return the index at which the quantity variable starts
    def GetStartQuantityVariable( self ):
        if self.Model == MIPSolver.ModelYQFix: return self.StartQuantityVariablYQFix
        if self.Model == MIPSolver.ModelYFix: return self.StartQuantityVariablYFix
        if self.Model == MIPSolver.Model_Fix: return self.StartQuantityVariable

    #return the number of quantity variables
    def GetNrQuantityVariable( self ):
        if self.Model == MIPSolver.ModelYQFix: return self.NrQuantiyVariablesYQFix
        else: return self.StartQuantityVariable

    #return the number of production variables
    def GetNrProductionVariable( self ):
        if self.Model == MIPSolver.ModelYQFix: return self.NrProductionVariablesYQFix
        if self.Model == MIPSolver.ModelYFix: return self.NrProductionVariablesYFix
        if self.Model == MIPSolver.Model_Fix: return self.NrProductionVariables


    # This function define the variables
    def CreateVariable( self ):
        # Define the cost vector for each variable. As the numbber of variable changes when non anticipativity is used the cost are created differently
        # if Method == "Two-stages":
        #     inventorycosts = [Instance.InventoryCosts[p] * Instance.Scenarios[w].Probability
        #                       for w in Instance.ScenarioSet for t in range( Instance.NrTimeBucket -1 ) for p in Instance.ProductSet]
        #     setupcosts = [Instance.SetupCosts[p] * Instance.Scenarios[w].Probability
        #                   for w in Instance.ScenarioSet for t in range( Instance.NrTimeBucket -1 )  for p in Instance.ProductSet]
        #     backordercosts = [Instance.BackorderCosts[p] * Instance.Scenarios[w].Probability
        #                       for w in Instance.ScenarioSet for t in range( Instance.NrTimeBucket -1 )  for p in Instance.ProductSet]
        #     #Add the cost of time 0
        #     inventorycosts =  [ Instance.InventoryCosts[p]  for p in Instance.ProductSet ] + inventorycosts
        #     setupcosts = [Instance.SetupCosts[p] for p in Instance.ProductSet ] + setupcosts
        #     backordercosts = [Instance.BackorderCosts[p] for p in Instance.ProductSet ] + backordercosts
        #     nrinventoryvariable = Instance.NrQuantiyVariablesTwoStages;
        #     nrbackordervariable = Instance.NrBackorderVariableTwoStages;
        #     nrproductionvariable = Instance.NrProductionVariableTwoStages;
        #     nrquantityvariable = Instance.NrQuantiyVariablesTwoStages;

        if self.UseNonAnticipativity:
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

            if self.Model == self.ModelYQFix:
                nrquantityvariable = self.NrQuantiyVariablesYQFix
                nrproductionvariable = self.NrProductionVariablesYQFix
            if self.Model == self.ModelYFix:
                nrproductionvariable = self.NrProductionVariablesYFix

            if self.Model == self.ModelYQFix or self.Model == self.ModelYFix:
                setupcosts = [ self.Instance.SetupCosts[p] * sum(
                    self.Scenarios[w].Probability for w in self.ScenarioSet) * math.pow( self.Instance.Gamma, t )
                              for t in self.Instance.TimeBucketSet for p in self.Instance.ProductSet]

        # Define only the required variables
        else:
            nrquantityvariable = self.Instance.NrQuantiyVariablesWithoutNonAnticipativity
            nrinventoryvariable = self.Instance.NrInventoryVariableWithoutNonAnticipativity
            nrbackordervariable = self.Instance.NrBackorderVariableWithoutNonAnticipativity
            nrproductionvariable = self.Instance.NrProductionVariableWithoutNonAnticipativity
            inventorycosts = [0] * nrinventoryvariable
            setupcosts = [0] * nrproductionvariable
            backordercosts = [0] * nrbackordervariable
            for w in self.ScenarioSet:
                for t in self.Instance.TimeBucketSet:
                    for p in self.Instance.ProductSet:
                        # Add the cost of the cariable representing multiple scenarios
                        inventorycostindex = self.Scenarios[w].InventoryVariable[t][
                                                 p] - self.StartInventoryVariableWithoutNonAnticipativity
                        setupcostindex = self.Scenarios[w].ProductionVariable[t][
                                             p] - self.StartProdustionVariableWithoutNonAnticipativity
                        backordercostindex = self.Scenarios[w].BackOrderVariable[t][
                                                 p] - self.StartBackorderVariableWithoutNonAnticipativity
                        inventorycosts[inventorycostindex] = inventorycosts[inventorycostindex] \
                                                             + self.Instance.InventoryCosts[p] * self.Scenarios[
                            w].Probability * math.pow( self.Instance.Gamma, t )
                        setupcosts[setupcostindex] = setupcosts[setupcostindex] \
                                                     + self.Instance.SetupCosts[p] * self.Scenarios[
                            w].Probability * math.pow(self.Instance.Gamma, t)
                        if t < self.Instance.NrTimeBucket -1 and self.Instance.HasExternalDemand[p]:
                            backordercosts[backordercostindex] = backordercosts[backordercostindex] \
                                                                 + self.Instance.BackorderCosts[p] \
                                                                   * self.Scenarios[w].Probability \
                                                                   * math.pow(self.Instance.Gamma, t)
                        else: backordercosts[backordercostindex] = backordercosts[backordercostindex] \
                                                                 + self.Instance.LostSaleCost[p] \
                                                                   * self.Scenarios[w].Probability \
                                                                   * math.pow(self.Instance.Gamma, t)

                        # the variable quantity_prod_time_scenario_p_t_w indicated the quantity of product p produced at time t in scneario w
        self.Cplex.variables.add(obj=[0.0] * nrquantityvariable,
                        lb=[0.0] * nrquantityvariable,
                        ub=[self.M] * nrquantityvariable)

        # the variable inventory_prod_time_scenario_p_t_w indicated the inventory level of product p at time t in scneario w
        self.Cplex.variables.add(obj=inventorycosts,
                        lb=[0.0] * nrinventoryvariable,
                        ub=[self.M] * nrinventoryvariable)

        # the variable production_prod_time_scenario_p_t_w equals 1 if a lot of product p is produced at time t in scneario w
        self.Cplex.variables.add(obj=setupcosts,
                        lb=[0.0] * nrproductionvariable,
                        ub=[1.0] * nrproductionvariable)

        # the variable backorder_prod_time_scenario_p_t_w gives the amount of product p backordered at time t in scneario w
        self.Cplex.variables.add(obj=backordercosts,
                        lb=[0.0] * nrbackordervariable,
                        ub=[self.M] * nrbackordervariable)

        # Define the variable name.
        # Usefull for debuging purpose. Otherwise, disable it, it is time consuming.
        if self.Debug:
            quantityvars = []
            inventoryvars = []
            productionvars = []
            backordervars = []
            for p in self.Instance.ProductSet:
                for t in self.Instance.TimeBucketSet:
                    for w in self.ScenarioSet:
                        quantityvars.append( ( self.GetIndexQuantityVariable(p, t, w), self.GetNameQuantityVariable(p, t, w) ) )
                        productionvars.append( ( self.GetIndexProductionVariable(p, t, w), self.GetNameProductionVariable(p, t, w) ) )
                        inventoryvars.append( ( self.GetIndexInventoryVariable(p, t, w), self.GetNameInventoryVariable(p, t, w) ) )
                        if self.Instance.HasExternalDemand[p] :
                            backordervars.append( ( self.GetIndexBackorderVariable(p, t, w), self.GetNameBackOrderQuantity(p, t, w) ) )

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
    def CreateCopyGivenSolutionConstraints( self ):
        AlreadyAdded = [ False for v in range( self.GetNrQuantityVariable() ) ]

        # Capacity constraint
        for p in self.Instance.ProductSet:
            for t in self.Instance.TimeBucketSet:
                for w in self.ScenarioSet:
                    indexvariable = self.GetIndexQuantityVariable(p, t, w)
                    #if #self.Instance.HasExternalDemand[p] \
                       #     and
                    if   not AlreadyAdded[indexvariable] \
                            and (t <= self.FixSolutionUntil):
                        vars = [indexvariable]
                        AlreadyAdded[indexvariable] = True
                        coeff = [1.0]
                        righthandside = [round( self.GivenSolution[t][p], 2) ]
                        # PrintConstraint( vars, coeff, righthandside )
                        self.Cplex.linear_constraints.add( lin_expr=[cplex.SparsePair(vars, coeff)],
                                                           senses=["E"],
                                                           rhs=righthandside )

                        # c.variables.set_lower_bounds( GetIndexQuantityVariable(p, t, w), GivenQuantities[p][t] )
                        # c.variables.set_upper_bounds(GetIndexQuantityVariable(p, t, w), GivenQuantities[p][t])


    # Demand and materials requirement: set the value of the invetory level and backorder quantity according to
    #  the quantities produced and the demand
    def CreateFlowConstraints( self ):
        expressionstoadd = []
        sensestoadd = []
        rigthandsidestoadd = []
        for p in self.Instance.ProductSet:
            for w in self.ScenarioSet:
                # To speed up the creation of the model, only the variable and coffectiant which were not in the previous constraints are added (See the model definition)
                righthandside = [-1 * self.Instance.StartingInventories[p]]
                quantityvar = []
                quantityvarceoff = []
                dependentdemandvar = []
                dependentdemandvarcoeff = []
                for t in self.Instance.TimeBucketSet:
                    backordervar = []
                    righthandside[0] = righthandside[0] + self.Scenarios[w].Demands[t][p]
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

                    vars = inventoryvar + backordervar + quantityvar + dependentdemandvar
                    coeff = [-1] * len(inventoryvar) \
                            + [1] * len(backordervar) \
                            + quantityvarceoff \
                            + dependentdemandvarcoeff

                    if len(vars) > 0:
                        self.Cplex.linear_constraints.add( lin_expr=[cplex.SparsePair(vars, coeff)],
                                                           senses=["E"],
                                                           rhs=righthandside )


    # This function creates the  indicator constraint to se the production variable to 1 when a positive quantity is produce
    def CreateProductionConstraints( self ):
        AlreadyAdded = [ [ False for v in range( self.GetNrQuantityVariable() ) ]  for w in range( self.GetNrProductionVariable() ) ]

        for t in self.Instance.TimeBucketSet:
            for p in self.Instance.ProductSet:
                for w in self.ScenarioSet:
                    indexQ = self.GetIndexQuantityVariable(p, t, w)
                    indexP = self.GetIndexProductionVariable(p, t, w) - self.GetStartProductionVariable()
                    if not AlreadyAdded[indexP][indexQ]:# or self.Model == MIPSolver.ModelYFix or self.Model == MIPSolver.ModelYQFix:
                        AlreadyAdded[indexP][indexQ] = True
                        ic_dict = {}
                        ic_dict["lin_expr"] = cplex.SparsePair(ind=[indexQ],
                                                               val=[1.0])
                        ic_dict["rhs"] = 0.0
                        ic_dict["sense"] = "E"
                        ic_dict["indvar"] = self.GetIndexProductionVariable(p, t, w)
                        ic_dict["complemented"] = 1
                        self.Cplex.indicator_constraints.add( **ic_dict )


    # This function creates the Capacity constraint
    def CreateCapacityConstraints( self ):

        secenarioset = [0]
        if self.Model <> MIPSolver.ModelYQFix :
            secenarioset = self.ScenarioSet
        # Capacity constraint
        if self.Instance.NrResource > 0:
            for k in range( self.Instance.NrResource ):
                for t in self.Instance.TimeBucketSet:
                    for w in secenarioset:
                        vars = [ self.GetIndexQuantityVariable(p, t, w) for p in self.Instance.ProductSet ]
                        coeff = [ self.Instance.ProcessingTime[p][k] for p in self.Instance.ProductSet ]
                        righthandside = [ self.Instance.Capacity[k] ]
                        # PrintConstraint( vars, coeff, righthandside )
                        self.Cplex.linear_constraints.add( lin_expr=[cplex.SparsePair(vars, coeff)],
                                                           senses=["L"],
                                                           rhs=righthandside )

    # This function creates the non anticipitativity constraint
    def CreateNonanticipativityConstraints( self ):
        considertimebucket = self.Instance.TimeBucketSet;
         # Non anticipitativity only for period 1 for now
        for w1 in self.ScenarioSet:
            for w2 in range(w1 + 1, self.NrScenario):
                for p in self.Instance.ProductSet:
                    for t in considertimebucket:
                        if self.Scenarios[w1].QuanitityVariable[t][p] == self.Scenarios[w2].QuanitityVariable[t][p]:
                            if not ( self.Model == MIPSolver.ModelYQFix ):
                                vars = [ self.GetIndexQuantityVariable(p, t, w1), self.GetIndexQuantityVariable(p, t, w2) ]
                                coeff = [1.0, -1.0]
                                righthandside = [0.0]

                                # PrintConstraint( vars, coeff, righthandside )
                                self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                         senses=["E"],
                                                         rhs=righthandside)

                            if not ( self.Model == MIPSolver.ModelYQFix or self.Model == MIPSolver.ModelYFix ):
                                vars = [ self.GetIndexProductionVariable(p, t, w1), self.GetIndexProductionVariable(p, t, w2) ]
                                coeff = [1.0, -1.0]
                                righthandside = [0.0]

                                # PrintConstraint( vars, coeff, righthandside )
                                self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                                  senses=["E"],
                                                                  rhs=righthandside)

                            vars = [ self.GetIndexBackorderVariable(p, t, w1), self.GetIndexBackorderVariable(p, t, w2) ]
                            coeff = [1.0, -1.0]
                            righthandside = [0.0]
                            # PrintConstraint( vars, coeff, righthandside )
                            self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                     senses=["E"],
                                                     rhs=righthandside)

                            vars = [ self.GetIndexInventoryVariable(p, t, w1), self.GetIndexInventoryVariable(p, t, w2) ]
                            coeff = [1.0, -1.0]
                            righthandside = [0.0]
                            # PrintConstraint( vars, coeff, righthandside )
                            self.Cplex.linear_constraints.add(  lin_expr=[cplex.SparsePair(vars, coeff)],
                                                                senses=["E"],
                                                                rhs=righthandside )

    # Define the constraint of the model
    def CreateConstraints( self ):
        self.CreateFlowConstraints()
        self.CreateProductionConstraints()
        self.CreateCapacityConstraints()
        if self.UseNonAnticipativity and not self.UseImplicitNonAnticipativity:
            self.CreateNonanticipativityConstraints( )
        if self.EvaluateSolution:
            self.CreateCopyGivenSolutionConstraints( )

    #This function build the CPLEX model
    def BuildModel( self ):
        #Create the variabbles and constraints
        self.CreateVariable()
        self.CreateConstraints()

    #This function set the parameter of CPLEX, run Cplex, and return a solution
    def Solve( self ):
        start_time = time.time()
        # Our aim is to minimize cost.
        self.Cplex.objective.set_sense(self.Cplex.objective.sense.minimize)
        if self.Debug:
            self.Cplex.write("mrp.lp")
        else:
            #name = "mrp_log%r_%r_%r" % ( self.Instance.InstanceName, self.Model, self.DemandScenarioTree.Seed )
            self.Cplex.set_log_stream( None )
            self.Cplex.set_results_stream( None )
            self.Cplex.set_warning_stream( None )
            self.Cplex.set_error_stream( None )

        # tune the paramters
        self.Cplex.parameters.timelimit.set(3600.0)
        self.Cplex.parameters.mip.limits.treememory.set(7000.0)
        self.Cplex.parameters.threads.set(1)

        end_modeling = time.time();

        #solve the problem
        self.Cplex.solve()

        buildtime = end_modeling - start_time;
        solvetime = time.time() - end_modeling;

        # Handle the results
        sol = self.Cplex.solution
        if sol.is_primal_feasible():
            if self.Debug:
                sol.write("mrpsolution.sol")

            objvalue = sol.get_objective_value()
            array = [ self.GetIndexQuantityVariable(p, t, w)
                     for p in self.Instance.ProductSet for t in self.Instance.TimeBucketSet for w in self.ScenarioSet ];
            solquantity = sol.get_values(array)
            solquantity = np.array(solquantity, np.float32).reshape(
                                    (self.Instance.NrProduct, self.Instance.NrTimeBucket * self.NrScenario))

            array = [self.GetIndexProductionVariable(p, t, w)
                     for p in self.Instance.ProductSet for t in self.Instance.TimeBucketSet for w in self.ScenarioSet]
            solproduction = sol.get_values(array)
            solproduction = np.array(solproduction, np.float32).reshape(
                (self.Instance.NrProduct, self.Instance.NrTimeBucket * self.NrScenario))
            array = [self.GetIndexInventoryVariable(p, t, w)
                     for p in self.Instance.ProductSet for t in self.Instance.TimeBucketSet for w in self.ScenarioSet]
            solinventory = sol.get_values(array)
            solinventory = np.array(solinventory, np.float32).reshape(
                (self.Instance.NrProduct, self.Instance.NrTimeBucket * self.NrScenario))

            array = [self.GetIndexBackorderVariable(p, t, w)
                     for p in self.Instance.ProductWithExternalDemand for t in self.Instance.TimeBucketSet for w in self.ScenarioSet]
            solbackorder = sol.get_values(array)
            solbackorder = np.array(solbackorder, np.float32).reshape(( len( self.Instance.ProductWithExternalDemand ),
                                                                        self.Instance.NrTimeBucket * self.NrScenario))

            Solution = MRPSolution( self.Instance, self,  solquantity, solproduction, solinventory, solbackorder)

            self.SolveInfo = [ self.Instance.InstanceName,
                    self.Model,

                    objvalue,
                    Solution.TotalCost,
                    sol.status[sol.get_status()],
                    buildtime,
                    solvetime,
                    sol.MIP.get_mip_relative_gap(),
                    sol.progress.get_num_iterations(),
                    sol.progress.get_num_nodes_processed(),
                    sol.MIP.get_incumbent_node(),
                    self.Cplex.variables.get_num(),
                    self.Cplex.linear_constraints.get_num(),

                    Solution.InventoryCost,
                    Solution.BackOrderCost,
                    Solution.SetupCost,
                    self.Instance.NrLevel,
                    self.Instance.NrProduct,
                    self.Instance.NrTimeBucket,
                    self.DemandScenarioTree.Seed,
                    self.NrScenario,
                    self.Instance.MaxLeadTime,
                    self.Instance.BranchingStrategy,
                    self.DemandScenarioTree.Distribution]



            return Solution
        else:
            print("No solution available.")

    #This function print the scenario of the instance in an excel file
    def PrintScenarioToFile( self ):
        writer = pd.ExcelWriter( "./Instances/" + self.Instance.InstanceName + "_Scenario.xlsx",
                                        engine='openpyxl' )
        for s in self.Scenarios:
            s.PrintScenarioToExcel( writer )
        writer.save()
    #    self.DemandScenarioTree.SaveInFile( scenarionr )