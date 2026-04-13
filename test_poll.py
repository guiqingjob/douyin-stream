import streamlit as st
import time

st.title("Smart Polling Test")
st.text_input("Type here (should not lose focus)")

if "running" not in st.session_state:
    st.session_state.running = False
    st.session_state.progress = 0

if st.button("Start Task"):
    st.session_state.running = True
    st.session_state.progress = 0
    st.rerun()

@st.fragment(run_every=1)
def poll_task():
    st.write(f"Polling... progress {st.session_state.progress}")
    st.session_state.progress += 10
    if st.session_state.progress >= 50:
        st.session_state.running = False
        st.rerun() # Break out of polling

if st.session_state.running:
    poll_task()
else:
    st.write("Not running. Static content.")
    if st.button("Do something else"):
        st.write("Did it")

