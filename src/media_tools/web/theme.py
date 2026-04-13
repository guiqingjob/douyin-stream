import streamlit as st


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root{
  --mt-bg0:#f9fafb;
  --mt-bg1:#f3f4f6;
  --mt-surface:rgba(255,255,255,.85);
  --mt-surface2:rgba(255,255,255,.95);
  --mt-border:rgba(0,0,0,.08);
  --mt-border2:rgba(0,0,0,.12);
  --mt-text:#111827;
  --mt-text2:rgba(17,24,39,.70);
  --mt-text3:rgba(17,24,39,.50);
  --mt-accent:#2563eb;
  --mt-accent2:#3b82f6;
  --mt-danger:#ef4444;
  --mt-warn:#f59e0b;
  --mt-ok:#10b981;
  --mt-radius:12px;
  --mt-radius-sm:8px;
  --mt-shadow:0 10px 25px rgba(0,0,0,.05);
  --mt-shadow2:0 4px 12px rgba(0,0,0,.03);
  --mt-font-ui:system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --mt-font-display:system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

html, body, [data-testid="stAppViewContainer"]{
  background: var(--mt-bg0);
}

[data-testid="stHeader"]{
  background: transparent;
}

[data-testid="stAppViewContainer"]::before{
  display: none;
}

[data-testid="stSidebar"]{
  background: rgba(255,255,255,.6);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-right: 1px solid var(--mt-border);
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] a{
  color: var(--mt-text2);
  text-decoration: none;
}

.stApp{
  font-family: var(--mt-font-ui) !important;
  color: var(--mt-text);
  font-size: 15px;
}

h1,h2,h3,h4{
  font-family: var(--mt-font-display) !important;
  letter-spacing: -0.01em;
  font-weight: 650;
}

html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"]{
  font-family: var(--mt-font-ui) !important;
}

p{
  line-height: 1.55;
}

p, li, span, label, small, div,
button, input, textarea, select,
[data-testid="stMarkdownContainer"], [data-testid="stText"]{
  font-family: var(--mt-font-ui) !important;
}

.mt-page-title{
  font-family: var(--mt-font-display) !important;
}

.block-container{
  padding-top: 1.4rem;
  padding-bottom: 3.5rem;
  max-width: 1160px;
}

.stApp hr{
  border-color: var(--mt-border) !important;
  opacity: .75;
  margin: 1.1rem 0;
}

.stCaption, [data-testid="stCaptionContainer"]{
  color: var(--mt-text3) !important;
}

.mt-page-header{
  padding: 18px 0 14px 0;
}
.mt-page-title{
  display:flex;
  align-items:center;
  gap:10px;
  font-weight: 650;
  line-height: 1.05;
  font-size: 32px;
  margin: 0 0 6px 0;
}
.mt-page-subtitle{
  color: var(--mt-text2);
  font-size: 15px;
  margin: 0;
}
.mt-tag{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid var(--mt-border);
  background: #ffffff;
  color: var(--mt-text2);
  font-size: 12px;
}

div[data-testid="stMetric"]{
  border: 1px solid var(--mt-border);
  background: var(--mt-surface);
  border-radius: var(--mt-radius);
  box-shadow: none;
  backdrop-filter: blur(10px);
}

div[data-testid="stMetric"] > div {
  padding: 6px 12px;
}

[data-testid="stMetricValue"] {
  font-size: 26px !important;
}

.stButton > button{
  border-radius: 8px;
  border: 1px solid var(--mt-border2);
  background: #ffffff;
  color: var(--mt-text);
  box-shadow: var(--mt-shadow2);
  font-family: var(--mt-font-ui);
  font-weight: 500;
  font-size: 14px;
  transition: transform .10s ease, box-shadow .18s ease, border-color .12s ease, background-color .12s ease, color .12s ease;
}
.stButton > button:focus-visible{
  outline: 2px solid rgba(37,99,235,.30) !important;
  outline-offset: 2px;
}
.stButton > button:hover{
  transform: translateY(-1px);
  box-shadow: var(--mt-shadow);
}

.stButton > button[kind="primary"]{
  border-color: transparent;
  background: var(--mt-accent);
  color: #ffffff;
}

.stButton > button[kind="secondary"]{
  background: #ffffff;
}

div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] div[role="combobox"],
div[data-testid="stFileUploader"] section{
  border-radius: 8px !important;
  border: 1px solid var(--mt-border) !important;
  background: #ffffff !important;
}

div[data-testid="stDataFrame"]{
  border-radius: var(--mt-radius);
  border: 1px solid var(--mt-border);
  overflow: hidden;
  background: rgba(255,255,255,.75);
}

div[data-testid="stAlert"]{
  border-radius: var(--mt-radius);
  border: 1px solid var(--mt-border);
  background: rgba(255,255,255,.72);
}

[data-testid="stSidebar"] a{
  display: block;
  padding: 8px 10px;
  margin: 2px 0;
  border-radius: 12px;
}
[data-testid="stSidebar"] a:hover{
  background: rgba(37,99,235,.06);
  color: var(--mt-text);
}

[data-testid="stSidebarNav"]{
  padding-top: 10px;
}

[data-testid="stNavSectionHeader"]{
  margin-top: 12px;
  padding: 8px 10px 6px 10px;
  border-radius: 12px;
  border: 1px solid transparent;
}

[data-testid="stNavSectionHeader"] span{
  font-family: var(--mt-font-ui);
  font-weight: 600 !important;
  font-size: 12px !important;
  color: var(--mt-text3);
}

[data-testid="stNavSectionHeader"]::after{
  display: none;
}

[data-testid="stSidebarNavLink"]{
  border: 1px solid transparent;
  transition: background-color .12s ease, border-color .12s ease, transform .10s ease;
}

[data-testid="stSidebarNavLink"][aria-current="page"]{
  background: rgba(37,99,235,.08) !important;
  border-color: rgba(37,99,235,.15) !important;
  box-shadow: inset 3px 0 0 var(--mt-accent);
}

[data-testid="stSidebarNavLink"] span[label]{
  font-family: var(--mt-font-ui);
  font-weight: 600;
  font-size: 14px;
}

[data-testid="stSidebarNavLink"]:hover{
  transform: translateY(-0.5px);
}

[data-testid="stToolbar"], [data-testid="stStatusWidget"]{
  visibility: hidden;
  height: 0;
}

@media (max-width: 920px){
  .mt-page-title{font-size: 30px;}
  [data-testid="stSidebar"]{border-right: none;}
}
</style>
"""


def apply_global_theme() -> None:
    if st.session_state.get("_mt_theme_applied"):
        return
    st.session_state["_mt_theme_applied"] = True
    st.markdown(_CSS, unsafe_allow_html=True)
