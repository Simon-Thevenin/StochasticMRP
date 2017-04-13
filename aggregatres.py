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
               "Nr level",
               "Nr product",
               "Nr time Period",
               "Nr Scenario",
               "Max lead time",
               "NrScenarioPerBranch" ]
               
all_data = pd.DataFrame(  columns = columnname )
#Add the content of each csv file at the end of the dataframe
for f in glob.glob("./Test/*.csv"):
    df = pd.read_csv( f, names= columnname )
    df.columns = columnname
    all_data = all_data.append(df,  ignore_index = True)

writer = pd.ExcelWriter( "./Test/TestResult.xlsx", engine='openpyxl' ) 
all_data.to_excel( writer, "Res" )
writer.save( )