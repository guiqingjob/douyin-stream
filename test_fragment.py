import streamlit as st
import time

st.title("Fragment Test")
st.text_input("Type something here (should not lose focus)")

if "running" not in st.session_state:
    st.session_state.running = False

if st.button("Start Task"):
    st.session_state.running = True

@st.fragment
def auto_update():
    st.write(f"Task is running: {st.session_state.running}")
    if st.session_state.running:
        time.sleep(1)
        st.session_state.running = False # Simulate finish
        st.rerun()

auto_update()
