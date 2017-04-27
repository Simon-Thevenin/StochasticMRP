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
#pass Debug to true to get some debug information printed
Debug = True
Instance = MRPInstance()
AverageInstance = MRPInstance()
M = cplex.infinity
#If UseNonAnticipativity is set to true a variable per scenario is generated, otherwise only the required variable a created.
UseNonAnticipativity = False
#ActuallyUseAnticipativity is set to False to compute the EPVI, otherwise, it is set to true to add the non anticipativity constraints
ActuallyUseAnticipativity = False
#PrintScenarios is set to true if the scenario tree is printed in a file, this is usefull if the same scenario must be reloaded in a ater test.
PrintScenarios = False
ScenarioNr = -1
#The attribut model refers to the model which is solved. It can take values in "Average, YQFix, YFix,_Fix"
# which indicates that the avergae model is solve, the Variable Y and Q are fixed at the begining of the planning horizon, only Y is fix, or everything can change at each period
Model = "Average"

ComputeAverageSolution = False

#When a solution is obtained, it is recorded in Solution. This is used to compute VSS for instance.
Solution = None
#Evaluate solution is true, the solution in the variable "GivenQuantities" is given to CPLEX to compute the associated costs
EvaluateSolution = False
FixUntilTime = 0
GivenQuantities =[]
VSS = []
#This function returns the name of the quantity variable for product p and time t
def GetNameQuantityVariable( p, t, w ):
    scenarioindex = -1;
    if Model == "YQFix":
        scenarioindex = 0
    elif UseNonAnticipativity:
            scenarioindex = w
    else :
            scenarioindex = Instance.Scenarios[w].QuanitityVariable[t][p]
    #return "quantity_prod_time_scenar_%d_%d_%d" % (p, t, scenarioindex );
    return "q_p_t_s_%d_%d_%d" % (p, t, scenarioindex );

#This function returns the name of the inventory variable for product p and time t
def GetNameInventoryVariable( p, t, w ):
    scenarioindex = -1;
    if UseNonAnticipativity :
        scenarioindex = w
    else :
        scenarioindex = Instance.Scenarios[w].InventoryVariable[t][p]
    #return "inventory_prod_time_scenar_%d_%d_%d" % ( p, t, scenarioindex )
    return "i_%d_%d_%d" % ( p, t, scenarioindex )

#This function returns the name of the production variable for product p and time t
def GetNameProductionVariable( p, t,w ):
    scenarioindex = -1;
    if UseNonAnticipativity:
        if Model == "YQFix" or Model == "YFix":
            scenarioindex = 0
        else:
            scenarioindex = w
    else :
        scenarioindex = Instance.Scenarios[w].ProductionVariable[t][p]
    #return "production_prod_time_scenar_%d_%d_%d" % ( p, t, scenarioindex )
    return "p_%d_%d_%d" % ( p, t, scenarioindex )

#This function returns the name of the backorder variable for product p and time t
def GetNameBackOrderQuantity( p, t, w ):
    scenarioindex = -1;
    if UseNonAnticipativity :
        scenarioindex = w
    else:
        scenarioindex = Instance.Scenarios[w].BackOrderVariable[t][p]
    #return "backorder_prod_time_scenar_%d_%d_%d" % ( p, t, scenarioindex )
    return "b_%d_%d_%d" % ( p, t, scenarioindex )

#the function GetIndexQuantityVariable returns the index of the variable Q_{p, t}. Quantity of product p produced at time t
def GetIndexQuantityVariable( p, t, w ):
    if Model == "YQFix":
        return GetStartQuantityVariable() + t  * Instance.NrProduct + p
    elif UseNonAnticipativity:
         return GetStartQuantityVariable() + w * ( Instance.NrTimeBucket ) * Instance.NrProduct + t  * Instance.NrProduct + p
    else :
        return Instance.Scenarios[ w ].QuanitityVariable[t][p];

#the function GetIndexInventoryVariable returns the index of the variable I_{p, t}. Inventory of product p produced at time t
def GetIndexInventoryVariable( p, t, w ):
    if UseNonAnticipativity:
        return GetStartInventoryVariable() + w * Instance.NrTimeBucket * Instance.NrProduct + t * Instance.NrProduct + p
    else :
        return Instance.Scenarios[ w ].InventoryVariable[t][p];

#the function GetIndexProductionVariable returns the index of the variable Y_{p, t, w}.
# This variable equal to one is product p is produced at time t, 0 otherwise
def GetIndexProductionVariable( p, t, w ):
    if Model == "YQFix" or Model == "YFix" :
        return GetStartProdustionVariable()  + t  * Instance.NrProduct + p
    elif UseNonAnticipativity :
        return Instance.StartProdustionVariable + w * Instance.NrTimeBucket * Instance.NrProduct + t * Instance.NrProduct + p
    else:
        return Instance.Scenarios[w].ProductionVariable[t][p];

#the function GetIndexBackorderVariable returns the index of the variable B_{p, t}. Quantity of product p produced backordered at time t
def GetIndexBackorderVariable( p, t, w ):
    if UseNonAnticipativity :
        return GetStartBackorderVariable() + w * Instance.NrTimeBucket * Instance.NrProduct + t * Instance.NrProduct + p
    else:
        return Instance.Scenarios[ w ].BackOrderVariable[ t ][ p ];


def GetStartBackorderVariable( ):
    if Model == "YQFix": return Instance.StartBackorderVariableYQFix
    if Model == "YFix": return Instance.StartBackorderVariableYFix
    if Model == "_Fix": return Instance.StartBackorderVariable

def GetStartProdustionVariable( ):
    if Model == "YQFix": return Instance.StartProdustionVariableYQFix
    if Model == "YFix": return Instance.StartProdustionVariableYFix
    if Model == "_Fix": return Instance.StartProductionVariable

def GetStartInventoryVariable( ):
    if Model == "YQFix": return Instance.StartInventoryVariableYQFix
    if Model == "YFix": return Instance.StartInventoryVariableYFix
    if Model == "_Fix": return Instance.StartInventoryVariable

def GetStartQuantityVariable( ):
    if Model == "YQFix": return Instance.StartQuantityVariablYQFix
    if Model == "YFix": return Instance.StartQuantityVariablYFix
    if Model == "_Fix": return Instance.StartQuantityVariable


