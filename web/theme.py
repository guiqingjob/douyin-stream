import streamlit as st


_CSS = """
<style>
:root{
  --mt-bg0:#0b0f14;
  --mt-bg1:#0f1722;
  --mt-surface:#101a28;
  --mt-surface2:#0d1623;
  --mt-border:rgba(255,255,255,.10);
  --mt-border2:rgba(255,255,255,.16);
  --mt-text:#e6edf7;
  --mt-text2:rgba(230,237,247,.78);
  --mt-text3:rgba(230,237,247,.58);
  --mt-accent:#5cf2d6;
  --mt-accent2:#68a6ff;
  --mt-danger:#ff5c7a;
  --mt-warn:#ffcc66;
  --mt-ok:#5cf2d6;
  --mt-radius:14px;
  --mt-radius-sm:10px;
  --mt-shadow:0 18px 46px rgba(0,0,0,.35);
}

html, body, [data-testid="stAppViewContainer"]{
  background:
    radial-gradient(1200px 700px at 18% 10%, rgba(104,166,255,.18), transparent 60%),
    radial-gradient(900px 540px at 82% 14%, rgba(92,242,214,.14), transparent 60%),
    radial-gradient(900px 600px at 40% 100%, rgba(255,92,122,.10), transparent 55%),
    linear-gradient(180deg, var(--mt-bg0), var(--mt-bg1));
}

[data-testid="stHeader"]{
  background: transparent;
}

[data-testid="stSidebar"]{
  background:
    radial-gradient(800px 520px at 20% 10%, rgba(104,166,255,.16), transparent 60%),
    linear-gradient(180deg, rgba(13,22,35,.95), rgba(11,15,20,.92));
  border-right: 1px solid var(--mt-border);
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] a{
  color: var(--mt-accent2);
}

.stApp{
  color: var(--mt-text);
}

h1,h2,h3,h4{
  letter-spacing: -0.02em;
}

.mt-page-header{
  padding: 12px 0 10px 0;
}
.mt-page-title{
  display:flex;
  align-items:center;
  gap:10px;
  font-weight: 760;
  line-height: 1.05;
  font-size: 34px;
  margin: 0 0 6px 0;
}
.mt-page-subtitle{
  color: var(--mt-text2);
  font-size: 14px;
  margin: 0;
}
.mt-tag{
  display:inline-flex;
  align-items:center;
  gap:6px;
  padding: 5px 10px;
  border-radius: 999px;
  border: 1px solid var(--mt-border);
  background: rgba(255,255,255,.04);
  color: var(--mt-text2);
  font-size: 12px;
}

div[data-testid="stMetric"]{
  border: 1px solid var(--mt-border);
  background: rgba(255,255,255,.03);
  border-radius: var(--mt-radius);
  box-shadow: 0 10px 26px rgba(0,0,0,.24);
}

.stButton > button{
  border-radius: 12px;
  border: 1px solid var(--mt-border2);
  transition: transform .08s ease, box-shadow .12s ease, border-color .12s ease, background-color .12s ease;
}
.stButton > button:focus-visible{
  outline: 3px solid rgba(92,242,214,.35) !important;
  outline-offset: 2px;
}
.stButton > button:hover{
  transform: translateY(-1px);
  box-shadow: 0 16px 30px rgba(0,0,0,.28);
}

.stButton > button[kind="primary"]{
  border-color: rgba(92,242,214,.55);
  background: linear-gradient(135deg, rgba(92,242,214,.22), rgba(104,166,255,.16));
}

div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stNumberInput"] input,
div[data-testid="stSelectbox"] div[role="combobox"],
div[data-testid="stFileUploader"] section{
  border-radius: 12px !important;
  border: 1px solid var(--mt-border) !important;
  background: rgba(255,255,255,.03) !important;
}

div[data-testid="stDataFrame"]{
  border-radius: var(--mt-radius);
  border: 1px solid var(--mt-border);
  overflow: hidden;
}

div[data-testid="stAlert"]{
  border-radius: var(--mt-radius);
  border: 1px solid var(--mt-border);
  background: rgba(255,255,255,.03);
}

@media (max-width: 920px){
  .mt-page-title{font-size: 28px;}
  [data-testid="stSidebar"]{border-right: none;}
}
</style>
"""


def apply_global_theme() -> None:
    if st.session_state.get("_mt_theme_applied"):
        return
    st.session_state["_mt_theme_applied"] = True
    st.markdown(_CSS, unsafe_allow_html=True)

