from dash import Dash, dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from dotenv import find_dotenv, load_dotenv
from flask import Flask
import pandas as pd
import os , sys
import re
import base64
import io
import layout
import datetime
import logging

#initialize flask
flask_server = Flask(__name__)

# External stylesheets for Dash app
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# Initialize Dash app
app = Dash(__name__, server=flask_server, external_stylesheets=external_stylesheets)
server = app.server

# Load the API key
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

model = ChatGroq(
    api_key=GROQ_API_KEY, 
    model="Llama3-70b-8192")

prompt = ChatPromptTemplate.from_messages(
    [
        ("system",
         "You're a data visualization expert and use your favourite graphing library Plotly only. Suppose, that"
         "the data is provided as a {stored_filename} file. Here are the first 5 rows of the data set: (data) "
         "Follow the user's indications when creating the graph."
        ),   
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# Chain the prompt with the model
chain = prompt | model

# Global variables for storing data and file information
stored_data = None
stored_filename = None
csv_str = None

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Ensure logs are output to standard output
    ]
)                      

# Define the layout of the Dash app
app.layout = layout.create_layout()

# Callback to handle file upload and processing
@callback(Output('output-data-upload', 'children'),
          Input('upload-data', 'contents'),
          State('upload-data', 'filename'),
          State('upload-data', 'last_modified'))


def parse_contents(contents, filename, date):
    global stored_data, stored_filename, csv_str

    if contents is None:
        return html.Div(['No file uploaded yet.'])

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    try:
        if 'csv' in filename:

            # Assume that the user uploaded a CSV file
            print(io.StringIO(decoded.decode('utf-8')))
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            print("file upload successfully")
            df.to_csv('/tmp/'+filename)

        elif 'xls' in filename or 'xlsx' in filename:

            # Assume that the user uploaded an Excel file
            print(io.BytesIO(decoded))
            df = pd.read_excel(io.BytesIO(decoded),sheet_name=None, engine='openpyxl')
            combined_df = pd.concat(df.values(), ignore_index=False)
            unnamed_cols = [col for col in combined_df.columns if col.startswith("Unnamed:")]
            df = combined_df.drop(unnamed_cols, axis=1)
            print("file upload successfully")
            df.to_excel('/tmp/'+filename)

        else:
            return html.Div(['Unsupported file format. Please upload a CSV or Excel file.']), dbc.Toast("Unsupported file format. Please upload a CSV or Excel file.", header="Error", duration=4000)
        
    except Exception as e:
        return html.Div(['There was an error processing this file.', str(e)]), dbc.Toast(f"There was an error processing this file: {str(e)}", header="Error", duration=4000)


    # Store the processed data and filename
    stored_data = df
    csv_str = stored_data.to_csv(index=False)

    stored_filename = '/tmp/'+filename

    table = dash_table.DataTable(
        data=stored_data.head(5).to_dict('records'),
        columns=[{'name': col, 'id': col} for col in stored_data.columns],
        style_table={'overflowX': 'auto'},
        style_cell={
            'height': 'auto',
            'minWidth': '50px', 'width': '100px', 'maxWidth': '200px',
            'whiteSpace': 'normal',
            'padding': '5px',
            'font-family': 'Arial',
            'font-size': '12px'
        },
        style_header={
            'backgroundColor': 'lightgrey',
            'fontWeight': 'bold'
        },
        style_data={
            'backgroundColor': 'white',
            'border': '1px solid lightgrey'
        }
    )

    return html.Div([
        html.H5(filename),
        # html.H6(datetime.datetime.fromtimestamp(date)),
        # html.Div('File uploaded and processed successfully.'),
        table
    ]), dbc.Toast("File uploaded and processed successfully.", header="Success", duration=4000)
 
# Callback to handle graph generation based on user input
@callback(
    [Output('my-figure', 'children'), Output('content', 'children'), Output('toast1', 'children')],
    [Input('my-button', 'n_clicks')],
    [State('user-request', 'value')],
    prevent_initial_call=True
)

def create_graph(n_clicks, user_input):
    global csv_str, stored_filename

    if csv_str is None:
        return '', 'No data available to generate the graph.'
    
    # Invoke LangChain model with user input and data
    try:
        response = chain.invoke({
            "messages": [HumanMessage(content=user_input)],
            "data": csv_str,
            "stored_filename": stored_filename
        })
        result_output = response.content

        # Extract code block from the response
        code_block_match = re.search(r'```(?:[Pp]ython)?(.*?)```', result_output, re.DOTALL)

        # If code is included, extract the figure created
        if code_block_match:
            code_block = code_block_match.group(1).strip()
            print(code_block)
            cleaned_code = re.sub(r'(?m)^\s*fig\.show\(\)\s*$', '', code_block)
            print(cleaned_code)

            # Correct column names in the generated code
            for col in stored_data.columns:
                cleaned_code = cleaned_code.replace('Column1', col)

            # Add imports for Plotly and statsmodels
            cleaned_code = "import plotly.express as px\nimport statsmodels.api as sm\n" + cleaned_code
            
            # Execute the cleaned code to get the Plotly figure
            local_variables = {}
            exec(cleaned_code, {}, local_variables)
            fig = local_variables['fig']

            # Display the Plotly figure
            graph = dcc.Graph(figure=fig)
            return graph, "", dbc.Toast("Graph generated successfully.", header="Success", duration=4000)
        else:
            return "", result_output, dbc.Toast("No valid code block found in the response.", header="Error", duration=4000)
        
    except Exception as e:
        logging.error(f'Error executing generated code: {str(e)}')
        return "", "", dbc.Toast(f"Please give it another try, and we’re confident it will work smoothly", header="Please Try Again")

# Main entry point for running the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)
