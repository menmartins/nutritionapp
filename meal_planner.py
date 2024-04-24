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
        prob += food_vars[food] >= 50 * food_selection_vars[food] 
        prob += food_vars[food] <= 1000 * food_selection_vars[food]

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
            available_foods = food_rotation_groups[(day_index, meal_time)]
            selected_foods = select_foods_for_meal(meal_requirements, tbalimentos_df, available_foods, set())
            daily_plan[meal_time] = selected_foods
        
        weekly_plan[day] = daily_plan
    
    return weekly_plan # Return the weekly plan 

# Streamlit app UI
st.title('Weekly Meal Planner')
st.image('image.jpg', caption=None, width=None, use_column_width=None, clamp=False, channels="RGB", output_format="auto")

# Sidebar
st.sidebar.header("User Input")

# Checkbox for Advanced Mode
advanced_mode = st.sidebar.checkbox("Advanced Mode")

if not advanced_mode:
    # Basic Mode Inputs
    with st.sidebar.form("basic_input_form"):
        gender = st.selectbox('Select your gender', ['Male', 'Female'])
        weight = st.slider('Select your weight (kg)', min_value=20, max_value=150, step=1)
        submit_button = st.form_submit_button("Submit")

if advanced_mode or submit_button:
    if advanced_mode:
        # Advanced Mode Inputs
        st.sidebar.subheader("Nutritional Requirements")
        with st.sidebar.form("advanced_input_form"):
            protein_requirement = st.number_input("Protein Requirement (g)", min_value=0.0, step=1.0, value=0.0)
            carb_requirement = st.number_input("Carbohydrate Requirement (g)", min_value=0.0, step=1.0, value=0.0)
            lipid_requirement = st.number_input("Lipid Requirement (g)", min_value=0.0, step=1.0, value=0.0)
            vitamin_a_requirement = st.number_input("Vitamin A Requirement (IU)", min_value=0.0, step=1.0, value=0.0)
            vitamin_c_requirement = st.number_input("Vitamin C Requirement (mg)", min_value=0.0, step=1.0, value=0.0)
            calcium_requirement = st.number_input("Calcium Requirement (mg)", min_value=0.0, step=1.0, value=0.0)
            iron_requirement = st.number_input("Iron Requirement (mg)", min_value=0.0, step=1.0, value=0.0)
            calorie_requirement = st.number_input("Calorie Requirement (kcal)", min_value=0.0, step=1.0, value=0.0)
            submit_button = st.form_submit_button("Submit")

    if submit_button:
        if advanced_mode:
            requirements = {
                "Proteinas_g": protein_requirement,
                "Carboidratos_g": carb_requirement,
                "Lipideos_g": lipid_requirement,
                "VitaminaA": vitamin_a_requirement,
                "VitaminaC": vitamin_c_requirement,
                "Calcio_mg": calcium_requirement,
                "Ferro_mg": iron_requirement,
                "Energia_kcal": calorie_requirement
            }
        else:
            requirements = get_nutritional_requirements(weight, gender.lower(), requisitos_df)

        st.write("Nutritional Requirements")
        requirements_table = pd.Series(requirements).to_frame('Value').style.format("{:.1f}")
        st.table(requirements_table)
        portion_of_day_target = [0.25, 0.35, 0.4]  # Example: Breakfast, Lunch, Dinner

        meal_plan = generate_weekly_meal_plan(requirements, tbalimentos_df, portion_of_day_target)

        # Loop to display the meal plan (moved outside the function)
        for day, meals in meal_plan.items():
            st.subheader(day)
            for meal_type, meal in meals.items():
                food_table = pd.DataFrame(list(meal.items()), columns=['Food', 'Portion (g)'])
                st.write(f"{meal_type}:")
                st.table(food_table.style.format({'Portion (g)': "{:.1f}"}))
                
                # Calculate nutrient totals
                nutrients_totals = defaultdict(float)
                total_calories = 0 
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
                        total_calories += food_data['Energia_kcal'] * (portion / 100) 
                    except KeyError:
                        st.error(f"Warning: '{food_name}' not found in the database and will be skipped.")
                
                # Create a table for nutrient totals
                nutrients_table = pd.DataFrame(list(nutrients_totals.items()), columns=['Nutrient', 'Total'])
                st.table(nutrients_table.style.format({'Total': "{:.2f}"}))

                # Display total calories
                st.write(f"**Total Calories:** {total_calories:.2f} kcal")
