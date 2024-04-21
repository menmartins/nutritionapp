import streamlit as st
import pandas as pd

# Load or create your DataFrame here
tbalimentos_df = pd.read_csv('tbalimentos.csv')
tbalimentos_df.set_index('NomeAlimento', inplace=True)

# Use this to print to the terminal (for debugging purposes)
print(tbalimentos_df.index.tolist())

# Use this to display in the Streamlit app
st.write(tbalimentos_df.index.tolist())