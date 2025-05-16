import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, List, Any, Optional, Literal, Union
from datetime import datetime

class QuestionVisualizer:
    """Class for creating visualizations from question data"""
    
    @staticmethod
    def _prepare_trend_data(data: List[Dict], metadata: Dict) -> pd.DataFrame:
        """Convert trend data to a pandas DataFrame for visualization
        
        Args:
            data (List[Dict]): List of data points
            metadata (Dict): Question metadata
            
        Returns:
            pd.DataFrame: Prepared data for visualization
        """
        # Create a list to store the data
        rows = []
        
        for point in data:
            date = point.get('StudyDate')
            for result in point.get('AnswerResults', []):
                if result.get('Result') is not None:
                    answer_id = result.get('ID')
                    answer_text = next(
                        (ans.get('Text', 'Unknown') for ans in metadata.get('Answers', [])
                         if ans.get('ID') == answer_id),
                        'Unknown'
                    )
                    rows.append({
                        'Date': date,
                        'Answer': answer_text,
                        'Value': result.get('Result') * 100  # Convert decimal to percentage
                    })
        
        return pd.DataFrame(rows)
    
    @staticmethod
    def _prepare_single_point_data(data: Dict, metadata: Dict) -> pd.DataFrame:
        """Convert single point data to a pandas DataFrame for visualization
        
        Args:
            data (Dict): Single data point
            metadata (Dict): Question metadata
            
        Returns:
            pd.DataFrame: Prepared data for visualization
        """
        rows = []
        
        for result in data.get('AnswerResults', []):
            if result.get('Result') is not None:
                answer_id = result.get('ID')
                answer_text = next(
                    (ans.get('Text', 'Unknown') for ans in metadata.get('Answers', [])
                     if ans.get('ID') == answer_id),
                    'Unknown'
                )
                rows.append({
                    'Answer': answer_text,
                    'Value': result.get('Result') * 100  # Convert decimal to percentage
                })
        
        return pd.DataFrame(rows)
    
    @staticmethod
    def create_visualization(
        data: Union[List[Dict], Dict],
        metadata: Dict,
        chart_type: Literal["line", "bar"] = "line",
        title: Optional[str] = None
    ) -> go.Figure:
        """Create a visualization for question data
        
        Args:
            data (Union[List[Dict], Dict]): Question data (trend or single point)
            metadata (Dict): Question metadata
            chart_type (str): Type of chart to create ("line" or "bar")
            title (Optional[str]): Title for the chart
            
        Returns:
            go.Figure: Plotly figure object
        """
        # Determine if we have trend data or single point data
        is_trend = isinstance(data, list)
        
        # Prepare the data
        if is_trend:
            df = QuestionVisualizer._prepare_trend_data(data, metadata)
            x_col = 'Date'
            y_col = 'Value'
            color_col = 'Answer'
        else:
            df = QuestionVisualizer._prepare_single_point_data(data, metadata)
            x_col = 'Answer'
            y_col = 'Value'
            color_col = None
        
        # Create the appropriate visualization
        if chart_type == "line":
            fig = px.line(
                df,
                x=x_col,
                y=y_col,
                color=color_col,
                title=title or metadata.get('Text', 'Question Results'),
                labels={
                    'Date': 'Date',
                    'Value': 'Response (%)',
                    'Answer': 'Answer Option'
                },
                color_discrete_sequence=px.colors.qualitative.Set3  # Use a colorblind-friendly palette
            )
        else:  # bar
            fig = px.bar(
                df,
                x=x_col,
                y=y_col,
                color=color_col,
                title=title or metadata.get('Text', 'Question Results'),
                labels={
                    'Date': 'Date',
                    'Value': 'Response (%)',
                    'Answer': 'Answer Option'
                },
                color_discrete_sequence=px.colors.qualitative.Set3  # Use a colorblind-friendly palette
            )
        
        # Update layout
        fig.update_layout(
            xaxis_title=x_col,
            yaxis_title='Response (%)',
            yaxis_range=[0, 100],
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            template='plotly_white',
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='black', size=12),
            margin=dict(t=100)  # Add top margin for legend
        )
        
        return fig 