#This function define the variables
def CreateVariable(c):
    #Define the cost vector for each variable. As the numbber of variable changes when non anticipativity is used the cost are created differently
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

    if UseNonAnticipativity :
        inventorycosts = [Instance.InventoryCosts[p] * Instance.Scenarios[w].Probability * math.pow( Instance.Gamma, t)
                            for w in Instance.ScenarioSet for t in Instance.TimeBucketSet for p in Instance.ProductSet]
        setupcosts = [Instance.SetupCosts[p] * Instance.Scenarios[w].Probability * math.pow( Instance.Gamma, t)
                      for w in Instance.ScenarioSet for t in Instance.TimeBucketSet for p in Instance.ProductSet]
        backordercosts = [Instance.BackorderCosts[p] * Instance.Scenarios[w].Probability * math.pow( Instance.Gamma, t)
                      for w in Instance.ScenarioSet for t in Instance.TimeBucketSet for p in Instance.ProductSet]
        nrinventoryvariable = Instance.NrInventoryVariable;
        nrbackordervariable = Instance.NrBackorderVariable;
        nrproductionvariable = Instance.NrProductionVariable;
        nrquantityvariable = Instance.NrQuantiyVariables;
        if Model == "YQFix":
            nrquantityvariable = Instance.NrQuantiyVariablesYQFix
            nrproductionvariable = Instance.NrProductionVariablesYQFix
        if Model == "YFix":
            nrproductionvariable = Instance.NrProductionVariablesYFix

        if Model == "YQFix" or Model == "YFix":
            setupcosts = [Instance.SetupCosts[p] * sum( Instance.Scenarios[w].Probability for w in Instance.ScenarioSet ) * math.pow( Instance.Gamma, t)
                          for t in Instance.TimeBucketSet for p in Instance.ProductSet]

    #Define only the required variables
    else :
        nrquantityvariable = Instance.NrQuantiyVariablesWithoutNonAnticipativity
        nrinventoryvariable = Instance.NrInventoryVariableWithoutNonAnticipativity
        nrbackordervariable = Instance.NrBackorderVariableWithoutNonAnticipativity
        nrproductionvariable = Instance.NrProductionVariableWithoutNonAnticipativity
        inventorycosts = [ 0 ] * nrinventoryvariable
        setupcosts = [ 0 ] * nrproductionvariable
        backordercosts = [ 0 ] * nrbackordervariable
        for w in Instance.ScenarioSet :
            for t in Instance.TimeBucketSet :
                for p in Instance.ProductSet :
                    #Add the cost of the cariable representing multiple scenarios
                    inventorycostindex =  Instance.Scenarios[ w ].InventoryVariable[ t ][ p ] - Instance.StartInventoryVariableWithoutNonAnticipativity
                    setupcostindex = Instance.Scenarios[w].ProductionVariable[t][p] - Instance.StartProdustionVariableWithoutNonAnticipativity
                    backordercostindex = Instance.Scenarios[w].BackOrderVariable[t][p] - Instance.StartBackorderVariableWithoutNonAnticipativity
                    inventorycosts[ inventorycostindex ] =  inventorycosts[ inventorycostindex ]\
                        + Instance.InventoryCosts[p] * Instance.Scenarios[w].Probability * math.pow( Instance.Gamma, t)
                    setupcosts[ setupcostindex ] = setupcosts[ setupcostindex ] \
                        + Instance.SetupCosts[p] * Instance.Scenarios[w].Probability * math.pow( Instance.Gamma, t)
                    backordercosts[ backordercostindex ] = backordercosts[ backordercostindex ] \
                        + Instance.BackorderCosts[p] * Instance.Scenarios[w].Probability * math.pow( Instance.Gamma, t)

     # the variable quantity_prod_time_scenario_p_t_w indicated the quantity of product p produced at time t in scneario w
    c.variables.add( obj = [ 0.0 ] * nrquantityvariable,
                      lb = [ 0.0 ] * nrquantityvariable,
                      ub = [ M ] * nrquantityvariable)

    # the variable inventory_prod_time_scenario_p_t_w indicated the inventory level of product p at time t in scneario w
    c.variables.add( obj = inventorycosts,
                     lb = [ 0.0 ] * nrinventoryvariable,
                     ub = [ M ] * nrinventoryvariable )

    # the variable production_prod_time_scenario_p_t_w equals 1 if a lot of product p is produced at time t in scneario w
    c.variables.add( obj = setupcosts,
                     lb=[ 0.0 ] * nrproductionvariable,
                     ub=[ 1.0 ] * nrproductionvariable )

    # the variable backorder_prod_time_scenario_p_t_w gives the amount of product p backordered at time t in scneario w
    c.variables.add( obj = backordercosts,
                     lb = [ 0.0 ] * nrbackordervariable,
                     ub = [ M ] * nrbackordervariable )

    #Define the variable name.
    #Usefull for debuging purpose. Otherwise, disable it, it is time consuming.
    if Debug :
        quantityvars = []
        inventoryvars = []
        productionvars = []
        backordervars = []
        for p in  Instance.ProductSet:
            for t in Instance.TimeBucketSet:
                for w in Instance.ScenarioSet:
                    quantityvars.append( ( GetIndexQuantityVariable( p, t, w ), GetNameQuantityVariable( p, t, w ) ) )
                    productionvars.append( ( GetIndexProductionVariable( p, t, w ), GetNameProductionVariable( p, t, w ) ) )
                    inventoryvars.append( ( GetIndexInventoryVariable( p, t, w ), GetNameInventoryVariable( p, t, w ) ) )
                    backordervars.append( ( GetIndexBackorderVariable( p, t, w ), GetNameBackOrderQuantity( p, t, w ) ) )

        quantityvars = list( set( quantityvars ) )
        productionvars = list( set( productionvars ) )
        inventoryvars = list( set( inventoryvars ) )
        backordervars = list( set( backordervars ) )
        varnames = quantityvars + inventoryvars + productionvars + backordervars
        c.variables.set_names( varnames )

