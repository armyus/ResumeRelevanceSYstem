import streamlit as st

st.set_page_config(
    page_title="HireSight",
    page_icon="🧠",
    layout="wide"
)

st.title("Welcome to HireSight")
st.write("The all-in-one solution for resume analysis.")
st.info("Please select a portal from the sidebar on the left to get started.")

st.sidebar.success("Select a portal to begin.")

