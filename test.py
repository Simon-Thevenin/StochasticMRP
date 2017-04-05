import cplex
import pandas as pd
import openpyxl as opxl
from MRPInstance import MRPInstance
from MRPSolution import MRPSolution
import time
import sys
import numpy as np

Debug = False
Instance = MRPInstance()
M = cplex.infinity

#This function returns the name of the quantity variable for product p in first period
#def GetNameQuantityPeriod1Variables( p ):
#    return "quantity_prod_time_%d_" % ( p )

#This function returns the name of the quantity variable for product p and time t
def GetNameQuantityVariable( p, t, w ):
    return "quantity_prod_time_scenar_%d_%d_%d" % ( p, t, w  )

#This function returns the name of the inventory variable for product p and time t
def GetNameInventoryVariable( p, t, w ):
    return "inventory_prod_time_scenar_%d_%d_%d" % ( p, t, w )

#This function returns the name of the production variable for product p in first period
#def GetNameProductionPeriod1Variable( p):
#    return "production_prod_time_%d" % ( p )

#This function returns the name of the production variable for product p and time t
def GetNameProductionVariable( p, t,w ):
    return "production_prod_time_scenar_%d_%d_%d" % ( p, t, w )

#This function returns the name of the backorder variable for product p and time t
def GetNameBackOrderQuantity( p, t, w ):
    return "backorder_prod_time_scenar_%d_%d_%d" % ( p, t, w )

#the function GetIndexQuantityVariable returns the index of the variable Q_{p, t}. Quantity of product p produced at time t
#def  GetIndexQuantiyPeriod1Variables( p ):
#    return Instance.StartQuantiyPeriod1Variables +  p

#the function GetIndexQuantityVariable returns the index of the variable Q_{p, t}. Quantity of product p produced at time t
def GetIndexQuantityVariable( p, t, w ):
    #if t == 0:
    #    print "This variable should not be defined at t = 0"
    return Instance.StartQuantityVariable + w * Instance.NrTimeBucket * Instance.NrProduct + t  * Instance.NrProduct + p

#the function GetIndexInventoryVariable returns the index of the variable I_{p, t}. Inventory of product p produced at time t
def GetIndexInventoryVariable( p, t, w ):
    return Instance.StartInventoryVariable + w * Instance.NrTimeBucket * Instance.NrProduct + t * Instance.NrProduct + p

#the function GetIndexProductionPeriod1Variable returns the index of the variable Y_{p, 1}.
# This variable equal to one is product p is produced at time t, 0 otherwise
#def GetIndexProductionPeriod1Variable( p ):
#    return Instance.StartProdustionPeriod1Variable  + p


#the function GetIndexProductionVariable returns the index of the variable Y_{p, t, w}.
# This variable equal to one is product p is produced at time t, 0 otherwise
def GetIndexProductionVariable( p, t, w ):
#    if t == 0:
#        print "This variable should not be defined at t = 0"
    return Instance.StartProdustionVariable  + w * Instance.NrTimeBucket * Instance.NrProduct + t  * Instance.NrProduct + p

#the function GetIndexBackorderVariable returns the index of the variable B_{p, t}. Quantity of product p produced backordered at time t
def GetIndexBackorderVariable( p, t, w ):
    return Instance.StartBackorderVariable + w * Instance.NrTimeBucket * Instance.NrProduct + t * Instance.NrProduct + p

