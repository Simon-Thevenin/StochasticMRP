import cplex
import pandas as pd
import openpyxl as opxl
from MRPInstance import MRPInstance
from MRPSolution import MRPSolution
import time
import sys
import numpy as np
import csv
from datetime import datetime

#pass Debug to true to get some debug information printed
Debug = False
Instance = MRPInstance()
M = cplex.infinity
#If UseNonAnticipativity is set to true a variable per scenario is generated, otherwise only the required variable a created.
UseNonAnticipativity = False
#ActuallyUseAnticipativity is set to False to compute the EPVI, otherwise, it is set to true to add the non anticipativity constraints
ActuallyUseAnticipativity = False
#PrintScenarios is set to true if the scenario tree is printed in a file, this is usefull if the same scenario must be reloaded in a ater test.
PrintScenarios = False
Method = "Two-stages"
#When a solution is obtained, it is recorded in Solution. This is used to compute VSS for instance.
Solution = None
#Evaluate solution is true, the solution in the variable "GivenQuantities" is given to CPLEX to compute the associated costs
EvaluateSolution = False
GivenQuantities =[]

#This function returns the name of the quantity variable for product p and time t
def GetNameQuantityVariable( p, t, w ):
    scenarioindex = -1;
    if Method == "One-stage":
        scenarioindex = 0
    elif UseNonAnticipativity or ( Method == "Two-stages" ):
            scenarioindex = w
            if Method == "Two-stages" and t == 0 : scenarioindex = 0
    else :
            scenarioindex = Instance.Scenarios[w].QuanitityVariable[t][p]
    return "quantity_prod_time_scenar_%d_%d_%d" % (p, t, scenarioindex );

#This function returns the name of the inventory variable for product p and time t
def GetNameInventoryVariable( p, t, w ):
    scenarioindex = -1;
    if UseNonAnticipativity or ( Method == "Two-stages" ):
        scenarioindex = w
        if Method == "Two-stages" and t == 0 : scenarioindex = 0
    else :
        scenarioindex = Instance.Scenarios[w].InventoryVariable[t][p]
    return "inventory_prod_time_scenar_%d_%d_%d" % ( p, t, scenarioindex )

#This function returns the name of the production variable for product p and time t
def GetNameProductionVariable( p, t,w ):
    scenarioindex = -1;
    if UseNonAnticipativity or ( Method == "Two-stages" ):
        scenarioindex = w
        if Method == "Two-stages" and t == 0 : scenarioindex = 0
    else :
        scenarioindex = Instance.Scenarios[w].ProductionVariable[t][p]
    return "production_prod_time_scenar_%d_%d_%d" % ( p, t, scenarioindex )

#This function returns the name of the backorder variable for product p and time t
def GetNameBackOrderQuantity( p, t, w ):
    scenarioindex = -1;
    if UseNonAnticipativity or ( Method == "Two-stages" ):
        scenarioindex = w
        if Method == "Two-stages" and t == 0 : scenarioindex = 0
    else:
        scenarioindex = Instance.Scenarios[w].BackOrderVariable[t][p]
    return "backorder_prod_time_scenar_%d_%d_%d" % ( p, t, scenarioindex )

#the function GetIndexQuantityVariable returns the index of the variable Q_{p, t}. Quantity of product p produced at time t
def GetIndexQuantityVariable( p, t, w ):
    if Method == "One-stage":
        return Instance.StartQuantityVariableOneStage + t  * Instance.NrProduct + p
    elif Method == "Two-stages":
        if t== 0:
            return Instance.StartQuantityVariableTwoStages +  p
        else:
            return Instance.StartQuantityVariableTwoStages +  Instance.NrProduct +  w  * ( Instance.NrTimeBucket -1 ) * Instance.NrProduct + (t-1) * Instance.NrProduct + p
    elif UseNonAnticipativity:
         return Instance.StartQuantityVariable + w * ( Instance.NrTimeBucket ) * Instance.NrProduct + t  * Instance.NrProduct + p
    else :
        return Instance.Scenarios[ w ].QuanitityVariable[t][p];