#Print a constraint (usefull for debugging)
def PrintConstraint( vars, coeff, righthandside ) :
    print "Add the following constraint:"
    print "----------------Var-----------------------------"
    print vars
    print "----------------Coeff-----------------------------"
    print coeff
    print "----------------Rhs-----------------------------"
    print righthandside


#To evaluate the solution obtained with the expected demand, the solution quanitity are constraint to be equal to some values
# This function creates the Capacity constraint
def CreateCopyGivenSolutionConstraints(c):
    AlreadyAdded = [ False for v in range( Instance.NrQuantiyVariables ) ]

    # Capacity constraint
    for p in Instance.ProductSet:
        for t in Instance.TimeBucketSet:
            for w in Instance.ScenarioSet:
                indexvariable = GetIndexQuantityVariable(p, t, w)
                if Instance.HasExternalDemand[p] \
                    and not AlreadyAdded[indexvariable] \
                    and ( t <= FixUntilTime ):
                    vars = [ indexvariable ]
                    AlreadyAdded[ indexvariable ] = True
                    coeff = [ 1.0 ]
                    righthandside = [ round( GivenQuantities[p][t], 2)   ]
                    #PrintConstraint( vars, coeff, righthandside )
                    c.linear_constraints.add( lin_expr=[cplex.SparsePair(vars, coeff)],
                                              senses=["E"],
                                              rhs=righthandside )

               # c.variables.set_lower_bounds( GetIndexQuantityVariable(p, t, w), GivenQuantities[p][t] )
               # c.variables.set_upper_bounds(GetIndexQuantityVariable(p, t, w), GivenQuantities[p][t])

# Demand and materials requirement: set the value of the invetory level and backorder quantity according to
#  the quantities produced and the demand
def CreateFlowConstraints(c):
     expressionstoadd = []
     sensestoadd = []
     rigthandsidestoadd = []
     for p in Instance.ProductSet:
       for w in Instance.ScenarioSet:
          #To speed up the creation of the model, only the variable and coffectiant which were not in the previous constraints are added (See the model definition)
          righthandside = [ -1 * Instance.StartingInventories[ p ] ]
          quantityvar = []
          quantityvarceoff = []
          dependentdemandvar= []
          dependentdemandvarcoeff =[]
          for t in Instance.TimeBucketSet:
                backordervar = []
                righthandside[ 0 ] = righthandside[ 0 ] +  Instance.Scenarios[ w ].Demands[ t ][p]
                if  Instance.HasExternalDemand[ p ]:
                    backordervar = [ GetIndexBackorderVariable( p, t, w ) ]

                if  t - Instance.Leadtimes[ p ] >= 0 :
                    quantityvar = quantityvar + [GetIndexQuantityVariable( p,  t - Instance.Leadtimes[ p ], w )]
                    quantityvarceoff = quantityvarceoff + [1]

                dependentdemandvar = dependentdemandvar + [ GetIndexQuantityVariable( q, t, w ) for q in Instance.RequieredProduct[p] ]
                dependentdemandvarcoeff = dependentdemandvarcoeff + [-1* Instance.Requirements[ q ][ p ] for q in Instance.RequieredProduct[p]  ]
                inventoryvar = [ GetIndexInventoryVariable( p, t, w ) ]

                vars = inventoryvar + backordervar +  quantityvar + dependentdemandvar
                coeff = [ -1 ] * len( inventoryvar ) \
                        + [ 1 ] * len( backordervar ) \
                        + quantityvarceoff \
                        + dependentdemandvarcoeff

                if len( vars ) > 0 :
                     c.linear_constraints.add( lin_expr = [ cplex.SparsePair( vars, coeff ) ],
                                              senses = [ "E" ],
                                              rhs = righthandside )

