import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json
import os
from dotenv import load_dotenv
from semantic_search import SemanticSearch
from api_client import ProsperAPI
from llm_client import LLMClient
from report_builder import ReportBuilder
from visualization import QuestionVisualizer
from typing import Optional, Dict, List
import uuid

# Configure Streamlit to ignore PyTorch modules
os.environ['STREAMLIT_SERVER_WATCH_DIRS'] = 'false'
# Configure tokenizers to avoid parallelism warnings
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# Load environment variables
def get_env_var(var_name: str, default: str = None) -> str:
    """Get environment variable from either .env file or Streamlit secrets"""
    # Try to get from Streamlit secrets first (production)
    if var_name in st.secrets:
        return st.secrets[var_name]
    
    # If not in secrets, try to get from environment (local development)
    value = os.getenv(var_name, default)
    if value is None:
        raise ValueError(f"Required environment variable {var_name} not found")
    return value

# Try to load .env file for local development
load_dotenv()

# Initialize session state
if 'selected_question' not in st.session_state:
    st.session_state.selected_question = None
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'semantic_search' not in st.session_state:
    st.session_state.semantic_search = None
if 'show_results' not in st.session_state:
    st.session_state.show_results = False
if 'api_client' not in st.session_state:
    st.session_state.api_client = None
if 'saved_questions' not in st.session_state:
    st.session_state.saved_questions = []
if 'llm_client' not in st.session_state:
    st.session_state.llm_client = None
if 'generated_insights' not in st.session_state:
    st.session_state.generated_insights = None
if 'generated_report' not in st.session_state:
    st.session_state.generated_report = None
if 'report_builder' not in st.session_state:
    st.session_state.report_builder = ReportBuilder()
if 'saved_states' not in st.session_state:
    st.session_state.saved_states = {}
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None

def create_visualization(data):
    """Create a visualization of the data"""
    # Convert API response to DataFrame
    df = pd.DataFrame(data.get('responses', []))
    if df.empty:
        return None
        
    fig = go.Figure()
    
    # Plot each answer option as a line
    for column in df.columns:
        if column != 'date':
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df[column],
                mode='lines+markers',
                name=column
            ))
    
    fig.update_layout(
        title='Question Response Over Time',
        xaxis_title='Date',
        yaxis_title='Response Count',
        hovermode='x unified'
    )
    return fig

def display_search_results(results):
    """Display search results with selection buttons"""
    st.subheader("Search Results")
    for idx, question in enumerate(results):
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(f"{question['question_text']}", key=f"q_{idx}"):
                st.session_state.selected_question = question
                st.session_state.show_results = False
                st.rerun()
        with col2:
            st.write(f"Score: {question['similarity_score']:.2f}")

def get_common_segments():
    """Get common segment definitions for the app"""
    return {
        "Gender": {
            "question_id": "1",
            "answers": {
                "Male": "0",
                "Female": "1"
            }
        },
        "Age": {
            "question_id": "3",
            "answers": {
                "18-24": "1",
                "25-34": "2",
                "35-44": "3",
                "45-54": "4",
                "55-64": "5",
                "65+": "6"
            }
        },
        "Marital Status": {
            "question_id": "2",
            "answers": {
                "Married": "0",
                "Living with Unmarried Partner": "1",
                "Divorced or separated": "2",
                "Widowed": "3",
                "Single, never married": "4"
            }
        }
    }

def create_segment_selector():
    """Create a segment selector widget"""
    segments = get_common_segments()
    selected_segments = []
    
    st.subheader("Segment Selection")
    
    # Create expandable sections for each segment type
    for segment_name, segment_info in segments.items():
        with st.expander(f"{segment_name} Filter"):
            selected_answers = st.multiselect(
                f"Select {segment_name}",
                options=list(segment_info["answers"].keys()),
                key=f"segment_{segment_name}"
            )
            
            if selected_answers:
                selected_segments.append({
                    "question_id": segment_info["question_id"],
                    "answer_ids": [segment_info["answers"][answer] for answer in selected_answers]
                })
    
    return selected_segments

def save_question_data(question_id: str, metadata: Dict, data: Dict, segment: str, months: int, end_date: Optional[str]):
    """Save question data to the session state"""
    saved_question = {
        "id": str(uuid.uuid4()),  # Unique identifier for this saved question
        "question_id": question_id,
        "metadata": metadata,
        "data": data,
        "segment": segment,
        "months": months,
        "end_date": end_date,
        "saved_at": datetime.now().isoformat()
    }
    
    # Check if this question is already saved
    for existing in st.session_state.saved_questions:
        if (existing["question_id"] == question_id and 
            existing["segment"] == segment and 
            existing["months"] == months and 
            existing["end_date"] == end_date):
            st.warning("This question data is already saved!")
            return
    
    st.session_state.saved_questions.append(saved_question)
    st.success("Question data saved successfully!")

