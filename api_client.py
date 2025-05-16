import requests
import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

class ProsperAPI:
    """Client for interacting with the Prosper Insights API"""
    
    def __init__(self):
        """Initialize the API client with configuration from environment variables"""
        load_dotenv()
        self.base_url = os.getenv("API_URL", "")
        self.api_key = os.getenv("API_KEY", "")
        self.study_name = os.getenv("STUDY_NAME", "")
        
        if not all([self.base_url, self.api_key, self.study_name]):
            raise ValueError("Missing required environment variables: API_URL, API_KEY, or STUDY_NAME")
    
    def _make_request(self, endpoint: str, method: str = "GET", params: Optional[Dict] = None) -> Dict:
        """Make an API request with proper headers and error handling
        
        Args:
            endpoint (str): API endpoint to call
            method (str): HTTP method (GET, POST, etc.)
            params (dict, optional): Query parameters
            
        Returns:
            dict: API response data
            
        Raises:
            Exception: If the API request fails
        """
        # Add API key to params
        if params is None:
            params = {}
        params["apikey"] = self.api_key
        
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {str(e)}")
    
    def create_segment_string(self, segments: List[Dict[str, Union[str, List[str]]]]) -> str:
        """Create a Prosper segment string from a list of segment definitions
        
        Args:
            segments (list): List of segment definitions, each containing:
                - question_id (str): The question ID
                - answer_ids (list): List of answer IDs to include (OR-ed together)
                
        Returns:
            str: Properly formatted segment string
            
        Example:
            segments = [
                {"question_id": "1", "answer_ids": ["1"]},  # Female
                {"question_id": "2", "answer_ids": ["0"]},  # Married
                {"question_id": "3", "answer_ids": ["2", "3"]}  # Age 25-44
            ]
            # Returns: "1~1|2~0|3~2^3"
        """
        segment_strings = []
        
        for segment in segments:
            question_id = segment["question_id"]
            answer_ids = segment["answer_ids"]
            
            # Create the segment string for this question
            segment_string = f"{question_id}~{'^'.join(answer_ids)}"
            segment_strings.append(segment_string)
        
        # Join all segment strings with | (AND)
        return "|".join(segment_strings)
    
    def get_question_metadata(self, question_id: str) -> Dict:
        """Get metadata for a specific question
        
        Args:
            question_id (str): ID of the question to get metadata for
            
        Returns:
            dict: Question metadata including text, type, and answers
        """
        endpoint = f"metadata/{self.study_name}/{question_id}"
        return self._make_request(endpoint)
    
    def get_question_data(self, question_id: str, months: int = 0, end_date: Optional[str] = None, 
                         segment: str = "all", increment: int = 1) -> Dict:
        """Get data for a specific question
        
        Args:
            question_id (str): ID of the question to get data for
            months (int): Number of months of data to retrieve (0 for single point)
            end_date (str, optional): End date for the data range (YYYY-MM-DD)
            segment (str): Segment string or "all" for all respondents
            increment (int): Data increment in months (1=monthly, 3=quarterly, 12=annual)
            
        Returns:
            dict: Question data including responses over time
        """
        if months == 0:
            # Get single point data
            endpoint = f"data/{self.study_name}/{question_id}/{segment}"
        else:
            # Get trend data
            if end_date:
                endpoint = f"datatrend/{self.study_name}/{end_date}/{months}/{question_id}/{segment}/{increment}"
            else:
                endpoint = f"datatrend/{self.study_name}/{months}/{question_id}/{segment}/{increment}"
        
        return self._make_request(endpoint)
    
    def get_most_recent_date(self, question_id: str) -> str:
        """Get the most recent date a question was asked
        
        Args:
            question_id (str): ID of the question
            
        Returns:
            str: Most recent date in YYYY-MM-DD format
        """
        endpoint = f"mrd/{self.study_name}/{question_id}"
        return self._make_request(endpoint)
    
    def get_question_data_range(self, question_id: str, start_date: str, end_date: str, 
                              segment: str = "all", increment: int = 1) -> List[Dict]:
        """Get question data for a specific date range
        
        Args:
            question_id (str): ID of the question to get data for
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            segment (str): Segment string or "all" for all respondents
            increment (int): Data increment in months (1=monthly, 3=quarterly, 12=annual)
            
        Returns:
            list: List of question data objects for each date in the range
        """
        endpoint = f"datatrend/{self.study_name}/{start_date}/{end_date}/{question_id}/{segment}/{increment}"
        return self._make_request(endpoint)
    
    def get_summary(self, data: Dict) -> str:
        """Generate a summary of the question data using LLM
        
        Args:
            data (dict): Question data to summarize
            
        Returns:
            str: Generated summary
        """
        return self._make_request(
            "questions/summary",
            method="POST",
            data={"question_data": data}
        ).get("summary", "No summary available")
    
    def generate_report(self, report_type: str, start_date: str, end_date: str, segment: str = "all") -> Dict:
        """Generate a report based on the specified parameters
        
        Args:
            report_type (str): Type of report to generate
            start_date (str): Start date for the report (YYYY-MM-DD)
            end_date (str): End date for the report (YYYY-MM-DD)
            segment (str): Segment to filter data by
            
        Returns:
            dict: Generated report data
        """
        data = {
            "study": self.study_name,
            "report_type": report_type,
            "start_date": start_date,
            "end_date": end_date,
            "segment": segment
        }
        
        return self._make_request("reports/generate", method="POST", data=data) 