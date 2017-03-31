import cplex
import pandas as pd
from MRPInstance import MRPInstance
from MRPSolution import MRPSolution

Debug = True
Instance = MRPInstance()
M = cplex.infinity

def GetNameQuanityVariable(p, t):
    return "quantity_prod_time_%d_%d" % (p, t)

def GetNameInventoryVariable(p, t):
    return "inventory_prod_time_%d_%d" % (p, t)

def GetNameProductionVariable(p, t):
    return "production_prod_time_%d_%d" % (p, t)

def GetNameBackOrderQuantity(p, t):
    return "backorder_prod_time_%d_%d" % (p, t)

#the function GetIndexQuantityVariable returns the index of the variable Q_{p, t}. Quantity of product p produced at time t
def GetIndexQuantityVariable( p, t ):
    return Instance.StartQuantityVariable + t* Instance.NrProduct + p;

#the function GetIndexInventoryVariable returns the index of the variable I_{p, t}. Inventory of product p produced at time t
def GetIndexInventoryVariable( p, t ):
    return Instance.StartInventoryVariable + t *  Instance.NrProduct  + p;

#the function GetIndexProductionVariable returns the index of the variable Y_{p, t}.
# This variable equal to one is product p is produced at time t, 0 otherwise
def GetIndexProductionVariable( p, t ):
    return Instance.StartProdustionVariable + t * Instance.NrProduct + p;

#the function GetIndexBackorderVariable returns the index of the variable B_{p, t}. Quantity of product p produced backordered at time t
def GetIndexBackorderVariable( p, t ):
    return Instance.StartBackorderVariable + t * Instance.NrProduct  + p;

