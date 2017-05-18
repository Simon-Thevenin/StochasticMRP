#This script aggregates all the csv file in the folder Test.

import openpyxl as opxl
import pandas as pd
import glob as glob

columnname = [ "Instance name",
               "Method",
               "Cplex solution value",
               "Solution cost",
               "Cplex_status",
               "Build time",
               "Solve time",
               "Cplex gap",
               "Cplex Nr iteration",
               "Cplex Nr nodes",
               "Cplex best node nr",
               "Cplex Nr Variable",
               "Cplex Nr constraint",
               "Inventory Cost",
               "BackOrder cost",
               "Setup cost",
               "In sample Average", 
               "In Sample Standard deviation",
               "Nr level",
               "Nr product",
               "Nr time Period",
               "Demand Tree Seed",
			   "Nr Scenario",
               "Max lead time",
			   "BranchingStrategy",
               "Demand Distribuion",
			   "UseNonAnticipativity", 
			   "ActuallyUseAnticipativity",
			   "Model",
			   "UseSlowMoving",		
			   "ComputeAverageSolution",	
			   "ScenarioSeed"		   
			   ]
			  
all_data = pd.DataFrame(  columns = columnname )
#Add the content of each csv file at the end of the dataframe
for f in glob.glob("./Test/*.csv"):
    df = pd.read_csv( f, names= columnname )
    df.columns = columnname
    all_data = all_data.append(df,  ignore_index = True)

writer = pd.ExcelWriter( "./Test/TestResult.xlsx", engine='openpyxl' ) 
all_data.to_excel( writer, "Res" )
writer.save( )

columnname = ["Instance name",
              "Model",
              "Identificator",
              "Mean",
              "Variance",
              "Covariance",
              "LB",
              "UB",
              "Min Average",
              "Max Average"
              ]

all_data = pd.DataFrame(columns=columnname)
# Add the content of each csv file at the end of the dataframe
for f in glob.glob("./Test/Bounds/*.csv"):
    df = pd.read_csv(f, names=columnname)
    df.columns = columnname
    all_data = all_data.append(df, ignore_index=True)

writer = pd.ExcelWriter("./Test/Bounds/TestResultBounds.xlsx", engine='openpyxl')
all_data.to_excel(writer, "Res")
writer.save()

columnname = ["Instance name",
              "Model",
              "Nr Scenario",
              "KPI On Time",
              "KPI Backorder",
              "KPI Lost sales",
              "Stock level 1",
              "Stock level 2",
              "Stock level 3",
              "Stock level 4",
              "Stock level 5"
              ]

all_data = pd.DataFrame(columns=columnname)
# Add the content of each csv file at the end of the dataframe
for f in glob.glob("./Test/Statistic/*.csv"):
    df = pd.read_csv(f, names=columnname)
    df.columns = columnname
    all_data = all_data.append(df, ignore_index=True)

writer = pd.ExcelWriter("./Test/Statistic/TestResultStatistic.xlsx", engine='openpyxl')
all_data.to_excel(writer, "Res")
writer.save()