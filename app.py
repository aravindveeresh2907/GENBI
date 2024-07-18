from dash import Dash, dcc, html, Input, Output, State, callback, dash_table
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from dotenv import find_dotenv, load_dotenv
from flask import Flask
import pandas as pd
import os
import re
import base64
import io
import layout

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
# Initialize LangChain model
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
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
            print("file upload successfully")
        elif 'xls' in filename or 'xlsx' in filename:
            # Assume that the user uploaded an Excel file
            df = pd.read_excel(io.BytesIO(decoded),sheet_name=None)
            combined_df = pd.concat(df.values(), ignore_index=False)
            unnamed_cols = [col for col in combined_df.columns if col.startswith("Unnamed:")]
            df = combined_df.drop(unnamed_cols, axis=1)
            print("file upload successfully")
        else:
            return html.Div(['Unsupported file format. Please upload a CSV or Excel file.'])
    except Exception as e:
        print(e)
        return html.Div(['There was an error processing this file.'])

    # Store the processed data and filename
    stored_data = df
    csv_str = stored_data.to_csv(index=False)
    stored_filename = filename

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
        html.H6(datetime.datetime.fromtimestamp(date)),
        html.Div('File uploaded and processed successfully.'),
        table
    ])
 
    
# Callback to handle graph generation based on user input
@callback(
    [Output('my-figure', 'children'), Output('content', 'children')],
    [Input('my-button', 'n_clicks')],
    [State('user-request', 'value')],
    prevent_initial_call=True
)
def create_graph(n_clicks, user_input):
    global csv_str, stored_filename

    if csv_str is None:
        return '', 'No data available to generate the graph.'

    # Invoke LangChain model with user input and data
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
        cleaned_code = re.sub(r'(?m)^\s*fig\.show\(\)\s*$', '', code_block)

        # Correct column names in the generated code
        for col in stored_data.columns:
            cleaned_code = cleaned_code.replace('Column1', col)

        # Execute the cleaned code to get the Plotly figure
        local_variables = {}
        exec(cleaned_code, {}, local_variables)
        fig = local_variables['fig']

        # Display the Plotly figure
        graph = dcc.Graph(figure=fig)
        return graph, ""
    else:
        return "", result_output

# Main entry point for running the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)
