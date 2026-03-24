import streamlit as st


def cargar_css_corporativo():
    st.markdown("""
    <style>
    /* --- PALETA VAPA CYBER-DARK --- */
    :root {
        --vapa-yellow: #FFCC00;
        --vapa-neon:   #F0FF42;
        --bg-main:     #0E1117;
        --bg-card:     #161B22;
        --border-color:#30363d;
    }

    .stApp { background-color: var(--bg-main); color: #E6EDF3; }

    [data-testid="stSidebar"] {
        background-color: #010409 !important;
        border-right: 2px solid var(--vapa-yellow);
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] label { color: #FFFFFF !important; }

    .stButton > button {
        background-color: transparent !important;
        color: var(--vapa-yellow) !important;
        border: 2px solid var(--vapa-yellow) !important;
        font-weight: 800; border-radius: 8px;
        transition: all 0.3s ease;
        text-transform: uppercase; letter-spacing: 1px;
    }
    .stButton > button:hover {
        background-color: var(--vapa-yellow) !important;
        color: #000000 !important;
        box-shadow: 0 0 20px var(--vapa-yellow);
        transform: translateY(-2px);
    }

    h1, h2, h3 {
        color: var(--vapa-yellow) !important;
        text-shadow: 0 0 10px rgba(255,204,0,0.4);
        font-weight: 800;
    }
    h1 { border-bottom: 3px solid var(--vapa-yellow); padding-bottom: 10px; }

    .stTextInput>div>div>input,
    .stTextArea>div>div>textarea,
    .stSelectbox>div>div {
        background-color: #0d1117 !important;
        color: #c9d1d9 !important;
        border: 1px solid var(--border-color) !important;
    }
    .stTextInput>div>div>input:focus {
        border-color: var(--vapa-neon) !important;
        box-shadow: 0 0 8px var(--vapa-neon) !important;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [aria-selected="true"] {
        color: #000 !important;
        background-color: var(--vapa-yellow) !important;
        border-radius: 5px; font-weight: bold;
    }

    .stInfo {
        background-color: rgba(255,204,0,0.1) !important;
        border-left: 5px solid var(--vapa-yellow) !important;
        color: #E6EDF3 !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)
