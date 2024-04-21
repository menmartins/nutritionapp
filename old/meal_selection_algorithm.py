import pandas as pd
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatus

# Load data
tbalimentos_df = pd.read_csv('tbalimentos.csv')

# Define the problem
prob = LpProblem("OptimalDietProblem", LpMinimize)

# Create a dictionary of food items and a variable for each representing the grams of each food to include in the diet
food_vars = LpVariable.dicts("Food", tbalimentos_df.NomeAlimento, lowBound=0, cat='Continuous')

# Objective function: Minimize total weight of food to simplify the diet
prob += lpSum([food_vars[i] for i in tbalimentos_df.NomeAlimento]), "TotalWeightOfFood"

# Nutritional requirements constraints (example for each nutrient)
prob += lpSum([food_vars[name] * protein / 100 for name, protein in zip(tbalimentos_df.NomeAlimento, tbalimentos_df.Proteinas_g)]) >= 56, "ProteinRequirement"
prob += lpSum([food_vars[name] * carbs / 100 for name, carbs in zip(tbalimentos_df.NomeAlimento, tbalimentos_df.Carboidratos_g)]) >= 280, "CarbohydrateRequirement"
prob += lpSum([food_vars[name] * lipids / 100 for name, lipids in zip(tbalimentos_df.NomeAlimento, tbalimentos_df.Lipideos_g)]) >= 70, "LipidRequirement"
prob += lpSum([food_vars[name] * vitA / 100 for name, vitA in zip(tbalimentos_df.NomeAlimento, tbalimentos_df.VitaminaA)]) >= 900, "VitaminARequirement"
prob += lpSum([food_vars[name] * vitC / 100 for name, vitC in zip(tbalimentos_df.NomeAlimento, tbalimentos_df.VitaminaC)]) >= 90, "VitaminCRequirement"
prob += lpSum([food_vars[name] * calcium / 100 for name, calcium in zip(tbalimentos_df.NomeAlimento, tbalimentos_df.Calcio_mg)]) >= 1000, "CalciumRequirement"
prob += lpSum([food_vars[name] * iron / 100 for name, iron in zip(tbalimentos_df.NomeAlimento, tbalimentos_df.Ferro_mg)]) >= 8, "IronRequirement"

# Solve the problem
prob.solve()

# Print the results
print("Status:", LpStatus[prob.status])
for v in prob.variables():
    if v.varValue > 0:
        print(v.name, "=", v.varValue)