#This function creates the  indicator constraint to se the production variable to 1 when a positive quantity is produce
def CreateProductionConstraints(c):
    AlreadyAdded = [False for v in range(Instance.NrQuantiyVariables)]

    for t in Instance.TimeBucketSet:
        for p in Instance.ProductSet:
            for w in Instance.ScenarioSet:
                indexQ =GetIndexQuantityVariable(p, t, w)
                if not AlreadyAdded[indexQ] or Model == "YFix" or Model == "YQFix":
                    AlreadyAdded[indexQ] = True
                    ic_dict = {}
                    ic_dict["lin_expr"] = cplex.SparsePair(ind=[indexQ],
                                                           val=[1.0])
                    ic_dict["rhs"] = 0.0
                    ic_dict["sense"] = "E"
                    ic_dict["indvar"] = GetIndexProductionVariable(p, t, w)
                    ic_dict["complemented"] = 1
                    c.indicator_constraints.add(**ic_dict)

# This function creates the Capacity constraint
def CreateCapacityConstraints(c):
    # Capacity constraint
    if Instance.NrResource > 0:
        for k in range(Instance.NrResource):
            for t in Instance.TimeBucketSet:
                for w in Instance.ScenarioSet:
                    vars = [GetIndexQuantityVariable(p, t, w) for p in Instance.ProductSet]
                    coeff = [Instance.ProcessingTime[p][k] for p in Instance.ProductSet]
                    righthandside = [ Instance.Capacity[k] ]
                    # PrintConstraint( vars, coeff, righthandside )
                    c.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                             senses=["L"],
                                             rhs=righthandside)


# This function creates the non anticipitativity constraint
def CreateNonanticipativityConstraints( c ):
    considertimebucket = Instance.TimeBucketSet;
   
    #Non anticipitativity only for period 1 for now
    for w1 in Instance.ScenarioSet:
         for w2 in range( w1 +1, Instance.NrScenario):
             for p in Instance.ProductSet:
                 for t in considertimebucket:
                      if  Instance.Scenarios[ w1 ].QuanitityVariable[ t ][ p ] == Instance.Scenarios[ w2 ].QuanitityVariable[ t ][ p ] :
                           if not ( model == 'YQFix' ):
                               vars = [ GetIndexQuantityVariable( p, t, w1 ), GetIndexQuantityVariable( p, t, w2 ) ]
                               coeff = [ 1.0, -1.0 ]
                               righthandside = [ 0.0 ]

                               # PrintConstraint( vars, coeff, righthandside )
                               c.linear_constraints.add( lin_expr = [cplex.SparsePair(vars, coeff)],
                                                           senses=["E"],
                                                           rhs=righthandside )

                           if not (model == 'YQFix' or model == 'YFix'):
                               vars = [ GetIndexProductionVariable(p, t, w1), GetIndexProductionVariable(p, t, w2)]
                               coeff = [ 1.0, -1.0 ]
                               righthandside = [ 0.0 ]

                               # PrintConstraint( vars, coeff, righthandside )
                               c.linear_constraints.add(lin_expr = [cplex.SparsePair(vars, coeff)],
                                                          senses=["E"],
                                                          rhs=righthandside)

                           vars = [GetIndexBackorderVariable(p, t, w1), GetIndexBackorderVariable(p, t, w2)]
                           coeff = [ 1.0, -1.0 ]
                           righthandside = [ 0.0 ]
                           # PrintConstraint( vars, coeff, righthandside )
                           c.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                      senses=["E"],
                                                      rhs=righthandside)

                           vars = [GetIndexInventoryVariable(p, t, w1), GetIndexInventoryVariable(p, t, w2)]
                           coeff = [ 1.0, -1.0 ]
                           righthandside = [ 0.0 ]
                           # PrintConstraint( vars, coeff, righthandside )
                           c.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                      senses=["E"],
                                                      rhs=righthandside)


