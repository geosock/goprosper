# Prosper Insights Survey Analysis

A Streamlit application for analyzing survey data from the Prosper Insights API.

## Features

- Authentication with username/password
- Semantic search for survey questions
- Interactive data visualization
- Report generation with customizable sections
- State saving and loading
- Export to Word documents

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your configuration:
```env
OPENAI_API_KEY=your_openai_api_key
PROSPER_API_KEY=your_prosper_api_key
PROSPER_API_URL=your_prosper_api_url
STUDY_NAME=your_study_name
QUESTIONS_FILE=path/to/questions.json
APP_USERNAME=your_username  # For authentication
APP_PASSWORD=your_password  # For authentication
```

## Running Locally

```bash
streamlit run app.py
```

## Deployment

### Deploying to Streamlit Cloud

1. Push your code to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Set the following secrets in the Streamlit Cloud dashboard:
   - `OPENAI_API_KEY`
   - `PROSPER_API_KEY`
   - `PROSPER_API_URL`
   - `STUDY_NAME`
   - `QUESTIONS_FILE`
   - `APP_USERNAME`  # For authentication
   - `APP_PASSWORD`  # For authentication

### Deploying to Other Platforms

The application can be deployed to any platform that supports Python web applications. Make sure to:

1. Set up the required environment variables
2. Install the dependencies from `requirements.txt`
3. Configure the platform to run `streamlit run app.py`

## File Structure

```
streamlit_app/
├── app.py                 # Main application file
├── api_client.py          # Prosper API client
├── llm_client.py          # OpenAI client for report generation
├── report_builder.py      # Report building and export functionality
├── semantic_search.py     # Semantic search implementation
├── visualization.py       # Data visualization utilities
├── requirements.txt       # Python dependencies
├── .streamlit/           # Streamlit configuration
│   └── config.toml       # Streamlit settings
└── README.md             # This file
```

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key
- `PROSPER_API_KEY`: Your Prosper Insights API key
- `PROSPER_API_URL`: Base URL for the Prosper Insights API
- `STUDY_NAME`: Name of the study to analyze
- `QUESTIONS_FILE`: Path to the questions JSON file
- `APP_USERNAME`: Username for application authentication
- `APP_PASSWORD`: Password for application authentication

## Notes

- The application requires a questions JSON file for semantic search functionality
- Saved states are stored in the `saved_states` directory
- Generated reports are exported as Word documents
- Authentication is required to access the application