#the function GetIndexInventoryVariable returns the index of the variable I_{p, t}. Inventory of product p produced at time t
def GetIndexInventoryVariable( p, t, w ):
    if Method == "One-stage":
        return Instance.StartInventoryVariableOneStage + w * Instance.NrTimeBucket * Instance.NrProduct + t * Instance.NrProduct + p

    if Method == "Two-stages":
        if t == 0:
            return Instance.StartInventoryVariableTwoStages + p
        else :
            return Instance.StartInventoryVariableTwoStages + Instance.NrProduct + w * ( Instance.NrTimeBucket - 1) * Instance.NrProduct + (t-1) * Instance.NrProduct + p
    elif UseNonAnticipativity:
        return Instance.StartInventoryVariable + w * Instance.NrTimeBucket * Instance.NrProduct + t * Instance.NrProduct + p
    else :
        return Instance.Scenarios[ w ].InventoryVariable[t][p];

#the function GetIndexProductionVariable returns the index of the variable Y_{p, t, w}.
# This variable equal to one is product p is produced at time t, 0 otherwise
def GetIndexProductionVariable( p, t, w ):
    if Method == "One-stage":
        return Instance.StartProdustionVariableOneStage + w * Instance.NrTimeBucket * Instance.NrProduct + t * Instance.NrProduct + p

    if Method == "Two-stages":
        if t== 0:
            return Instance.StartProdustionVariableTwoStages +  p
        else:
            return Instance.StartProdustionVariableTwoStages +  Instance.NrProduct +  w  * ( Instance.NrTimeBucket -1 ) * Instance.NrProduct + (t-1) * Instance.NrProduct + p
    elif UseNonAnticipativity :
        return Instance.StartProdustionVariable + w * Instance.NrTimeBucket * Instance.NrProduct + t * Instance.NrProduct + p
    else:
        return Instance.Scenarios[w].ProductionVariable[t][p];

#the function GetIndexBackorderVariable returns the index of the variable B_{p, t}. Quantity of product p produced backordered at time t
def GetIndexBackorderVariable( p, t, w ):
    if Method == "One-stage":
        return Instance.StartBackorderVariableOneStage + w * Instance.NrTimeBucket * Instance.NrProduct + t * Instance.NrProduct + p

    if Method == "Two-stages":
        if t== 0:
            return Instance.StartBackorderVariableTwoStages +  p
        else:
            return Instance.StartBackorderVariableTwoStages +  Instance.NrProduct +  w  * ( Instance.NrTimeBucket -1 ) * Instance.NrProduct + (t-1) * Instance.NrProduct + p
    elif UseNonAnticipativity :
        return Instance.StartBackorderVariable + w * Instance.NrTimeBucket * Instance.NrProduct + t * Instance.NrProduct + p
    else:
        return Instance.Scenarios[w].BackOrderVariable[t][p];


