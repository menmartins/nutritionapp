import streamlit as st
import pandas as pd
from pulp import LpProblem, LpMinimize, LpVariable, lpSum
from collections import defaultdict

# Load data
requisitos_df = pd.read_csv('requisitos.csv')
tbalimentos_df = pd.read_csv('tbalimentos.csv')

# Replace hyphens and commas in food names with spaces for consistency
tbalimentos_df['NomeAlimento'] = tbalimentos_df['NomeAlimento'].str.replace('-', ' ').str.replace(',', '')
tbalimentos_df.set_index('NomeAlimento', inplace=True)

def sanitize_food_name(name):
    """ Standardize the food name by replacing special characters to ensure consistency with DataFrame indices. """
    return name.replace('_', ' ').replace('-', ' ').replace(',', ' ')

# Define functions
def get_nutritional_requirements(weight, gender, requisitos_df):
    gender_normalized = "Homem" if gender.lower() == "male" else "Mulher"
    closest_weight = requisitos_df[requisitos_df['Sexo'] == gender_normalized]['Peso'].sub(weight).abs().idxmin()
    requirements = requisitos_df.loc[closest_weight]
    # Return a Series with nutrient names as index and rounded values
    return requirements.drop(['Peso', 'Sexo']).round(1)

def select_foods_for_meal(nutritional_requirements, tbalimentos_df, available_foods, selected_foods_today):
    prob = LpProblem("MealSelection", LpMinimize)
    
    # Only include foods that are available for today's rotation
    food_vars = LpVariable.dicts("Food", available_foods, lowBound=0, cat='Continuous')
    food_selection_vars = LpVariable.dicts("FoodSelection", available_foods, cat='Binary')
    
    # Objective function includes a penalty for each selection of the food based on how many times it's been selected before
    # Increasing penalties for repeated selections
    prob += lpSum([food_vars[i] for i in available_foods]), "TotalWeightOfFood"
    
    # Nutritional constraints
    for nutrient, requirement in nutritional_requirements.items():
        prob += lpSum([food_vars[name] * value / 100 for name, value in tbalimentos_df.loc[available_foods, nutrient].items()]) >= requirement

    # Linking binary variables to quantity variables with minimum portion size
    for food in available_foods:
        prob += food_vars[food] >= 50 * food_selection_vars[food]  # Minimum 50g
        prob += food_vars[food] <= 1000 * food_selection_vars[food]

    # Penalty for selecting the same food again in the same day
    for food in available_foods:
        if food in selected_foods_today:
            prob += food_vars[food] * 1000  # High penalty for selecting the same food again

    prob.solve()

    return {v.name.replace("Food_", ""): v.varValue for v in prob.variables() if v.varValue > 0 and "FoodSelection" not in v.name}

def generate_weekly_meal_plan(requirements, tbalimentos_df, portion_of_day_target):
    weekly_plan = {}

    # Creating 21 food groups for rotation (7 days * 3 meals)
    food_rotation_groups = {
        (i, meal_time): tbalimentos_df.index[(i * 3 + meal_index)::21]
        for i in range(7)
        for meal_index, meal_time in enumerate(["Breakfast", "Lunch", "Dinner"])
    } 

    for day_index, day in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]):
        daily_plan = {}

        for meal_time, portion in zip(["Breakfast", "Lunch", "Dinner"], portion_of_day_target):
            meal_requirements = {nutrient: req * portion for nutrient, req in requirements.items()}
            available_foods = food_rotation_groups[(day_index, meal_time)]  # Specific food group for this day and meal
            selected_foods = select_foods_for_meal(meal_requirements, tbalimentos_df, available_foods, set())
            daily_plan[meal_time] = selected_foods
        
        weekly_plan[day] = daily_plan
    
    return weekly_plan

# Streamlit app UI
st.title('Weekly Meal Planner')

with st.sidebar:
    st.header("User Input")
    with st.form("input_form"):
        gender = st.selectbox('Select your gender', ['Male', 'Female'])
        weight = st.slider('Select your weight (kg)', min_value=20, max_value=150, step=1)
        submit_button = st.form_submit_button("Submit")

if submit_button:
    requirements = get_nutritional_requirements(weight, gender.lower(), requisitos_df)
    st.write("Nutritional Requirements")
    requirements_table = requirements.to_frame('Value').style.format("{:.1f}")
    st.table(requirements_table)
    portion_of_day_target = [0.25, 0.35, 0.4]  # Example: Breakfast, Lunch, Dinner

    meal_plan = generate_weekly_meal_plan(requirements, tbalimentos_df, portion_of_day_target)
    
    for day, meals in meal_plan.items():
        st.subheader(day)
        for meal_type, meal in meals.items():
            food_table = pd.DataFrame(list(meal.items()), columns=['Food', 'Portion (g)'])
            st.write(f"{meal_type}:")
            st.table(food_table.style.format({'Portion (g)': "{:.1f}"}))
            
            # Calculate nutrient totals
            nutrients_totals = defaultdict(float)
            for food, portion in meal.items():
                food_name = sanitize_food_name(food)
                try:
                    food_data = tbalimentos_df.loc[food_name]
                    nutrients_totals['Proteins (g)'] += food_data['Proteinas_g'] * (portion / 100)
                    nutrients_totals['Carbohydrates (g)'] += food_data['Carboidratos_g'] * (portion / 100)
                    nutrients_totals['Lipids (g)'] += food_data['Lipideos_g'] * (portion / 100)
                    nutrients_totals['Vitamin A'] += food_data['VitaminaA'] * (portion / 100)
                    nutrients_totals['Vitamin C'] += food_data['VitaminaC'] * (portion / 100)
                    nutrients_totals['Calcium (mg)'] += food_data['Calcio_mg'] * (portion / 100)
                    nutrients_totals['Iron (mg)'] += food_data['Ferro_mg'] * (portion / 100)
                except KeyError:
                    st.error(f"Warning: '{food_name}' not found in the database and will be skipped.")
            
            # Create a table for nutrient totals
            nutrients_table = pd.DataFrame(list(nutrients_totals.items()), columns=['Nutrient', 'Total'])
            st.table(nutrients_table.style.format({'Total': "{:.2f}"}))
