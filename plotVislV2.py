from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
# from langchain_openai import ChatOpenAI
from dash import Dash, html, dcc, callback, Output, Input, State
from flask import Flask
import pandas as pd
import re
from dotenv import find_dotenv, load_dotenv
import os

flask_server=Flask(__name__)
# Load the API key
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Load the dataset
df = pd.read_excel(r"SummaryDatabyweek.xlsx") 
# print(df)              
df_5_rows = df.head()
print(df_5_rows)
csv_string = df_5_rows.to_string(index=False)
print(csv_string)

#Choose the model
model = ChatGroq(
    api_key=GROQ_API_KEY, 
    model="Llama3-70b-8192",
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system",
         "You're a data visualization expert and use your favourite graphing library Plotly only. Suppose, that"
         "the data is provided as a SummaryDatabyweek.xlsx file. Here are the first 5 rows of the data set: (data) "
         "Follow the user's indications when creating the graph."
        ),   
        MessagesPlaceholder(variable_name="messages"),
    ]
)

chain = prompt | model

def get_fig_from_code(code):
    local_variables = {}
    exec(code, {}, local_variables)
    return local_variables['fig']

app = Dash(__name__, server=flask_server)
server = app.server

app.layout = html.Div([
    html.Div([
        dcc.Textarea(id='user-request', style={'width': '70%', 'height': 50, 'margin-top': 20}),
        html.Button('Generate', id='my-button', style={'margin-left': '10px', 'height': '50px', 'margin-left': '10px','border-radius': '25px','background-color': 'SlateBlue','color': 'white','border': None,'cursor': 'pointer','font-size': '16px','padding': '0 20px'})
    ], style={'display': 'flex', 'align-items': 'center'}),
    html.Br(),
    dcc.Loading([
        html.Div(id='my-figure', children=''),
        dcc.Markdown(id='content', children="")
    ], type='cube')
])


@callback(
    [Output('my-figure', 'children'),Output('content','children')],
    [Input('my-button', 'n_clicks')],
    [State('user-request', 'value')],
    prevent_initial_call=True
)
def create_graph(n_clicks, user_input):
    response = chain.invoke(
        {
            "messages": [HumanMessage(content=user_input)],
            "data": csv_string
        },
    )
    result_output = response.content

    # Extract code block from the response
    code_block_match = re.search(r'```(?:[Pp]ython)?(.*?)```', result_output, re.DOTALL)
    # print(code_block_match)

    # If code is included, extract the figure created
    if code_block_match:
        code_block = code_block_match.group(1).strip()
        cleaned_code = re.sub(r'(?m)^\s*fig\.show\(\)\s*$', '', code_block)
        print(cleaned_code)
        # Correct column names in the generated code
        for col in df.columns:
            cleaned_code = cleaned_code.replace('Column1', col)

        fig = get_fig_from_code(cleaned_code)

        graph = dcc.Graph(figure=fig)
        return graph , ""
    else: 
        return "" , result_output

if __name__ == '__main__':
    app.run_server(debug=False, port=8009)