#This function define the variables
def CreateVariable(c):
    #Define the cost vector for each variable. As the numbber of variable changes when non anticipativity is used the cost are created differently
    if Method == "Two-stages":
        inventorycosts = [Instance.InventoryCosts[p] * Instance.Scenarios[w].Probability
                          for w in Instance.ScenarioSet for t in range( Instance.NrTimeBucket -1 ) for p in Instance.ProductSet]
        setupcosts = [Instance.SetupCosts[p] * Instance.Scenarios[w].Probability
                      for w in Instance.ScenarioSet for t in range( Instance.NrTimeBucket -1 )  for p in Instance.ProductSet]
        backordercosts = [Instance.BackorderCosts[p] * Instance.Scenarios[w].Probability
                          for w in Instance.ScenarioSet for t in range( Instance.NrTimeBucket -1 )  for p in Instance.ProductSet]
        #Add the cost of time 0
        inventorycosts =  [ Instance.InventoryCosts[p]  for p in Instance.ProductSet ] + inventorycosts
        setupcosts = [Instance.SetupCosts[p] for p in Instance.ProductSet ] + setupcosts
        backordercosts = [Instance.BackorderCosts[p] for p in Instance.ProductSet ] + backordercosts
        nrinventoryvariable = Instance.NrQuantiyVariablesTwoStages;
        nrbackordervariable = Instance.NrBackorderVariableTwoStages;
        nrproductionvariable = Instance.NrProductionVariableTwoStages;
        nrquantityvariable = Instance.NrQuantiyVariablesTwoStages;

    elif UseNonAnticipativity :
        inventorycosts = [Instance.InventoryCosts[p] * Instance.Scenarios[w].Probability
                            for w in Instance.ScenarioSet for t in Instance.TimeBucketSet for p in Instance.ProductSet]
        setupcosts = [Instance.SetupCosts[p] * Instance.Scenarios[w].Probability
                      for w in Instance.ScenarioSet for t in Instance.TimeBucketSet for p in Instance.ProductSet]
        backordercosts = [Instance.BackorderCosts[p] * Instance.Scenarios[w].Probability
                      for w in Instance.ScenarioSet for t in Instance.TimeBucketSet for p in Instance.ProductSet]
        nrinventoryvariable = Instance.NrInventoryVariable;
        nrbackordervariable = Instance.NrBackorderVariable;
        nrproductionvariable = Instance.NrProductionVariable;
        if Method == "One-stage":
            nrquantityvariable = Instance.NrQuantiyVariablesOneStage
        else:
            nrquantityvariable = Instance.NrQuantiyVariables;
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
                        + Instance.InventoryCosts[p] * Instance.Scenarios[w].Probability
                    setupcosts[ setupcostindex ] = setupcosts[ setupcostindex ] \
                        + Instance.SetupCosts[p] * Instance.Scenarios[w].Probability
                    backordercosts[ backordercostindex ] = backordercosts[ backordercostindex ] \
                        + Instance.BackorderCosts[p] * Instance.Scenarios[w].Probability

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
    # Capacity constraint
    for p in Instance.ProductSet:
        for t in Instance.TimeBucketSet:
            for w in Instance.ScenarioSet:
                vars = [GetIndexQuantityVariable(p, t, w) ]
                coeff = [ 1.0 ]
                righthandside = [ GivenQuantities[p][t] ]
                # PrintConstraint( vars, coeff, righthandside )
                c.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                             senses=["E"],
                                             rhs=righthandside)


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

                if  t - Instance.Leadtimes[ p ] > 0 :
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
    for t in Instance.TimeBucketSet:
        for p in Instance.ProductSet:
            for w in Instance.ScenarioSet:
                ic_dict = {}
                ic_dict["lin_expr"] = cplex.SparsePair(ind=[GetIndexQuantityVariable(p, t, w)],
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
                    coeff = [Instance.CapacityConsumptions[p][k] for p in Instance.ProductSet]
                    righthandside = [1.0]
                    # PrintConstraint( vars, coeff, righthandside )
                    c.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                             senses=["L"],
                                             rhs=righthandside)


# This function creates the non anticipitativity constraint
def CreateNonanticipativityConstraints( c ):
    considertimebucket = Instance.TimeBucketSet;
    if Method == "Two-stages":
        considertimebucket = [0]

    #Non anticipitativity only for period 1 for now
    for w1 in Instance.ScenarioSet:
         for w2 in range( w1 +1, Instance.NrScenario):
             for p in Instance.ProductSet:
                 for t in considertimebucket:
                      if ( not Method == "Two-stages" ) and Instance.Scenarios[ w1 ].QuanitityVariable[ t ][ p ] == Instance.Scenarios[ w2 ].QuanitityVariable[ t ][ p ] :
                           vars = [ GetIndexQuantityVariable( p, t, w1 ), GetIndexQuantityVariable( p, t, w2 ) ]
                           coeff = [ 1.0, -1.0 ]
                           righthandside = [ 0.0 ]
                           # PrintConstraint( vars, coeff, righthandside )
                           c.linear_constraints.add( lin_expr = [cplex.SparsePair(vars, coeff)],
                                                       senses=["E"],
                                                       rhs=righthandside )

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
        Instance.PrintScenarioToFile()
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
        c.set_log_stream( "mrp_log%r_%r_%r"%(Instance.InstanceName,  Method,  Instance.NrScenarioPerBranch ))
        c.set_results_stream( "mrp_log%r_%r_%r"%(Instance.InstanceName,  Method,  Instance.NrScenarioPerBranch ))
        c.set_warning_stream( "mrp_log%r_%r_%r"%(Instance.InstanceName,  Method,  Instance.NrScenarioPerBranch ))
        c.set_error_stream( "mrp_log%r_%r_%r"%(Instance.InstanceName,  Method,  Instance.NrScenarioPerBranch ))

    #tune the paramters
    c.parameters.timelimit.set( 3600.0 )
    c.parameters.mip.limits.treememory.set( 7000.0 )
    c.parameters.threads.set( 1 )

    print "Start to solve instance %s with Cplex"% Instance.InstanceName;
    end_modeling = time.time();
    c.solve()
    buildtime =   end_modeling - start_time;
    solvetime =  time.time() - end_modeling ;
    sol = c.solution

    if Debug:
        sol.write( "mrpsolution.sol" )

    #Handle the results
    if sol.is_primal_feasible():
        objvalue = sol.get_objective_value()
        array =  [  GetIndexQuantityVariable( p, t, w )
                    for p in Instance.ProductSet for t in Instance.TimeBucketSet  for w in  Instance.ScenarioSet];
        solquantity =   sol.get_values( array )
        solquantity = np.array(solquantity, np.float32).reshape(
                                     (Instance.NrProduct, Instance.NrTimeBucket * Instance.NrScenario))

        result = solquantity.tolist()

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
        if Debug:
            Solution.Print()

            description = "%r_%r" % ( Method, Instance.NrScenarioPerBranch )

            Solution.PrintToExcel( description )

        data =  [ Instance.InstanceName,
                  Method,
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
                  Instance.NrScenarioPerBranch ]

        d = datetime.now()
        date = d.strftime('%m_%d_%Y_%H:%M:%S')
        myfile = open(r'./Test/TestResult_%s_%r_%s_%s.csv' % (Instance.InstanceName, Instance.NrScenarioPerBranch, Method, date), 'wb')
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        wr.writerow(data)

    else: 
        print("No solution available.")

    return result

