import streamlit as st

def apply_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500;700&family=Inter:wght@400;600&display=swap');

    /* Global Setting */
    .stApp {
        background-color: #F8F9FA;
        font-family: 'Inter', sans-serif;
    }

    /* Container Spacing for Header Visibility */
    .block-container { 
        padding-top: 3rem; 
        padding-bottom: 0rem; 
    }

    /* Typography */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        color: #2C3E50; /* Slate Blue */
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    
    div[data-testid="stMarkdownContainer"] p {
        color: #495057;
    }

    /* Metric Card */
    .metric-container {
        display: flex;
        flex-direction: column;
        background-color: #FFFFFF;
        border: 1px solid #E9ECEF;
        border-radius: 4px;
        padding: 12px 15px; /* Compact Padding */
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        height: 100%;
        transition: transform 0.2s ease-in-out;
    }
    
    .metric-container:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .metric-label {
        font-size: 0.75rem; /* Smaller Label */
        font-weight: 600;
        color: #6C757D; /* Muted Gray */
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }

    .metric-value {
        font-family: 'Roboto Mono', monospace;
        font-size: 1.5rem; /* Smaller Value */
        font-weight: 700;
        color: #212529;
    }

    .metric-sub {
        font-size: 0.75rem; /* Smaller Subtext */
        color: #ADB5BD;
        margin-top: auto;
        padding-top: 8px;
    }

    /* Table Styling */
    div[data-testid="stDataFrame"] {
        font-family: 'Roboto Mono', monospace;
        font-size: 0.9rem;
    }
    
    /* Divider */
    hr {
        margin-top: 2rem;
        margin-bottom: 2rem;
        border-top: 1px solid #DEE2E6;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E9ECEF;
    }
    
    </style>
    """, unsafe_allow_html=True)
