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
               
all_data = pd.DataFrame( columns = columnname  )
for f in glob.glob("./Test/*.xlsx"):
    df = pd.read_excel(f, sheetname = 'Result', parse_cols = 'A:V' )
    print df
    all_data = all_data.append(df)
    
writer = pd.ExcelWriter( "./Test/TestResult.xlsx", engine='openpyxl' ) 
all_data.to_excel( writer, "Res" )
writer.save( )