def save_current_state(state_name: str):
    """Save the current state (saved questions) to a file"""
    state = {
        "saved_questions": st.session_state.saved_questions,
        "timestamp": datetime.now().isoformat()
    }
    
    # Create states directory if it doesn't exist
    states_dir = "saved_states"
    os.makedirs(states_dir, exist_ok=True)
    
    # Save state to file
    state_file = os.path.join(states_dir, f"{state_name}.json")
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
    
    # Update session state
    st.session_state.saved_states[state_name] = state
    st.success(f"State '{state_name}' saved successfully!")

def load_saved_state(state_name: str):
    """Load a saved state from file"""
    state_file = os.path.join("saved_states", f"{state_name}.json")
    
    if not os.path.exists(state_file):
        st.error(f"State '{state_name}' not found!")
        return
    
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
        
        # Update session state with saved questions
        st.session_state.saved_questions = state["saved_questions"]
        st.session_state.saved_states[state_name] = state
        st.success(f"State '{state_name}' loaded successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"Error loading state: {str(e)}")

def get_saved_states():
    """Get list of saved states"""
    states_dir = "saved_states"
    if not os.path.exists(states_dir):
        return []
    
    states = []
    for file in os.listdir(states_dir):
        if file.endswith('.json'):
            state_name = file[:-5]  # Remove .json extension
            state_file = os.path.join(states_dir, file)
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                states.append({
                    "name": state_name,
                    "timestamp": state.get("timestamp", "Unknown"),
                    "questions_count": len(state.get("saved_questions", []))
                })
            except:
                continue
    
    return sorted(states, key=lambda x: x["timestamp"], reverse=True)

def display_saved_states():
    """Display saved states and provide options to load/delete them"""
    st.subheader("Saved States")
    
    states = get_saved_states()
    if not states:
        st.info("No saved states found. Save your current state to load it later.")
        return
    
    # Display states in a table
    states_df = pd.DataFrame(states)
    states_df["timestamp"] = pd.to_datetime(states_df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    states_df = states_df.rename(columns={
        "name": "State Name",
        "timestamp": "Saved At",
        "questions_count": "Questions"
    })
    
    st.dataframe(states_df, use_container_width=True)
    
    # State management buttons
    col1, col2 = st.columns(2)
    
    with col1:
        selected_state = st.selectbox(
            "Select state to load",
            options=[s["name"] for s in states],
            key="load_state_select"
        )
        if st.button("Load Selected State"):
            load_saved_state(selected_state)
    
    with col2:
        state_to_delete = st.selectbox(
            "Select state to delete",
            options=[s["name"] for s in states],
            key="delete_state_select"
        )
        if st.button("Delete Selected State"):
            state_file = os.path.join("saved_states", f"{state_to_delete}.json")
            try:
                os.remove(state_file)
                if state_to_delete in st.session_state.saved_states:
                    del st.session_state.saved_states[state_to_delete]
                st.success(f"State '{state_to_delete}' deleted successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error deleting state: {str(e)}")

def display_saved_questions():
    """Display the saved questions and their data"""
    st.subheader("Saved Questions")
    
    if not st.session_state.saved_questions:
        st.info("No questions saved yet. Search for questions and save them to generate a report.")
        return
    
    # Display saved questions in a table
    questions_df = pd.DataFrame([
        {
            "Question": q["metadata"]["Text"],
            "ID": q["metadata"]["ID"],
            "Segment": q["segment"],
            "Months": q["months"],
            "End Date": q["end_date"]
        }
        for q in st.session_state.saved_questions
    ])
    
    st.dataframe(questions_df, use_container_width=True)
    
    # Remove question button
    if st.button("Remove Selected Question", key="remove_question_select"):
        selected_question = st.selectbox(
            "Select question to remove",
            options=[q["metadata"]["Text"] for q in st.session_state.saved_questions],
            key="question_select"
        )
        st.session_state.saved_questions = [
            q for q in st.session_state.saved_questions
            if q["metadata"]["Text"] != selected_question
        ]
        st.rerun()
    
    # Report generation section
    st.subheader("Generate Report")
    
    # Initialize LLM client if not already done
    if st.session_state.llm_client is None:
        try:
            st.session_state.llm_client = LLMClient()
        except ValueError as e:
            st.error(str(e))
            return
    
    # Report type selection (only executive available)
    report_type = st.selectbox(
        "Select Report Type",
        options=["executive"],
        format_func=lambda x: "Executive Summary",
        key="report_type_select"
    )
    
    # Generate report button
    if st.button("Generate Report"):
        with st.spinner("Generating report..."):
            try:
                report = st.session_state.llm_client.generate_report(
                    st.session_state.saved_questions,
                    report_type
                )
                st.session_state.generated_report = report
                # Add to report builder
                st.session_state.report_builder.add_content(report)
            except Exception as e:
                st.error(f"Error generating report: {str(e)}")
    
    # Display generated report
    if st.session_state.generated_report:
        st.subheader("Generated Report")
        st.write(st.session_state.generated_report)
    
    # Save state section
    st.subheader("Save Current State")
    state_name = st.text_input("Enter a name for this state:", key="state_name_input")
    if st.button("Save Current State"):
        if not state_name:
            st.error("Please enter a name for the state")
        else:
            save_current_state(state_name)

def display_question_data(question_id: str, months: int = 12, end_date: Optional[str] = None, segment: str = "all"):
    """Display question data in a formatted way"""
    try:
        # Get question metadata first
        metadata = st.session_state.api_client.get_question_metadata(question_id)
        
        # Display question text and metadata
        st.subheader(metadata.get("Text", "Question Text Not Available"))
        st.write(f"**Type:** {metadata.get('Type', 'N/A')}")
        st.write(f"**First Asked:** {metadata.get('FirstAsked', 'N/A')}")
        st.write(f"**Last Asked:** {metadata.get('LastAsked', 'N/A')}")
        
        # Get question data
        data = st.session_state.api_client.get_question_data(
            question_id=question_id,
            months=months,
            end_date=end_date,
            segment=segment
        )
        
        # Add save button before displaying data
        if st.button("Save Question Data"):
            save_question_data(question_id, metadata, data, segment, months, end_date)
        
        # Create visualization section
        st.subheader("Visualization")
        
        # Determine if we have trend data
        is_trend = isinstance(data, list)
        
        # Add chart type selector
        chart_type = st.radio(
            "Select Chart Type",
            options=["line", "bar"],
            format_func=lambda x: x.capitalize(),
            horizontal=True
        )
        
        # Create and display the visualization
        fig = QuestionVisualizer.create_visualization(
            data=data,
            metadata=metadata,
            chart_type=chart_type
        )
        st.plotly_chart(fig, use_container_width=True, key=f"question_chart_{question_id}")
        
        # Add option to save visualization to report
        if st.button("Add to Report"):
            st.session_state.report_builder.add_visualization(fig, title=metadata.get("Text", "Question Results"))
            st.success("Visualization added to report!")
        
        # Display data
        st.subheader("Data")
        if isinstance(data, list):
            # Handle trend data
            valid_data_points = []
            
            # Filter out invalid data points
            for point in data:
                # Check if the point has valid data
                if (point.get('N', 0) > 0 and  # Sample size must be positive
                    point.get('AnswerResults') and  # Must have answer results
                    any(result.get('Result') is not None for result in point.get('AnswerResults', []))):  # At least one valid result
                    valid_data_points.append(point)
            
            if not valid_data_points:
                st.warning("No valid data points found for the selected time period.")
                return
                
            # Display valid data points
            for point in valid_data_points:
                st.write(f"**Date:** {point.get('StudyDate', 'N/A')}")
                st.write(f"**Sample Size (N):** {point.get('N', 'N/A')}")
                
                # Display answer results
                results = point.get('AnswerResults', [])
                if results:
                    for result in results:
                        # Skip results with None values
                        if result.get('Result') is None:
                            continue
                            
                        answer_id = result.get('ID')
                        answer_text = next(
                            (ans.get('Text', 'Unknown') for ans in metadata.get('Answers', []) 
                             if ans.get('ID') == answer_id),
                            'Unknown'
                        )
                        st.write(f"- {answer_text}: {result.get('Result', 'N/A')}")
                st.write("---")
        else:
            # Handle single point data
            # Check if the single point has valid data
            if (data.get('N', 0) > 0 and  # Sample size must be positive
                data.get('AnswerResults') and  # Must have answer results
                any(result.get('Result') is not None for result in data.get('AnswerResults', []))):  # At least one valid result
                
                st.write(f"**Sample Size (N):** {data.get('N', 'N/A')}")
                
                # Display answer results
                results = data.get('AnswerResults', [])
                if results:
                    for result in results:
                        # Skip results with None values
                        if result.get('Result') is None:
                            continue
                            
                        answer_id = result.get('ID')
                        answer_text = next(
                            (ans.get('Text', 'Unknown') for ans in metadata.get('Answers', []) 
                             if ans.get('ID') == answer_id),
                            'Unknown'
                        )
                        st.write(f"- {answer_text}: {result.get('Result', 'N/A')}")
            else:
                st.warning("No valid data available for the selected parameters.")
                return
    except Exception as e:
        st.error(f"Error fetching question data: {str(e)}")

# Authentication
def check_credentials(username, password):
    # In production, you should use environment variables for these
    return username == get_env_var("APP_USERNAME", "admin") and password == get_env_var("APP_PASSWORD", "admin")

def login():
    st.title("Prosper Insights Survey Analysis")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if check_credentials(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid username or password")

def display_search_page(prosper_client, semantic_search):
    """Display the search page with question search and results"""
    st.header("Question Search")
    
    # Initialize API client if not already done
    if st.session_state.api_client is None:
        try:
            st.session_state.api_client = prosper_client
        except ValueError as e:
            st.error(str(e))
            return
    
    # Initialize semantic search if not already done
    if st.session_state.semantic_search is None:
        questions_file = os.getenv("QUESTIONS_FILE", "questions.json")
        if os.path.exists(questions_file):
            st.session_state.semantic_search = semantic_search
            st.session_state.semantic_search.load_questions(questions_file)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        api_url = st.text_input("API URL", value=st.session_state.api_client.base_url)
        api_key = st.text_input("API Key", value=st.session_state.api_client.api_key, type="password")
        study_name = st.text_input("Study Name", value=st.session_state.api_client.study_name)
        questions_file = st.text_input("Questions File", value=os.getenv("QUESTIONS_FILE", "questions.json"))
        
        # Update configuration if changed
        if (api_url != st.session_state.api_client.base_url or 
            api_key != st.session_state.api_client.api_key or 
            study_name != st.session_state.api_client.study_name):
            st.session_state.api_client.base_url = api_url
            st.session_state.api_client.api_key = api_key
            st.session_state.api_client.study_name = study_name
            st.success("Configuration updated!")
    
    # Search input
    search_query = st.text_input("Enter your search query:")
    
    if search_query:
        # Perform semantic search
        results = st.session_state.semantic_search.search(search_query)
        
        if results:
            st.subheader("Search Results")
            
            # Display results in a selectbox
            selected_question = st.selectbox(
                "Select a question:",
                options=results,
                format_func=lambda x: f"{x['question_text']} (ID: {x['question_id']})",
                key="question_select"
            )
            
            if selected_question:
                st.subheader("Question Details")
                
                # Parameters for data retrieval
                col1, col2 = st.columns(2)
                with col1:
                    months = st.number_input("Number of months", min_value=0, max_value=60, value=12)
                with col2:
                    end_date = st.date_input("End date", value=datetime.now())
                
                # Create segment selector
                selected_segments = create_segment_selector()
                
                # Create segment string
                segment = "all"
                if selected_segments:
                    segment = st.session_state.api_client.create_segment_string(selected_segments)
                    st.write(f"**Selected Segment:** {segment}")
                
                # Display question data
                display_question_data(
                    question_id=selected_question['question_id'],
                    months=months,
                    end_date=end_date.strftime("%Y-%m-%d") if months > 0 else None,
                    segment=segment
                )
        else:
            st.warning("No results found for your search query.")

def show_help():
    """Display help instructions in an expandable section"""
    with st.expander("Help & Instructions", expanded=True):
        st.markdown("""
        ###

       Hey there! This is the very, very early version of a tool to analyze survey data from Prosper Insights. This app was created by me, Ben, and you can reach me at wedepo_b1@denison.edu. Please mess around and try to break it! If/when you do, please let me know! I added a quick breakdown of the app below. A few issues I am already aware of: The visuals are not polished and may render poorly. The question search occasionally returns strange results, so try to be as specific as possible for now! Thanks for checking it out!

        #### Search Questions
        - Use the search bar to find questions using natural language
        - Select a question from the results to view its data
        - Configure data retrieval parameters:
          - Number of months to analyze
          - End date
          - Segment filters (demographics)
        - Click the "Save Question Data" button to save the question data to your current state
        - Click the "Add to Report" button to add the visualization to your report

        #### Saved Questions & Analysis
        - View all your saved questions
        - Generate reports from saved questions
        - Remove questions you no longer need
        - Save your current state for later use

        #### Saved States
        - View all your saved states
        - Load previous states to continue your analysis
        - Delete states you no longer need
        """)

# Main app
def main():
    if not st.session_state.authenticated:
        login()
        return

    # Initialize API clients
    prosper_client = ProsperAPI()
    llm_client = LLMClient()
    semantic_search = SemanticSearch()

    # Sidebar navigation
    st.sidebar.title("Navigation")
    st.sidebar.write(f"Logged in as: {st.session_state.username}")
    
    # Help button at the top of sidebar
    show_help()
    st.sidebar.markdown("---")  # Add a separator
    
    page = st.sidebar.radio("Go to", ["Search Questions", "Saved Questions & Analysis", "Saved States"])
    
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.rerun()

    if page == "Search Questions":
        display_search_page(prosper_client, semantic_search)
    elif page == "Saved Questions & Analysis":
        display_saved_questions()
    else:
        display_saved_states()

if __name__ == "__main__":
    main() 