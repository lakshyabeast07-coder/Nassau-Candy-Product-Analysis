import streamlit as st

st.set_page_config(page_title="Demo App", layout="centered")

st.title("Demo Streamlit App")
name = st.text_input("Enter your name")

if name:
    st.success(f"Hello, {name}!")
