import streamlit as st
import asyncio
from agent import ask_treelife_agent
import os

st.set_page_config(page_title="Rahul CRM", page_icon="🏢", layout="wide")

# Custom CSS for Corporate Look
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #f4f7f6;
        color: #1e293b;
        font-family: 'Inter', -apple-system, sans-serif;
    }
    
    /* Chat Message Styling */
    .stChatMessage {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 15px 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        border: 1px solid #e2e8f0;
        margin-bottom: 12px;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Sidebar Blue Header */
    .sidebar-header {
        color: #ffffff; /* White text */
        background-color: #2563eb; /* Bright Blue */
        padding: 8px 15px;
        border-radius: 8px;
        text-align: center;
        font-size: 1.5em;
        font-weight: 700;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.2);
    }
    
    /* Status indicators */
    .status-item {
        padding: 12px;
        border-radius: 8px;
        background-color: #f0fdf4;
        border-left: 4px solid #16a34a;
        margin-bottom: 15px;
        font-size: 0.95em;
        color: #1e293b;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    
    /* User Input styling */
    .stChatInputContainer {
        border-radius: 12px !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.04) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Configuration ---
with st.sidebar:
    st.markdown('<div class="sidebar-header">🏢 Rahul CRM</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    st.markdown("#### System Status")
    st.markdown("""
    <div class="status-item">
        <strong>🟢 LLM Engine</strong><br>
        Llama 3.1 70B (Connected)
    </div>
    <div class="status-item">
        <strong>🟢 Database Engine</strong><br>
        Semantic Mapping Active
    </div>
    <div class="status-item">
        <strong>🟢 Translation Layer</strong><br>
        API Interface Online
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("#### About")
    st.info("Enterprise Translation Layer. Allows non-technical executives to query messy, unstructured CRM databases using natural language.")

# Check for API Key
if not os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_API_KEY") == "your_nvidia_api_key_here":
    st.error("⚠️ NVIDIA_API_KEY missing in .env file.")
    st.stop()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Welcome to the Treelife Enterprise Translation Layer. How can I assist you with your CRM data today?"}]

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get user input
prompt = st.chat_input("Enter your natural language query...")

# React to user input
if prompt:
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Analyzing schema and compiling semantic translation..."):
            try:
                # Call our MCP Agent
                response = asyncio.run(ask_treelife_agent(prompt))
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                st.error(f"System Error: {str(e)}")
