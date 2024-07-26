from dash import dcc, html

def create_layout():
    layout = html.Div([
        dcc.Upload(
            id='upload-data',
            children = 
            html.Button('Upload File'),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'border': None,
                'borderRadius': '5px',
                'textAlign': 'center',
            }
        ),
        dcc.Loading([
            html.Div(id='output-data-upload'),
            html.Hr()], type='circle'),
        

        # User input textarea and Generate button
        html.Div([
            dcc.Textarea(id='user-request', style={'width': '70%', 'height': 50, 'margin-top': 20}),
            html.Button('Generate', id='my-button', style={
                'margin-left': '10px',
                'height': '50px',
                'border-radius': '25px',
                'background-color': 'SlateBlue',
                'color': 'white',
                'border': None,
                'cursor': 'pointer',
                'font-size': '16px',
                'padding': '0 20px'
            })
        ], style={'display': 'flex', 'align-items': 'center'}),
        html.Br(),

        # Loading component for displaying graph and content
        dcc.Loading([
            html.Div(id='toast1', children=''),
            html.Div(id='my-figure', children=''),
            dcc.Markdown(id='content', children="")
        ], type='cube')
    ])

    return layout