#This function define the variables
def CreateVariable(c):
    # the variable quantity_prod_p indicated the quantity of product p produced at time 1
    #c.variables.add( obj = [ 0.0 ] * Instance.NrQuantiyPeriod1Variables,
    #                 lb = [ 0.0 ] * Instance.NrQuantiyPeriod1Variables,
    #                 ub = [ M ] * Instance.NrQuantiyPeriod1Variables )

    # the variable recourse_quantity_prod_time_scenario_p_t_w indicated the quantity of product p produced at time t in scenario w
    c.variables.add( obj = [ 0.0 ] * Instance.NrQuantiyVariables,
                     lb = [ 0.0 ] * Instance.NrQuantiyVariables,
                     ub = [ M ] * Instance.NrQuantiyVariables )

    # the variable inventory_prod_time_p_t indicated the inventory level of product p at time t
    c.variables.add( obj = Instance.InventoryCosts * ( Instance.NrTimeBucket * Instance.NrScenario ),
                     lb = [ 0.0 ] * Instance.NrInventoryVariable,
                     ub = [ M ] * Instance.NrInventoryVariable )

    # the variable production_prod_time_p_t equals 1 if a lot of product p is produced at time t
    c.variables.add( obj = Instance.SetupCosts * ( Instance.NrTimeBucket  * Instance.NrScenario ),
                     lb=[ 0.0 ] * Instance.NrProductionVariable,
                     ub=[ 1.0 ] * Instance.NrProductionVariable )
    # the variable backorder_prod_time_p_t gives the amount of product p backordered at time t
    c.variables.add( obj = Instance.BackorderCosts * ( Instance.NrTimeBucket * Instance.NrScenario ),
                     lb = [ 0.0 ] * Instance.NrBackorderVariable,
                     ub = [ M ] * Instance.NrBackorderVariable )

    #Define the variable name.
    #Usefull for debuging purpose. Otherwise, disable it, it is time consuming.
    if Debug:
        quantityvars = []
        inventoryvars = []
        productionvars = []
        backordervars = []
        for p in  Instance.ProductSet:
          #  quantityvars.append( ( GetIndexQuantiyPeriod1Variables( p, t ), GetNameQuantityPeriod1Variables( p ) ) )
          #  productionvars.append( ( GetIndexProductionPeriod1Variable( p ), GetNameProductionPeriod1Variable( p ) ) )
            for t in Instance.TimeBucketSet:
                  for w in Instance.ScenarioSet:
                    quantityvars.append( ( GetIndexQuantityVariable( p, t, w ), GetNameQuantityVariable( p, t, w ) ) )
                    productionvars.append( ( GetIndexProductionVariable( p, t, w ), GetNameProductionVariable( p, t, w ) ) )
                    inventoryvars.append( ( GetIndexInventoryVariable( p, t, w ), GetNameInventoryVariable( p, t, w ) ) )
                    backordervars.append( ( GetIndexBackorderVariable( p, t, w ), GetNameBackOrderQuantity( p, t, w ) ) )
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


# Demand and materials requirement: set the value of the invetory level and backorder quantity according to
#  the quantities produced and the demand
def CreateFlowConstraints(c):
     expressionstoadd = []
     sensestoadd = []
     rigthandsidestoadd = []
     for t in Instance.TimeBucketSet:
        for p in Instance.ProductSet:
            for w in Instance.ScenarioSet:
                righthandside = [ -1 * Instance.StartingInventories[ p ] ]
                backordervar = [];
                righthandside[ 0 ] = righthandside[ 0 ] + sum( Instance.Demands[ p ][ tau ][w] for tau in range( t + 1 ) )
                if  sum( Instance.Demands[ p ][ tau ][w]  for tau in range( Instance.NrTimeBucket )   ) > 0:
                    backordervar = [ GetIndexBackorderVariable( p, t, w ) ]

                quantityvar = [ GetIndexQuantityVariable( p, tau, w ) for tau in range( t - Instance.Leadtimes[ p ] + 1 ) ]

                dependentdemandvar = [ GetIndexQuantityVariable( q, tau, w ) for q in Instance.ProductSet
                                                                             for tau in range( t + 1 )
                                                                             if Instance.Requirements[ q ][ p ] > 0.0 ]

                inventoryvar = [ GetIndexInventoryVariable( p, t, w ) ]

                vars = inventoryvar + backordervar +  quantityvar + dependentdemandvar
                coeff = [ -1 ] * len( inventoryvar ) \
                        + [ 1 ] * len( backordervar ) \
                        + [ 1 ] * len( quantityvar ) \
                        + [-1* Instance.Requirements[ q ][ p ] for q in Instance.ProductSet
                                                      for tau in range( t + 1 )
                                                      if Instance.Requirements[ q ][ p ] > 0.0  ]

                 # PrintConstraint( vars, coeff, righthandside )
                if len( vars ) > 0 :
                     c.linear_constraints.add( lin_expr = [ cplex.SparsePair( vars, coeff ) ],
                                              senses = [ "E" ],
                                              rhs = righthandside )
     #            if len( vars ) > 0 :
     #                expressionstoadd.append( cplex.SparsePair( vars, coeff ) )
     #                sensestoadd.append( "E" )
     #                rigthandsidestoadd.append( righthandside[0] )
     #
     # c.linear_constraints.add( lin_expr = expressionstoadd,
     #                            senses = sensestoadd,
     #                            rhs = rigthandsidestoadd )

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
def CreateNonanticipativityConstraints(c):
    #Non anticipitativity only for period 1 for now
     for w1 in Instance.ScenarioSet:
         for w2 in Instance.ScenarioSet:
             if w1 <> w2:
                 for p in Instance.ProductSet:
                     vars = [ GetIndexQuantityVariable(p, 0, w1), GetIndexQuantityVariable(p, 0, w2)]
                     coeff = [ 1.0, -1.0]
                     righthandside = [0.0]
                     # PrintConstraint( vars, coeff, righthandside )
                     c.linear_constraints.add( lin_expr=[cplex.SparsePair(vars, coeff)],
                                               senses=["E"],
                                               rhs=righthandside )

                     vars = [ GetIndexProductionVariable(p, 0, w1), GetIndexProductionVariable(p, 0, w2)]
                     coeff = [1.0, -1.0]
                     righthandside = [0.0]
                     # PrintConstraint( vars, coeff, righthandside )
                     c.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                              senses=["E"],
                                              rhs=righthandside)

