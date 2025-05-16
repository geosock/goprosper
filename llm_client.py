import os
import streamlit as st
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

class LLMClient:
    """Client for interacting with OpenAI's API for generating insights"""
    
    def __init__(self):
        """Initialize the LLM client with configuration from environment variables"""
        api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
        if not api_key:
            raise ValueError("Missing required environment variable: OPENAI_API_KEY")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"  # Using GPT-4o for best performance
    
    def _format_question_data(self, question: Dict[str, Any]) -> str:
        """Format question data for the LLM prompt
        
        Args:
            question (dict): Saved question data
            
        Returns:
            str: Formatted question data
        """
        metadata = question["metadata"]
        data = question["data"]
        
        # Format the question information
        formatted = f"Question: {metadata.get('Text', 'Unknown')}\n"
        formatted += f"Type: {metadata.get('Type', 'N/A')}\n"
        formatted += f"Segment: {question['segment']}\n"
        formatted += f"Time Period: {question['months']} months ending {question['end_date']}\n\n"
        
        # Format the answer options
        formatted += "Answer Options:\n"
        for answer in metadata.get("Answers", []):
            formatted += f"- {answer.get('Text', 'Unknown')} (ID: {answer.get('ID', 'N/A')})\n"
        formatted += "\n"
        
        # Format the response data
        if isinstance(data, list):
            formatted += "Trend Data:\n"
            for point in data:
                formatted += f"\nDate: {point.get('StudyDate', 'N/A')}\n"
                formatted += f"Sample Size (N): {point.get('N', 'N/A')}\n"
                formatted += "Results:\n"
                for result in point.get("AnswerResults", []):
                    if result.get("Result") is not None:
                        answer_id = result.get("ID")
                        answer_text = next(
                            (ans.get("Text", "Unknown") for ans in metadata.get("Answers", [])
                             if ans.get("ID") == answer_id),
                            "Unknown"
                        )
                        formatted += f"- {answer_text}: {result.get('Result', 'N/A')}\n"
        else:
            formatted += "Single Point Data:\n"
            formatted += f"Sample Size (N): {data.get('N', 'N/A')}\n"
            formatted += "Results:\n"
            for result in data.get("AnswerResults", []):
                if result.get("Result") is not None:
                    answer_id = result.get("ID")
                    answer_text = next(
                        (ans.get("Text", "Unknown") for ans in metadata.get("Answers", [])
                         if ans.get("ID") == answer_id),
                        "Unknown"
                    )
                    formatted += f"- {answer_text}: {result.get('Result', 'N/A')}\n"
        
        return formatted
    
    def generate_insights(self, questions: List[Dict[str, Any]], analysis_type: str = "comprehensive") -> str:
        """Generate insights from saved question data
        
        Args:
            questions (list): List of saved question data
            analysis_type (str): Type of analysis to perform
                - "comprehensive": Full analysis of trends and patterns
                - "summary": Brief summary of key findings
                - "trends": Focus on temporal trends
                - "segments": Focus on segment differences
            
        Returns:
            str: Generated insights
        """
        # Format all question data
        formatted_data = "\n\n".join(self._format_question_data(q) for q in questions)
        
        # Create the prompt based on analysis type
        if analysis_type == "comprehensive":
            prompt = """Analyze the following survey question data and provide comprehensive insights. 
            Structure your response using clear sections and subsections with headers.
            
            Include the following sections:
            
            # Executive Summary
            [Provide a brief overview of key findings]
            
            # Key Trends and Patterns
            ## Overall Trends
            [Describe main trends]
            ## Seasonal Patterns
            [Describe any seasonal variations]
            ## Long-term Changes
            [Describe long-term changes]
            
            # Segment Analysis
            ## Segment Differences
            [Describe differences between segments]
            ## Segment-specific Trends
            [Describe trends within segments]
            
            # Implications
            ## Business Impact
            [Describe business implications]
            ## Strategic Considerations
            [Describe strategic implications]
            
            # Recommendations
            ## Short-term Actions
            [List immediate recommendations]
            ## Long-term Strategy
            [List long-term recommendations]
            
            Data:
            """
        elif analysis_type == "summary":
            prompt = """Provide a concise summary of the key findings from the following survey data.
            Structure your response using clear sections with headers.
            
            Include the following sections:
            
            # Key Findings
            [List 3-5 most important findings]
            
            # Supporting Evidence
            [Provide data points supporting each finding]
            
            # Implications
            [Describe what these findings mean]
            
            Data:
            """
        elif analysis_type == "trends":
            prompt = """Analyze the temporal trends in the following survey data.
            Structure your response using clear sections with headers.
            
            Include the following sections:
            
            # Trend Overview
            [Provide a high-level summary of trends]
            
            # Time-based Analysis
            ## Short-term Changes
            [Describe recent changes]
            ## Medium-term Trends
            [Describe trends over the past few months]
            ## Long-term Patterns
            [Describe long-term patterns]
            
            # Seasonal Analysis
            ## Seasonal Patterns
            [Describe any seasonal variations]
            ## Year-over-Year Changes
            [Compare with previous years]
            
            # Significant Shifts
            ## Major Changes
            [Describe significant changes]
            ## Potential Causes
            [Analyze possible causes]
            
            Data:
            """
        else:  # segments
            prompt = """Analyze the segment differences in the following survey data.
            Structure your response using clear sections with headers.
            
            Include the following sections:
            
            # Segment Overview
            [Provide a high-level summary of segment differences]
            
            # Detailed Analysis
            ## Key Differences
            [Describe main differences between segments]
            ## Segment-specific Patterns
            [Describe patterns within each segment]
            
            # Trend Analysis
            ## Segment Trends
            [Describe how trends vary by segment]
            ## Convergence/Divergence
            [Describe if segments are becoming more similar or different]
            
            # Implications
            ## Business Impact
            [Describe how segment differences affect business]
            ## Strategic Recommendations
            [Provide segment-specific recommendations]
            
            Data:
            """
        
        prompt += formatted_data
        
        try:
            # Call OpenAI API using the new interface
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data analyst specializing in survey data analysis. Provide clear, actionable insights based on the data. Use markdown formatting for headers and sections."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"Error generating insights: {str(e)}")
    
    def generate_report(self, questions: List[Dict[str, Any]], report_type: str = "executive") -> str:
        """Generate a formal report from saved question data
        
        Args:
            questions (list): List of saved question data
            report_type (str): Type of report to generate (only "executive" is supported)
            
        Returns:
            str: Generated report
        """
        # Format all question data
        formatted_data = "\n\n".join(self._format_question_data(q) for q in questions)
        
        # Create the prompt for executive report
        prompt = """Create an executive summary report based on the following survey data.
        Structure your response using clear sections with headers.
        
        Include the following sections:
        
        # Executive Summary
        [Provide a concise overview of key findings]
        
        # Key Findings
        ## Primary Insights
        [List 3-5 most important findings]
        ## Supporting Data
        [Provide key data points]
        
        # Business Implications
        ## Market Impact
        [Describe market implications]
        ## Strategic Considerations
        [Describe strategic implications]
        
        # Recommendations
        ## Immediate Actions
        [List immediate recommendations]
        ## Strategic Initiatives
        [List long-term recommendations]
        
        # Next Steps
        [Outline specific next steps and timeline]
        
        Data:
        """
        
        prompt += formatted_data
        
        try:
            # Call OpenAI API using the new interface
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a data analyst creating a formal report. Use clear, professional language and structure the content appropriately. Use markdown formatting for headers and sections."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise 