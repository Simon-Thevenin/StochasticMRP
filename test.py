import cplex
import pandas as pd
import openpyxl as opxl
from MRPInstance import MRPInstance
from MRPSolution import MRPSolution
import time
import sys
import numpy as np

Debug = True
Instance = MRPInstance()
M = cplex.infinity

#This function returns the name of the quantity variable for product p and time t
def GetNameQuanityVariable( p, t ):
    return "quantity_prod_time_%d_%d" % ( p, t )

#This function returns the name of the inventory variable for product p and time t
def GetNameInventoryVariable( p, t, w ):
    return "inventory_prod_time_scenar_%d_%d_%d" % ( p, t, w )

#This function returns the name of the production variable for product p and time t
def GetNameProductionVariable( p, t ):
    return "production_prod_time_scenar_%d_%d" % ( p, t )

#This function returns the name of the backorder variable for product p and time t
def GetNameBackOrderQuantity( p, t, w ):
    return "backorder_prod_time_scenar_%d_%d_%d" % ( p, t, w )

#the function GetIndexQuantityVariable returns the index of the variable Q_{p, t}. Quantity of product p produced at time t
def GetIndexQuantityVariable( p, t ):
    return Instance.StartQuantityVariable + t * Instance.NrProduct + p

#the function GetIndexInventoryVariable returns the index of the variable I_{p, t}. Inventory of product p produced at time t
def GetIndexInventoryVariable( p, t, w ):
    return Instance.StartInventoryVariable + w * Instance.NrTimeBucket * Instance.NrProduct + t * Instance.NrProduct + p

#the function GetIndexProductionVariable returns the index of the variable Y_{p, t}.
# This variable equal to one is product p is produced at time t, 0 otherwise
def GetIndexProductionVariable( p, t ):
    return Instance.StartProdustionVariable + t * Instance.NrProduct + p

#the function GetIndexBackorderVariable returns the index of the variable B_{p, t}. Quantity of product p produced backordered at time t
def GetIndexBackorderVariable( p, t, w ):
    return Instance.StartBackorderVariable + w * Instance.NrTimeBucket * Instance.NrProduct + t * Instance.NrProduct + p