#Define the constraint of the model
def CreateConstraints(c):
     CreateFlowConstraints( c )
     CreateProductionConstraints( c )
     CreateCapacityConstraints( c )
     CreateNonanticipativityConstraints( c )




#This function creates the CPLEX model and solves it.
def MRP():
    start_time = time.time()
    if Debug:
        Instance.PrintInstance()

    #print "Start to model in Cplex";
    c = cplex.Cplex()

    #Create the variabbles and constraints
    CreateVariable(c)
    CreateConstraints(c)

    # Our aim is to minimize cost.
    c.objective.set_sense( c.objective.sense.minimize )
    if Debug:
        c.write("mrp.lp")
    else:
        c.set_log_stream( None ) #"mrp_log.txt")
        c.set_results_stream( None ) #"mrp_log.txt")
        c.set_warning_stream( None ) #"mrp_log.txt")
        c.set_error_stream( None ) #"mrp_log.txt")

    #tune the paramters
    c.parameters.timelimit.set( 1800.0 )
    c.parameters.threads.set( 1 )

    print "Start to solve instance %s with Cplex"% Instance.InstanceName;
    end_modeling = time.time();
    c.solve()
    buildtime =   end_modeling - start_time;
    solvetime =  time.time() - end_modeling ;
    sol = c.solution
    #print("Solution status = ", sol.get_status() )
    #print(sol.status[sol.get_status()])

    if Debug:
        sol.write( "mrpsolution.sol" )

    #Handle the results
    if sol.is_primal_feasible():
        objvalue = sol.get_objective_value()
        #print("Solution value  = %r" % objvalue)
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

        mrpsolution = MRPSolution( Instance, solquantity, solproduction, solinventory, solbackorder )
        if Debug:
            mrpsolution.Print()
        mrpsolution.PrintToExcel()

        #Print the output of the test in an excel file
        #writer = pd.ExcelWriter("./Test/TestResult.xlsx", engine='openpyxl')

        wb = opxl.Workbook()
        ws = wb.active
        try:
            wb = opxl.load_workbook("./Test/TestResult.xlsx");
            ws = wb.get_sheet_by_name( "Result" )
        except IOError:
            wb = opxl.Workbook()
            ws = wb.create_sheet("Result")
            columnname = [ "Instance name",
                           "Cplex solution value",
                           "Solution cost",
                           "Cplex_status",
                           "Build time",
                           "Solve time",
                           "Cplex gap",
                           "Cplex Nr nodes",
                           "Cplex best node nr",
                           "Cplex Nr Variable",
                           "Cplex Nr constraint",
                           "Inventory Cost",
                           "BackOrder cost",
                           "Setup cost",
                           "Nr level",
                           "Nr product",
                           "Nr time Period",
                           "Nr Scenario",
                           "Max lead time" ]
            ws.append( columnname )

        data =  [ Instance.InstanceName,
                  objvalue,
                  mrpsolution.TotalCost,
                  sol.status[ sol.get_status() ],
                  buildtime,
                  solvetime,
                  sol.MIP.get_mip_relative_gap(),
                  sol.progress.get_num_iterations(),
                  sol.MIP.get_incumbent_node(),
                  c.variables.get_num(),
                  c.linear_constraints.get_num(),
                  mrpsolution.InventoryCost,
                  mrpsolution.BackOrderCost,
                  mrpsolution.SetupCost,
                  Instance.NrLevel,
                  Instance.NrProduct,
                  Instance.NrTimeBucket,
                  Instance.NrScenario,
                  Instance.MaxLeadTime ]

        ws.append( data )
        wb.save( "./Test/TestResult.xlsx" )
    else:
        print("No solution available.")

if __name__ == "__main__":
    #Instance.DefineAsSmallIntance()
    #MRP();
      instancename = ""
      try:
         if len(sys.argv) == 1:
             instancename = raw_input("Enter the number (in [01;38]) of the instance to solve:")
         else:
             script, instancename = sys.argv

         Instance.ReadFromFile( instancename, 1 )
         MRP()
      except KeyError:
          print "This instance does not exist. Instance should be in 01, 02, 03, ... , 38"
   # Instance.DefineAsSmallIntance()
   #
   # Instance.PrintInstance()