#Define the constraint of the model
def CreateConstraints(c):
     CreateFlowConstraints( c )
     CreateProductionConstraints( c )
     CreateCapacityConstraints( c )
     if UseNonAnticipativity and ActuallyUseAnticipativity:
        CreateNonanticipativityConstraints( c )
     if EvaluateSolution :
         CreateCopyGivenSolutionConstraints( c )

#This function creates the CPLEX model and solves it.
def MRP():
    start_time = time.time()
    if Debug:
        Instance.PrintInstance()
    if PrintScenarios:
        Instance.PrintScenarioToFile( ScenarioNr )
    print "Start to model in Cplex";
    c = cplex.Cplex()

    #Create the variabbles and constraints
    CreateVariable(c)
    CreateConstraints(c)

    # Our aim is to minimize cost.
    c.objective.set_sense( c.objective.sense.minimize )
    if Debug:
        c.write("mrp.lp")
    else:
        c.set_log_stream( "mrp_log%r_%r_%r"%(Instance.InstanceName,  Model,  Instance.NrScenarioPerBranch ))
        c.set_results_stream( "mrp_log%r_%r_%r"%(Instance.InstanceName,  Model,  Instance.NrScenarioPerBranch ))
        c.set_warning_stream( "mrp_log%r_%r_%r"%(Instance.InstanceName,  Model,  Instance.NrScenarioPerBranch ))
        c.set_error_stream( "mrp_log%r_%r_%r"%(Instance.InstanceName,  Model,  Instance.NrScenarioPerBranch ))

    #tune the paramters
    c.parameters.timelimit.set( 3600.0 )
    c.parameters.mip.limits.treememory.set( 7000.0 )
    #c.parameters.mip.tolerances.mipgap.set( 0.05 )
    c.parameters.threads.set( 1 )

    print "Start to solve instance %s with Cplex"% Instance.InstanceName;
    end_modeling = time.time();
    c.solve()
    buildtime =   end_modeling - start_time;
    solvetime =  time.time() - end_modeling ;
    sol = c.solution



    #Handle the results
    if sol.is_primal_feasible():
        if Debug:
            sol.write("mrpsolution.sol")

        objvalue = sol.get_objective_value()
        array =  [  GetIndexQuantityVariable( p, t, w )
                    for p in Instance.ProductSet for t in Instance.TimeBucketSet  for w in  Instance.ScenarioSet];
        solquantity =   sol.get_values( array )
        solquantity = np.array(solquantity, np.float32).reshape(
                                     (Instance.NrProduct, Instance.NrTimeBucket * Instance.NrScenario))


        array = [ GetIndexProductionVariable( p, t, w )
                    for p in Instance.ProductSet for t in Instance.TimeBucketSet  for w in  Instance.ScenarioSet]
        solproduction = sol.get_values( array )
        solproduction = np.array( solproduction,np.float32 ).reshape( ( Instance.NrProduct, Instance.NrTimeBucket  * Instance.NrScenario  ) )
        array = [ GetIndexInventoryVariable( p, t, w )
                  for p in Instance.ProductSet   for t in Instance.TimeBucketSet  for w in  Instance.ScenarioSet ]
        solinventory = sol.get_values( array )
        solinventory =  np.array( solinventory,np.float32 ).reshape( ( Instance.NrProduct, Instance.NrTimeBucket * Instance.NrScenario ) )

        array = [ GetIndexBackorderVariable( p, t, w )
                  for p in Instance.ProductSet for t in Instance.TimeBucketSet for w in Instance.ScenarioSet ]
        solbackorder = sol.get_values(array)
        solbackorder = np.array(solbackorder, np.float32).reshape((Instance.NrProduct, Instance.NrTimeBucket * Instance.NrScenario))  # array # tempmatinv.reshape(  (Instance.NrScenario, Instance.NrProduct, Instance.NrTimeBucket) ) # zip(*[iter(solinventory)] * Instance.NrTimeBucket )

        Solution = MRPSolution( Instance, solquantity, solproduction, solinventory, solbackorder )
        result = Solution.TotalCost, solquantity.tolist()

        if Debug:
            Solution.Print()

            description = "%r_%r" % ( Model, Instance.BranchingStrategy )

         #   Solution.PrintToExcel( description )

        data =  [ Instance.InstanceName,
                  Model,
                  objvalue,
                  Solution.TotalCost,
                  sol.status[ sol.get_status() ],
                  buildtime,
                  solvetime,
                  sol.MIP.get_mip_relative_gap(),
                  sol.progress.get_num_iterations(),
                  sol.progress.get_num_nodes_processed(),
                  sol.MIP.get_incumbent_node(),
                  c.variables.get_num(),
                  c.linear_constraints.get_num(),
                  Solution.InventoryCost,
                  Solution.BackOrderCost,
                  Solution.SetupCost,
                  Instance.NrLevel,
                  Instance.NrProduct,
                  Instance.NrTimeBucket,
                  Instance.NrScenario,
                  Instance.MaxLeadTime,
                  Instance.BranchingStrategy ]
        if not EvaluateSolution:
            d = datetime.now()
            date = d.strftime('%m_%d_%Y_%H:%M:%S')
            myfile = open(r'./Test/TestResult_%s_%r_%s_%s.csv' % (Instance.InstanceName, Instance.BranchingStrategy, Model, date), 'wb')
            wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
            wr.writerow(data)

    else:
        print("No solution available.")

    return result