if __name__ == "__main__":

    instancename = ""
    try: 
        if len(sys.argv) == 1:
            instancename = raw_input("Enter the number (in [01;38]) of the instance to solve:")
        else:
            script, instancename, nrbranchasstring = sys.argv

        nrbranch = int(nrbranchasstring)
        Method = "Multi-stages"
        Instance.Average = False
        Instance.NrScenarioPerBranch = nrbranch
        Instance.LoadScenarioFromFile = False
        PrintScenarios = True
        Instance.ReadFromFile( instancename, 1 )
        #Instance.DefineAsSuperSmallIntance()
    except KeyError:
        print "This instance does not exist. Instance should be in 01, 02, 03, ... , 38"
      
    MRP()

    #Method = "Two-stages"
    #Instance.Average = False
    #Instance.NrScenarioPerBranch = nrbranch
    #Instance.LoadScenarioFromFile = True
    #PrintScenarios = False
    #Instance.ReadFromFile(instancename, 1)
    #Instance.DefineAsSuperSmallIntance()
    #MRP()

    Method = "Average"
    Instance.Average = True
    Instance.NrScenarioPerBranch = nrbranch
    Instance.LoadScenarioFromFile = True
    PrintScenarios = False
    Instance.ReadFromFile( instancename, 1 )
    #Instance.DefineAsSuperSmallIntance()
    solutionofaverage = MRP()
    #
    Method = "Average_Solution_In_Multi-stages"
    Instance.Average = False
    Instance.NrScenarioPerBranch = nrbranch
    EvaluateSolution = True
    Instance.LoadScenarioFromFile = True
    PrintScenarios = False
    Instance.ReadFromFile( instancename, 1 )
    #Instance.DefineAsSuperSmallIntance()
    GivenQuantities = solutionofaverage
    MRP()

    Method = "Knowledge_Of_Future"
    Instance.Average = False
    Instance.NrScenarioPerBranch = nrbranch
    EvaluateSolution = False
    Instance.LoadScenarioFromFile = True
    PrintScenarios = False
    UseNonAnticipativity = True
    ActuallyUseAnticipativity = False
    Instance.ReadFromFile( instancename, 1 )
    #Instance.DefineAsSuperSmallIntance()
    MRP()


    Method = "One-stage"
    Instance.Average = False
    Instance.NrScenarioPerBranch = nrbranch
    EvaluateSolution = False
    Instance.LoadScenarioFromFile = True
    PrintScenarios = False
    UseNonAnticipativity = True
    ActuallyUseAnticipativity = False
    Instance.ReadFromFile( instancename, 1 )
    #Instance.DefineAsSuperSmallIntance()
    MRP()