#This function define the variables
def CreateVariable(c):
    # the variable quantity_prod_time_p_t indicated the quantity of product p produced at time t
    c.variables.add( obj = [ 0.0 ] * Instance.NrQuantiyVariables,
                     lb = [ 0.0 ] * Instance.NrQuantiyVariables,
                     ub = [ M ] * Instance.NrQuantiyVariables )

    # the variable inventory_prod_time_p_t indicated the inventory level of product p at time t
    c.variables.add( obj = Instance.InventoryCosts * ( Instance.NrTimeBucket * Instance.NrScenario ),
                     lb = [ 0.0 ] * Instance.NrInventoryVariable,
                     ub = [ M ] * Instance.NrInventoryVariable )

    # the variable production_prod_time_p_t equals 1 if a lot of product p is produced at time t
    c.variables.add( obj = Instance.SetupCosts * ( Instance.NrTimeBucket ),
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
            for t in Instance.TimeBucketSet:
                 quantityvars.append( ( GetIndexQuantityVariable( p, t ), GetNameQuanityVariable( p, t ) ) )
                 productionvars.append((GetIndexProductionVariable(p, t), GetNameProductionVariable(p, t)))
                 for w in Instance.ScenarioSet:
                    inventoryvars.append( ( GetIndexInventoryVariable( p, t, w ), GetNameInventoryVariable(p, t, w) ) )
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

#Define the constraint of the model
def CreateConstraints(c):
    # Demand and materials requirement: set the value of the invetory level and backorder quantity according to
    #  the quantities produced and the demand
     for t in Instance.TimeBucketSet:
        for p in Instance.ProductSet:
            for w in Instance.ScenarioSet:
                righthandside = [ -1 * Instance.StartingInventories[ p ] ]

                backordervar = [];
                #
                righthandside[ 0 ] = righthandside[ 0 ] + sum( Instance.Demands[ p ][ tau ][w] for tau in range( t + 1 ) )
                if  sum( Instance.Demands[ p ][ tau ][w]  for tau in range( Instance.NrTimeBucket )   ) > 0:
                    backordervar = [ GetIndexBackorderVariable( p, t, w ) ]

                quantityvar = [ GetIndexQuantityVariable( p, tau ) for tau in range( t - Instance.Leadtimes[ p ] + 1 ) ]

                dependentdemandvar = [ GetIndexQuantityVariable( q, tau ) for q in Instance.ProductSet
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

                # indicator constraint to se the production variable to 1 when a positive quantity is produce
                ic_dict = {}
                ic_dict["lin_expr"] = cplex.SparsePair( ind = [ GetIndexQuantityVariable(p, t) ],
                                                        val = [ 1.0 ] )
                ic_dict["rhs"] = 0.0
                ic_dict["sense"] = "E"
                ic_dict["indvar"] = GetIndexProductionVariable( p, t )
                ic_dict["complemented"] = 1
                c.indicator_constraints.add(**ic_dict )

     #Capacity constraint
     if Instance.NrResource > 0:
        for k in range( Instance.NrResource ) :
            for t in Instance.TimeBucketSet :
                vars = [ GetIndexQuantityVariable( p, t ) for p in Instance.ProductSet ]
                coeff = [ Instance.CapacityConsumptions[ p ][ k ] for p in Instance.ProductSet ]
                righthandside = [ 1.0 ]
                # PrintConstraint( vars, coeff, righthandside )
                c.linear_constraints.add( lin_expr = [ cplex.SparsePair( vars, coeff )],
                                              senses = [ "L" ],
                                              rhs = righthandside )


#This function creates the CPLEX model and solves it.
def MRP():
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
        c.set_log_stream("mrp_log.txt")
        c.set_results_stream("mrp_log.txt")
        c.set_warning_stream("mrp_log.txt")
        c.set_error_stream("mrp_log.txt")

    #tune the paramters
    c.parameters.timelimit.set( 1800.0 )
    c.parameters.threads.set( 1 )

    print "Start to solve with Cplex";
    start_time = time.time()
    c.solve()
    elapsedtime =  time.time() - start_time;
    sol = c.solution
    #print("Solution status = ", sol.get_status() )
    #print(sol.status[sol.get_status()])

    if Debug:
        sol.write( "mrpsolution.sol" )

    #Handle the results
    if sol.is_primal_feasible():
        objvalue = sol.get_objective_value()
        #print("Solution value  = %r" % objvalue)
        array =  [  GetIndexQuantityVariable( p, t ) for p in Instance.ProductSet for t in Instance.TimeBucketSet ];
        solquantity =   sol.get_values( array )
        solquantity =  zip(*[iter(solquantity)] * Instance.NrTimeBucket )

        array = [ GetIndexProductionVariable( p, t ) for p in Instance.ProductSet for t in Instance.TimeBucketSet ]
        solproduction = sol.get_values( array )
        solproduction = np.array( solproduction,np.float32 ).reshape( ( Instance.NrProduct, Instance.NrTimeBucket ) )
        array = [ GetIndexInventoryVariable( p, t, w )
                  for p in Instance.ProductSet  for w in  Instance.ScenarioSet   for t in Instance.TimeBucketSet  ]
        solinventory = sol.get_values( array )
        solinventory =  np.array( solinventory,np.float32 ).reshape( ( Instance.NrProduct, Instance.NrTimeBucket * Instance.NrScenario ) )
        #print solinventory
        test = [  "w %d t %d p %d"%(w,t,p)
                  for p in Instance.ProductSet  for w in Instance.ScenarioSet   for t in Instance.TimeBucketSet   ]
        testarray = np.array(test).reshape((Instance.NrProduct,
                                            Instance.NrTimeBucket * Instance.NrScenario))
        #print test
        #print testarray
        iterables = [Instance.ScenarioSet, Instance.TimeBucketSet]
        multiindex = pd.MultiIndex.from_product(iterables, names=['scenario', 'time'])

        testdf = pd.DataFrame(testarray, index=Instance.ProductName, columns=multiindex)
        #print testdf
        array = [ GetIndexBackorderVariable( p, t, w )
                  for p in Instance.ProductSet  for w in Instance.ScenarioSet   for t in Instance.TimeBucketSet  ]
        solbackorder = sol.get_values(array)
        solbackorder = np.array(solbackorder, np.float32).reshape((Instance.NrProduct, Instance.NrTimeBucket * Instance.NrScenario))  # array # tempmatinv.reshape(  (Instance.NrScenario, Instance.NrProduct, Instance.NrTimeBucket) ) # zip(*[iter(solinventory)] * Instance.NrTimeBucket )
        #print solbackorder

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
                           "Cplex time",
                           "Cplex gap",
                           "Cplex Nr nodes",
                           "Cplex best node nr",
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
                  elapsedtime,
                  sol.MIP.get_mip_relative_gap() ,
                  sol.progress.get_num_iterations(),
                  sol.MIP.get_incumbent_node(),
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
    #Instance.DefineAsSuperSmallIntance()
    #MRP();
     instancename = ""
     try:
         if len(sys.argv) == 1:
             instancename = raw_input("Enter the number (in [01;38]) of the instance to solve:")
         else:
             script, instancename = sys.argv

         Instance.ReadFromFile( instancename, 500, 1 )
         MRP();
     except KeyError:
         print "This instance does not exist. Instance should be in 01, 02, 03, ... , 38"
   # Instance.DefineAsSmallIntance()
   #
   # Instance.PrintInstance()