def ComputeVSS():
     # Compute the average value of the demand
    global Instance
    global FixUntilTime
    global EvaluateSolution
    global GivenQuantities
    SavedInstance = Instance

    Instance.PrintInstance()
    averagedemand = [ ( sum ( Instance.Scenarios[w].Demands[t][p] for w in Instance.ScenarioSet ) / Instance.NrScenario )
                      for t in Instance.TimeBucketSet for p in Instance.ProductSet ]
    name = Instance.InstanceName
    Instance = MRPInstance()
    Instance.ReadInstanceFromExelFile( name )
    Instance.AverageDemand = averagedemand
    Instance.Average = True
    Instance.NrScenarioPerBranch = 1
    Instance.ComputeInstanceData()

    cost, GivenQuantities = MRP()

    Instance =  SavedInstance
    EvaluateSolution = True
    VSS = [ -1 for t in Instance.TimeBucketSet]
    for t in Instance.TimeBucketSet:
         FixUntilTime = t
         solutionofVSS, qties = MRP()
         VSS[t] = solutionofVSS

    Instance = SavedInstance
    print "VSS: %r" % VSS

    d = datetime.now()
    date = d.strftime('%m_%d_%Y_%H:%M:%S')
    myfile = open(r'./Test/TestResultVSS_%s_%r_%s_%s.csv' % (Instance.InstanceName, Instance.BranchingStrategy, Model, date),
                  'wb')
    wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
    wr.writerow(VSS)


#Save the scenario tree in a file
def ReadCompleteInstanceFromFile( name, nrbranch ):
        result = None
        filepath = '/tmp/thesim/%s_%r.pkl'%( name, nrbranch )

        try:
            with open(filepath, 'rb') as input:
                result = pickle.load(input)
            return result
        except:
            print "file %r not found" % (filepath)