#This function define the variables
def CreateVariable(c):
    # the variable quantity_prod_time_p_t indicated the quantity of product p produced at time t
    c.variables.add( obj = [ 0.0 ] * Instance.NrQuantiyVariables,
                     lb = [ 0.0 ] * Instance.NrQuantiyVariables,
                     ub = [ M ] * Instance.NrQuantiyVariables )

    # the variable inventory_prod_time_p_t indicated the inventory level of product p at time t
    c.variables.add( obj = Instance.InventoryCosts * Instance.NrTimeBucket ,
                     lb = [ 0.0 ] * Instance.NrInventoryVariable,
                     ub = [ M ] * Instance.NrInventoryVariable )

    # the variable production_prod_time_p_t equals 1 if a lot of product p is produced at time t
    c.variables.add( obj = Instance.SetupCosts * Instance.NrTimeBucket,
                     lb=[ 0.0 ] * Instance.NrProductionVariable,
                     ub=[ 1.0 ] * Instance.NrProductionVariable )
    # the variable backorder_prod_time_p_t gives the amount of product p backordered at time t
    c.variables.add( obj = Instance.BackorderCosts * Instance.NrTimeBucket,
                     lb = [ 0.0 ] * Instance.NrBackorderVariable,
                     ub = [ M ] * Instance.NrBackorderVariable )

    #Define the variable name.
    #Usefull for debuging purpose. Otherwise, disable it, it is time consuming.
    if Debug:
        quantityvars = []
        inventoryvars = []
        productionvars = []
        backordervars = []
        for p in range( Instance.NrProduct ):
            for t in range( Instance.NrTimeBucket ):
                index = p * Instance.NrTimeBucket + t
                quantityvars.append( ( GetIndexQuantityVariable( p, t ), GetNameQuanityVariable( p, t ) ) )
                inventoryvars.append( ( GetIndexInventoryVariable( p, t ), GetNameInventoryVariable(p, t) ) )
                productionvars.append( ( GetIndexProductionVariable( p, t ), GetNameProductionVariable(p, t) ) )
                backordervars.append( ( GetIndexBackorderVariable( p, t ), GetNameBackOrderQuantity( p, t ) ) )
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
     for t in range( Instance.NrTimeBucket ):
        for p in range( Instance.NrProduct ):
            righthandside = [ -1 * Instance.StartingInventories[ p ] ]

            backordervar = [];
            #
            righthandside[ 0 ] = righthandside[ 0 ] + sum( Instance.Demands[ p ][ tau ] for tau in range( t + 1 ) )
            if  sum( Instance.Demands[ p ][ tau ]  for tau in range( Instance.NrTimeBucket )   ) > 0:
                backordervar = [ GetIndexBackorderVariable( p, t ) ]

            quantityvar = [ GetIndexQuantityVariable( p, tau ) for tau in range( t - Instance.Leadtimes[ p ] + 1 ) ]

            dependentdemandvar = [ GetIndexQuantityVariable( q, tau ) for q in range( Instance.NrProduct )
                                                                      for tau in range( t + 1 )
                                                                      if Instance.Requirements[ q ][ p ] > 0.0 ]

            inventoryvar = [ GetIndexInventoryVariable( p, t ) ]

            vars = inventoryvar + backordervar +  quantityvar + dependentdemandvar
            coeff = [ -1 ] * len( inventoryvar ) \
                    + [ 1 ] * len( backordervar ) \
                    + [ 1 ] * len( quantityvar ) \
                    + [-1* Instance.Requirements[ q ][ p ] for q in range( Instance.NrProduct )
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
            for t in range( Instance.NrTimeBucket ) :
                vars = [ GetIndexQuantityVariable( p, t ) for p in range( Instance.NrProduct ) ]
                coeff = [ Instance.CapacityConsumptions[ p ][ k ] for p in range( Instance.NrProduct ) ]
                righthandside = [ 1.0 ]
                # PrintConstraint( vars, coeff, righthandside )
                c.linear_constraints.add( lin_expr = [ cplex.SparsePair( vars, coeff )],
                                              senses = [ "L" ],
                                              rhs = righthandside )



def MRP():
    Instance.PrintInstance()

    print "Start to model in Cplex";
    c = cplex.Cplex()

    Instance.ComputeIndices()

    print "The indexes of the variables are:"
    print "quantity: %d - %d, inventory: %d - %d, prodution: %d - %d,  backorder: %d - %d" % (
        Instance.StartQuantityVariable, Instance.NrQuantiyVariables, Instance.StartInventoryVariable, Instance.NrInventoryVariable,
        Instance.StartProdustionVariable, Instance.NrProductionVariable, Instance.StartBackorderVariable, Instance.NrBackorderVariable)

    CreateVariable(c)
    CreateConstraints(c)

    # Our aim is to minimize cost.
    c.objective.set_sense( c.objective.sense.minimize )
    if Debug:
        c.write("mrp.lp")
    c.set_log_stream("mrp_log.txt")
    c.set_log_stream("mrp_log.txt")
    c.set_log_stream("mrp_log.txt")
    c.set_log_stream("mrp_log.txt")

    print "Start to solve with Cplex";
    c.solve()

    sol = c.solution
    print("Solution status = ", sol.get_status() )
    print(sol.status[sol.get_status()])


    if sol.is_primal_feasible():
        print("Solution value  = %r" % sol.get_objective_value())
        array =  [  GetIndexQuantityVariable( p, t ) for p in range( Instance.NrProduct ) for t in range( Instance.NrTimeBucket )    ];
        solquantity =   sol.get_values( array )
        solquantity =  zip(*[iter(solquantity)] * Instance.NrTimeBucket )

        array = [ GetIndexProductionVariable( p, t ) for p in range(Instance.NrProduct ) for t in range( Instance.NrTimeBucket ) ]
        solproduction = sol.get_values( array )
        solproduction = zip( *[ iter(solproduction) ] * Instance.NrTimeBucket )

        array = [ GetIndexInventoryVariable( p, t )  for p in range(Instance.NrProduct) for t in range( Instance.NrTimeBucket )  ]
        solinventory = sol.get_values( array )
        solinventory = zip(*[iter(solinventory)] * Instance.NrTimeBucket )

        array = [ GetIndexBackorderVariable( p, t ) for p in range(Instance.NrProduct) for t in range( Instance.NrTimeBucket ) ]
        solbackorder = sol.get_values( array )
        solbackorder = zip(*[iter(solbackorder)] * Instance.NrTimeBucket )

        mrpsolution = MRPSolution( Instance, solquantity, solproduction, solinventory, solbackorder )
        mrpsolution.Print()
        mrpsolution.PrintToExcel()
    else:
        print("No solution available.")

if __name__ == "__main__":
    instancename = raw_input( "Enter the number (in [0;38]) of the instance to solve:" )
    Instance.ReadFromFile( instancename )
   # Instance.DefineAsSmallIntance()
   # Instance.DefineAsSuperSmallIntance()
   # Instance.PrintInstance()
    if Instance.NrProduct > 0 :
        MRP();
    else :
        print "Problem during instance reading";
