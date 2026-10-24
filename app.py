import streamlit as st

st.set_page_config(page_title="Home Title Checkup", page_icon=":material/home:", layout="centered")

st.markdown("""
<style>
html, body, [class*="css"] {font-size: 18px;}
.block-container {padding-top: 2rem; max-width: 820px;}
div.stButton > button, div.stDownloadButton > button {font-size: 1.05rem; padding: .6rem 1.2rem;}
.status-box {padding: 1.1rem 1.3rem; border-radius: 12px; margin: .5rem 0 1rem 0; border: 2px solid;}
.status-box h3 {margin: 0 0 .3rem 0;}
.status-green  {background: #e9f7ef; border-color: #1e8e3e;}
.status-blue   {background: #e8f0fe; border-color: #1a73e8;}
.status-orange {background: #fff4e5; border-color: #e37400;}
.status-red    {background: #fdecea; border-color: #c5221f;}
.status-gray   {background: #f1f3f4; border-color: #5f6368;}
.record-card {padding: .9rem 1.1rem; border-radius: 10px; background: #f8f9fa; border: 1px solid #dadce0;}
</style>
""", unsafe_allow_html=True)

# Larger text for older users and anyone reading on a phone
if st.sidebar.toggle("Larger text", key="big_text", help="Makes all the words on the screen bigger."):
    st.markdown("<style>html, body, [class*='css'], p, li, label {font-size: 22px !important;}</style>",
                unsafe_allow_html=True)

pages = [
    st.Page("app_pages/check.py", title="Check my home", icon=":material/home:", default=True),
    st.Page("app_pages/explore.py", title="Property map", icon=":material/map:"),
    st.Page("app_pages/inherit.py", title="Who would inherit?", icon=":material/family_restroom:"),
    st.Page("app_pages/learn.py", title="What is a tangled title?", icon=":material/help:"),
    st.Page("app_pages/about.py", title="About and sources", icon=":material/info:"),
]
st.navigation(pages).run()
