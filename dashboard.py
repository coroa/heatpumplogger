#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 22 09:02:57 2024

@author: and
"""
import os
import time
import pandas as pd
import numpy as np
from dash import Dash, dcc, html, Input, Output, callback
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from plotly.subplots import make_subplots
#%%
datapath = 'data'
mar = 10 #margin
#%% plot functions

def plot_temperatures(df, prefix):
    fig = go.Figure()

    line_style = dict(color='green', dash='dot', width=2)


    for colname in [x for x in df.columns if x.startswith(prefix)]:
        # print(hist_data.loc[:, colname])
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df.loc[:, colname],
                # line_color=cpf.config.variable_meta.loc[colname, 'plot_color'],
                # line=dict(
                #     color=cpf.config.variable_meta.loc[colname, 'plot_color'], width=1
                # ),
                hovertemplate=' %{y:2.2f}°C',
                name=colname,
            )
        )
    fig.update_layout(hovermode="x unified",
                      legend=dict(
                            yanchor="top",
                            y=0.99,
                            xanchor="left",
                            x=0.01),
                    margin=dict(l=mar, r=mar, t=mar, b=mar), 
                    


                    )
    fig.update_yaxes(automargin='left+top')

    return fig

def plot_heat_power(df):
    fig = go.Figure()

    line_style = dict(color='green', dash='dot', width=2)

    colors = ['Green', 'Blue']
    
    df['Leistung Heizen'] = df['Heizleistung Ist'].where(df['Betriebszustand']=='Heizen',0)
    df['Leistung Warmwasser'] = df['Heizleistung Ist'].where(df['Betriebszustand']=='WW',0)
    for colname in ['Leistung Heizen','Leistung Warmwasser']:
        # print(hist_data.loc[:, colname])
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df.loc[:, colname],
                # line_color=cpf.config.variable_meta.loc[colname, 'plot_color'],
                # line=dict(
                #     color=cpf.config.variable_meta.loc[colname, 'plot_color'], width=1
                # ),
                hovertemplate=' %{y:2.2f}kW',
                name=colname,
            )
        )
    fig.update_layout(hovermode="x unified",
                      legend=dict(
                            yanchor="top",
                            y=0.99,
                            xanchor="left",
                            x=0.01),
                    margin=dict(l=mar, r=mar, t=mar, b=mar),
                    )
    fig.update_yaxes(automargin='left+top')
    return fig

def plot_flow(df):
    fig = go.Figure()

    line_style = dict(color='green', dash='dot', width=2)


    for colname in ['Durchfluss']:
        # print(hist_data.loc[:, colname])
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df.loc[:, colname],
                # line_color=cpf.config.variable_meta.loc[colname, 'plot_color'],
                # line=dict(
                #     color=cpf.config.variable_meta.loc[colname, 'plot_color'], width=1
                # ),
                hovertemplate=' %{y:2.2f}%',
                name=colname,
            )
        )
    fig.update_layout(hovermode="x unified",
                      legend=dict(
                            yanchor="top",
                            y=0.99,
                            xanchor="left",
                            x=0.01),
                      margin=dict(l=mar, r=mar, t=mar, b=mar),
                      )
    fig.update_yaxes(automargin='left+top')
    return fig

def plot_defrost(df):
    fig = go.Figure()

    line_style = dict(color='green', dash='dot', width=2)


    for colname in ['Abtaubedarf']:
        # print(hist_data.loc[:, colname])
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df.loc[:, colname],
                # line_color=cpf.config.variable_meta.loc[colname, 'plot_color'],
                # line=dict(
                #     color=cpf.config.variable_meta.loc[colname, 'plot_color'], width=1
                # ),
                hovertemplate=' %{y:2.2f}%',
                name=colname,
            )
        )
    fig.update_layout(hovermode="x unified",
                      legend=dict(
                            yanchor="top",
                            y=0.99,
                            xanchor="left",
                            x=0.01),
                      margin=dict(l=mar, r=mar, t=mar, b=mar),
                      )
    fig.update_yaxes(automargin='left+top')
    return fig

def plot_energies(data_df):
    fig = make_subplots(specs=[[{"secondary_y": True}]])


    line_style = dict(color='green', dash='dot', width=2)


    for i, colname in enumerate(
            ['Eingesetzte Energie_Heizung', 'Wärmemenge_Heizung']
            ):
        # print(hist_data.loc[:, colname])
        fig.add_trace(
            go.Bar(
                x=data_df.index,
                y=data_df.loc[:, colname],
                # line_color=cpf.config.variable_meta.loc[colname, 'plot_color'],
                # line=dict(
                #     color=cpf.config.variable_meta.loc[colname, 'plot_color'], width=1
                # ),
                offsetgroup=i,
                hovertemplate=' %{y:2.2f} kWh',
                name=colname,
            )
        )
    for i,(colname,color) in enumerate(zip(
            ['Eingesetzte Energie_Warmwasser', 'Wärmemenge_Warmwasser'],
            ['maroon', 'darkblue']
            )):
        # print(hist_data.loc[:, colname])
        fig.add_trace(
            go.Bar(
                x=data_df.index,
                y=data_df.loc[:, colname],
                marker = dict(color=color),
                # line_color=cpf.config.variable_meta.loc[colname, 'plot_color'],
                # line=dict(
                #     color=cpf.config.variable_meta.loc[colname, 'plot_color'], width=1
                # ),
                offsetgroup=i,
                hovertemplate=' %{y:2.2f} kWh',
                name=colname,
            )
        )
    colors= {
        'COP_Heizung' :'Green',
        'COP_Warmwasser' :'darkgreen',
        }
    for colname in ['COP_Heizung', 'COP_Warmwasser']:
        # print(hist_data.loc[:, colname])
        fig.add_trace(
            go.Scatter(
                x=data_df.index,
                y=data_df.loc[:, colname],
                # line_color=cpf.config.variable_meta.loc[colname, 'plot_color'],
                # line=dict(
                #     color=cpf.config.variable_meta.loc[colname, 'plot_color'], width=1
                # ),
                mode='markers',
                marker=dict(
                    color=colors[colname],
                    size=20,
                    line=dict(
                        color='Yellow',
                        width=2
                    )
                ),
                hovertemplate=' %{y:2.2f} X',
                name=colname,
            ),
            secondary_y=True,
        )
    fig.update_layout(hovermode="x unified",
                      legend=dict(
                            yanchor="top",
                            y=0.99,
                            xanchor="left",
                            x=0.01),
                      margin=dict(l=mar, r=mar, t=mar, b=mar),
                      )
    fig.update_yaxes(automargin='left+top')
    # fig.update_traces(marker=dict(size=24,
    #                           line=dict(width=2,
    #                                     color='DarkSlateGrey')),
    #               selector=dict(mode='markers'))
    return fig

#%% Content

# @callback(
#     output=Output('sidebar_content', 'children'),
#     inputs=[

#         Input('day_dropdown', 'value'),
#     ],
# )
# def update_sidebar(day_dropdown):
#     html.Div(
#         children=[
            
#             ]
    
@callback(
    output=[
        Output('graph_content', 'children'),
        Output('sidebar_content', 'children')
        ],
    inputs=[

        Input('day_dropdown', 'value'),
    ],
)
def update_content(day_dropdown):
    # load data
    filepath = os.path.join(
            datapath,
            'log_' + day_dropdown + '.csv'
    )
    print(filepath)
    tt = time.time()
    df = pd.read_csv(
            filepath,
            index_col=0,
        )
    print(f"File loaded in {time.time()-tt}s")
    
    tt = time.time()
    
    today = pd.Timestamp.now().floor('d')
    data_date = pd.to_datetime(day_dropdown,format="%y-%m-%d")
    
    delta_time = today-data_date
    
    df.index = pd.DatetimeIndex(df.index) - delta_time
    # df = df.resample('1min').first()
    print(f"Data processed in {time.time()-tt}s")
    
    data_df = df[['Eingesetzte Energie_Heizung', 'Wärmemenge_Heizung',
                  'Wärmemenge_Warmwasser', 'Eingesetzte Energie_Warmwasser']].resample('60min').first().diff()
    
    data_df['COP_Heizung'] = data_df['Wärmemenge_Heizung'] / data_df['Eingesetzte Energie_Heizung']
    data_df['COP_Warmwasser'] = data_df['Wärmemenge_Warmwasser'] / data_df['Eingesetzte Energie_Warmwasser']
    
    

    # graphs.append(
        
    graph_content = html.Div(
        children=[
            html.H4('Heat Output'),
            dcc.Graph(
                figure=plot_heat_power(df)),
            html.H4('Heating temperatures'),
            dcc.Graph(
                figure=plot_temperatures(df, 
                                         prefix='Th'
                                         ),
                
                # config={'displayModeBar': False},
                style={'height': '50vh'},
            ),    
            html.H4('Hot water temperatures'),
            dcc.Graph(
                figure=plot_temperatures(df, prefix='Tw'),
                style={'height': '50vh'},
                # config={'displayModeBar': False},

            ),  
            # html.H4('Water flow'),
            # dcc.Graph(
            #     figure=plot_flow(df),
            #     style={'height': '50vh'},
            #     # config={'displayModeBar': False},

            # ),  
            html.H4('Ambient temperature'),
            dcc.Graph(
                figure=plot_temperatures(df, 
                                         prefix='Ta'
                                         ),
                # config={'displayModeBar': False},
                style={'height': '50vh'},
            ),   
            html.H4('Defreezing share'),
            dcc.Graph(
                figure=plot_defrost(df),
                # config={'displayModeBar': False},
                #style={'height': '50vh'},
            ),   
            html.H4('Energy input/output'),
            dcc.Graph(
                figure=plot_energies(data_df),
                # config={'displayModeBar': False},
                style={'height': '50vh'},
            ),   
            
        ]
        
        
    )
    
    #sample_values =pd.Series(df.index).diff().dt.total_seconds().fillna(0).cumsum().values
    
    # day_heat_output = np.trapezoid( df['Heizleistung Ist'],sample_values)/3600
    total_heat_output = data_df['Wärmemenge_Warmwasser'].sum() + data_df['Wärmemenge_Heizung'].sum()
    total_heating_output = data_df['Wärmemenge_Heizung'].sum()
    total_hotwater_output = data_df['Wärmemenge_Warmwasser'].sum() 
    
    total_heat_input = data_df['Eingesetzte Energie_Warmwasser'].sum() + data_df['Eingesetzte Energie_Heizung'].sum()
    total_heating_input = data_df['Eingesetzte Energie_Heizung'].sum()
    total_hotwater_input = data_df['Wärmemenge_Warmwasser'].sum() 
    
    overall_COP = total_heat_output / total_heat_input
    
    
    hours_running = (~df['Betriebszustand'].isna()).sum()/60
    sidebar_content = html.Div(
            children=[
                
                html.B('Overview :'),
                html.P(f'Time heating: {hours_running:2.2f} h'),
                html.P(f'COP: {overall_COP:2.2f}'),
                
                html.B('Thermal heat output :'),
                html.P(f'Total output: {total_heat_output:2.2f} kWh'),
                html.P(f'Total heating: {total_heating_output:2.2f} kWh'),
                html.P(f'Total hotwater: {total_hotwater_output:2.2f} kWh'),
                
                html.B('Electric input :'),
                html.P(f'Total input: {total_heat_input:2.2f} kWh'),
                html.P(f'Total heating: {total_heating_input:2.2f} kWh'),
                html.P(f'Total hotwater: {total_hotwater_input:2.2f} kWh'),
              
                ]
            )
    
    # return graphs
    return graph_content, sidebar_content


def graphs():
    return html.Div(id="graph_content")

def sidebar_content():
    days = [f.name[4:-4] for f in os.scandir(datapath)]
    days = sorted(days)
    content = html.Div(  # smaller now moved up beside the first block
        children = [
            dcc.Dropdown(
                days,
                days[-1],
                id='day_dropdown',
            ),
            html.Div(id="sidebar_content"),
        ]
    )
    
    return content


@callback(
    Output('day_dropdown', 'options'),
    Input('interval-component', 'n_intervals'),
    prevent_initial_call=True
)
def update(val):
    days = [f.name[4:-4] for f in os.scandir(datapath)]
    days = sorted(days)
    print('Updating options')
    return days
#%% Layout    
def construct_layout():
    print('constructing layout')
    # shared_data = Shared_data('DEU')
    # versions = shared_data.get_old_commits()
    # layout = html.Div(
    #             [
                
    #             html.Div(
    #                 [html.H3('Heatpump Dashboard')],
    #                 style={
    #                     'width': '100%',
    #                     # 'display': 'inline-block',
    #                     # 'verticalAlign': 'middle',
    #                 },
    #             ),
    #             html.Div(id='tabs-content-props'),
    #             ]
    #         )
    layout = html.Div([
        dbc.Row(html.Div(html.H1("Heatpump Dashboard"))),
        dbc.Row([
            dbc.Col(sidebar_content(),
                   width=2,
                   style={'background-color': '#ADD8E6',
                          }
                   ),
            dbc.Col([
                    #html.Div("Content"),
                    # graphs,
                    html.Div(id="graph_content"),
                    # dcc.Graph(id = 'Other'),
                    
                ])
        ]),
        dcc.Interval(
            id='interval-component',
            interval=60*1000,
            n_intervals=0
        ),
        ]
    )
    
    return layout


def dash_server():
    tt = time.time()
    print('Starting dash application:')

    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        )  # url_base_pathname="/ca_equity_explorer/")
    # server = app.server

    # shared_data = Shared_data('DEU')
    app.layout = construct_layout
    

    print(f'Dashboard init took {time.time()-tt:2.2f}s')

    app.run(
        debug=False,
        port=8887,
        host='0.0.0.0',
    )


if __name__ == '__main__':
    # app.run(debug=True)
    dash_server()