if __name__ == "__main__":

    instancename = ""
    try: 
        if len(sys.argv) == 1:
            instancename = raw_input("Enter the number (in [01;38]) of the instance to solve:")
        else:
            script, instancename, nrbranchasstring, model, scenarionr = sys.argv

        nrbranch = int(nrbranchasstring)

        Model = model
        ScenarioNr = scenarionr
        Instance.ScenarioNr = scenarionr
        UseNonAnticipativity = True
        ActuallyUseAnticipativity = True
        Instance.Average = False
        Instance.BranchingStrategy = nrbranch
        Instance.LoadScenarioFromFile = True
        PrintScenarios = False
        Instance.ReadInstanceFromExelFile( instancename )
        #Instance.ReadFromFile( instancename )
        #Instance.PrintInstance()
        #Instance.SaveCompleteInstanceInFile()
        #Instance.DefineAsSuperSmallIntance()
        #Instance.SaveCompleteInstanceInExelFile()
    except KeyError:
        print "This instance does not exist. Instance should be in 01, 02, 03, ... , 38"
      
    MRP()
    ComputeVSS()

   #  Method = "Average"
   #  Instance = MRPInstance()
   #  Instance.LoadScenarioFromFile = False
   #  PrintScenarios = False
   #  UseNonAnticipativity = False
   #  ActuallyUseAnticipativity = False
   #  Instance=ReadCompleteInstanceFromFile( instancename ,nrbranch);
   #  Instance.Average = True
   #  Instance.NrScenarioPerBranch = 1
   #  Instance.ComputeInstanceData();
   #  #Instance.ReadFromFile(instancename)
   #  #Instance.DefineAsSuperSmallIntance()
   #  solutionofaverage = MRP()
   #  #
   #  Method = "Average_Solution_In_Multi-stages"
   #  Instance = MRPInstance()
   #  Instance.Average = False
   #  Instance.NrScenarioPerBranch = nrbranch
   #  EvaluateSolution = True
   #  Instance.LoadScenarioFromFile = True
   #  PrintScenarios = False
   #  UseNonAnticipativity = False
   #  ActuallyUseAnticipativity = False
   #  FixOnlyFirstPeriod = False
   #  Instance=ReadCompleteInstanceFromFile( instancename ,nrbranch);
   # # Instance.ReadFromFile( instancename )
   #  #Instance.DefineAsSuperSmallIntance()
   #  GivenQuantities = solutionofaverage
   #  MRP()
   #
   #  Method = "First_Period_Average_In_Multi-stages"
   #  Instance = MRPInstance()
   #  Instance.Average = False
   #  Instance.NrScenarioPerBranch = nrbranch
   #  EvaluateSolution = True
   #  Instance.LoadScenarioFromFile = True
   #  PrintScenarios = False
   #  UseNonAnticipativity = False
   #  ActuallyUseAnticipativity = False
   #  FixOnlyFirstPeriod = True
   #  Instance=ReadCompleteInstanceFromFile(instancename,nrbranch);
   #  #Instance.ReadFromFile( instancename )
   #  #Instance.DefineAsSuperSmallIntance()
   #  GivenQuantities = solutionofaverage
   #  MRP()
   #
   #  Method = "Knowledge_Of_Future"
   #  Instance = MRPInstance()
   #  Instance.Average = False
   #  Instance.NrScenarioPerBranch = nrbranch
   #  EvaluateSolution = False
   #  Instance.LoadScenarioFromFile = True
   #  PrintScenarios = False
   #  UseNonAnticipativity = True
   #  ActuallyUseAnticipativity = False
   #  Instance=ReadCompleteInstanceFromFile(instancename,nrbranch);
   #  #Instance.ReadFromFile( instancename )
   #  #Instance.DefineAsSuperSmallIntance()
   #  MRP()
   #
   #
   #  Method = "One-stage"
   #  Instance = MRPInstance()
   #  Instance.Average = False
   #  Instance.NrScenarioPerBranch = nrbranch
   #  EvaluateSolution = False
   #  Instance.LoadScenarioFromFile = True
   #  PrintScenarios = False
   #  UseNonAnticipativity = True
   #  ActuallyUseAnticipativity = False
   #  Instance=ReadCompleteInstanceFromFile(instancename,nrbranch);
   #  #Instance.ReadFromFile( instancename )
   #  #Instance.DefineAsSuperSmallIntance()
   #  MRP()

