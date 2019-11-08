import os
import pandas as pd
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import dash_table

from sqlalchemy import create_engine

db_host = os.environ.get('HOST')
db_name = os.environ.get('DB_NAME')
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASS')

connection_string = f'postgresql://{db_user}:{db_password}@{db_host}/{db_name}'

engine = create_engine(connection_string)

df = pd.read_sql('Select * from trades', engine.connect(), parse_dates=['Entry time'])

external_stylesheets = ['https://codepen.io/uditagarwal/pen/oNvwKNP.css',
                        'https://codepen.io/uditagarwal/pen/YzKbqyV.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(
    children=[
        html.Div(
            children=[
                html.H2(children='Bitcoin Leveraged Trading Backtest Analysis',
                        className='h2-title')
            ],
            className='study-browser-banner row'),
        html.Div(
            className='row-app-body',
            children=[
                html.Div(
                    className='twelve columns card',
                    children=[
                        html.Div(
                            className='padding-row',
                            children=[
                                html.Div(
                                    className='two columns card',
                                    children=[
                                        html.H6('Select Exchange', ),
                                        dcc.RadioItems(
                                            id='exchange-select',
                                            options=[{'label': label, 'value': label} for label in df['Exchange'].unique()],
                                            value='Bitmex',
                                            labelStyle={'display': 'inline-block'}
                                        )
                                    ]
                                ),
                                html.Div(
                                    className='two columns card 2',
                                    children=[
                                        html.H6('Select Leverage', ),
                                        dcc.RadioItems(
                                            id='leverage-select',
                                            options=[{'label': label, 'value': label} for label in df['Margin'].unique()],
                                            value=1,
                                            labelStyle={'display': 'inline-block'}
                                        )
                                    ]
                                ),
                                html.Div(
                                    className='three columns card',
                                    children=[
                                        html.H6('Select a Date Range'),
                                        dcc.DatePickerRange(
                                            id='date-range-select',
                                            start_date=df['Entry time'].min(),
                                            end_date=df['Entry time'].max(),
                                            display_format='MMM YY',
                                            initial_visible_month=df['Entry time'].min(),
                                            number_of_months_shown=2
                                        )
                                    ]
                                ),
                                html.Div(
                                    id='strat-returns-div',
                                    className='two columns indicator pretty_container',
                                    children=[
                                        html.Strong(id='strat-returns', className='indicator_value'),
                                        html.H6('Strategy Returns')
                                    ]
                                ),
                                html.Div(
                                    id='market-returns-div',
                                    className='two columns indicator pretty_container',
                                    children=[
                                        html.Strong(id='market-returns', className='indicator_value'),
                                        html.H6('Market Returns')
                                    ]
                                ),
                                html.Div(
                                    id='strat-vs-market-div',
                                    className='two columns indicator pretty_container',
                                    children=[
                                        html.Strong(id='strat-vs-market', className='indicator_value'),
                                        html.H6('Returns vs. Market')
                                    ]
                                ),
                            ]
                        )
                    ]
                )
            ]
        ),
        html.Div(
            className='twelve columns card',
            children=[
                dcc.Graph(
                    id='monthly-chart',
                    figure={
                        'data': list()
                    }
                )
            ]
        ),
        html.Div(
            className='padding row',
            children=[
                html.Div(
                    className='six columns card',
                    children=[
                        dash_table.DataTable(
                            id='table',
                            columns=[
                                {'name': 'Number', 'id': 'Number'},
                                {'name': 'Trade type', 'id': 'Trade type'},
                                {'name': 'Exposure', 'id': 'Exposure'},
                                {'name': 'Entry balance', 'id': 'Entry balance'},
                                {'name': 'Exit balance', 'id': 'Exit balance'},
                                {'name': 'Pnl (incl fees)', 'id': 'Pnl (incl fees)'}
                            ],
                            style_cell={'width': '50px'},
                            style_table={
                                'maxHeight': '450px',
                                'overflowY': 'scroll'
                            }
                        )
                    ]
                ),
                dcc.Graph(
                    id='pnl-types',
                    className='six columns card'
                )
            ]
        ),
        html.Div(
            className="twelve columns card",
            children=[
                dcc.Graph(
                    id="daily-btc",
                    className="six columns card",
                    figure={}
                ),
                dcc.Graph(
                    id="balance",
                    className="six columns card",
                    figure={}
                )
            ]
        )
    ]
)


def get_filter_df(exchange, margin, start_date, end_date):
    return df[(df['Exchange'] == exchange)
              & (df['Margin'] == margin)
              & (df['Entry time'].between(start_date, end_date))]


@app.callback(
    [
        Output('date-range-select', 'start_date'),
        Output('date-range-select', 'end_date')
    ],
    [Input('exchange-select', 'value')]

)
def update_dates(exchange):
    time_series = df[df['Exchange'] == exchange]['Entry time']
    return time_series.min(), time_series.max()


def get_btc_returns(df_):
    initial_value = df_.iloc[-1]['BTC Price']
    end_value = df_.iloc[0]['BTC Price']
    return 100.0*end_value/initial_value - 100


def get_strat_returns(df_):
    initial_value = df_.iloc[-1]['Entry balance']
    end_value = df_.iloc[0]['Exit balance']
    return 100.0*end_value/initial_value - 100


def get_return_over_month(df_):
    df_['YearMonth'] = pd.to_datetime(df_['Entry time'].map(lambda x: "{}-{}".format(x.year, x.month)))
    out = list()
    for month, group in df_.groupby('YearMonth'):
        entry_balance = group.iloc[-1]['Entry balance']
        exit_balance = group.iloc[0]['Exit balance']
        monthly_return = 100.0*exit_balance/entry_balance - 100
        out.append(
            {
                'month': month,
                'open': entry_balance,
                'close': exit_balance,
                'return': monthly_return
            }
        )
    return out


# @app.callback(
#     [
#         Output('monthly-chart', 'figure'),
#         Output('table', 'data'),
#         Output('pnl-types', 'figure'),
#         Output('daily-btc', 'figure'),
#         Output('market-returns', 'children'),
#         Output('strat-returns', 'children'),
#         Output('strat-vs-market', 'children'),
#         Output('balance', 'figure'),
#     ],
#     [
#         Input('exchange-select', 'value'),
#         Input('leverage-select', 'value'),
#         Input('date-range-select', 'start_date'),
#         Input('date-range-select', 'end_date')
#     ]
# )
# def update_data(exchange, margin, start_date, end_date):
#     filter_df = get_filter_df(exchange, margin, start_date, end_date)
#     btc_returns = get_btc_returns(filter_df)
#     strat_returns = get_strat_returns(filter_df)
#     strat_vs_market = strat_returns - btc_returns
#
#
#
#     return f'{btc_returns:0.2f}%', f'{strat_returns:0.2f}%', f'{strat_vs_market:0.2f}%'


def update_monthly_chart(dff):
    data = get_return_over_month(dff)
    open_, close, months = list(), list(), list()
    for each in data:
        open_.append(each['open'])
        close.append(each['close'])
        months.append(each['month'])
    fig = {
        'data': [go.Candlestick(open=open_, close=close, x=months,
                                low=open_, high=close)],
        'layout': go.Layout(title='Overview of Monthly performance')
    }
    return fig


@app.callback(
    [
        Output('monthly-chart', 'figure'),
        Output('market-returns', 'children'),
        Output('strat-returns', 'children'),
        Output('strat-vs-market', 'children'),
    ],
    [
        Input('exchange-select', 'value'),
        Input('leverage-select', 'value'),
        Input('date-range-select', 'start_date'),
        Input('date-range-select', 'end_date')
    ]
)
def update_figure(exchange, margin, start_date, end_date):
    filter_df = get_filter_df(exchange, margin, start_date, end_date)
    data = get_return_over_month(filter_df)
    btc_returns = get_btc_returns(filter_df)
    strat_returns = get_strat_returns(filter_df)
    strat_vs_market = strat_returns - btc_returns
    open_, close, months = list(), list(), list()
    for each in data:
        open_.append(each['open'])
        close.append(each['close'])
        months.append(each['month'])
    return {
        'data': [
            go.Candlestick(
                open=open_,
                close=close,
                x=months,
                low=open_,
                high=close
            )
        ],
        'layout':
            go.Layout(
                title='Overview of Monthly performance',

            )
    }, f'{btc_returns:0.2f}%', f'{strat_returns:0.2f}%', f'{strat_vs_market:0.2f}%'


@app.callback(
    Output('table', 'data'),
    (
        Input('exchange-select', 'value'),
        Input('leverage-select', 'value'),
        Input('date-range-select', 'start_date'),
        Input('date-range-select', 'end_date')
    )
)
def update_table(exchange, leverage, start_date, end_date):
    dff = get_filter_df(exchange, leverage, start_date, end_date)
    return dff.to_dict('records')


@app.callback(
    Output('pnl-types', 'figure'),
    [
        Input('exchange-select', 'value'),
        Input('leverage-select', 'value'),
        Input('date-range-select', 'start_date'),
        Input('date-range-select', 'end_date')
    ]
)
def update_bar_chart(exchange, leverage, start_date, end_date):
    dff = get_filter_df(exchange, leverage, start_date, end_date)
    data = list()
    for type_ in dff['Trade type'].unique():
        df_ = dff[dff['Trade type'] == type_]
        df_['Day'] = pd.to_datetime(df_['Entry time'].map(lambda x: '{}-{}-{}'.format(x.year, x.month, x.day)))
        df_ = df_.groupby('Day').sum()
        data.append(
            go.Bar(
                x=df_.index,
                y=df_['Pnl (incl fees)'],
                name=type_
            )
        )
    return {
        'data': data,
        'layout':
            go.Layout(
                title='PnL vs Trade type',
                height=400,
                colorway=['#000000', '#EF963B']
            )
    }


@app.callback(
    Output('daily-btc', 'figure'),
    [
        Input('date-range-select', 'start_date'),
        Input('date-range-select', 'end_date')
    ]
)
def update_daily_btc(start_date, end_date):
    dff = df[df['Entry time'].between(start_date, end_date)]
    dff['Day'] = pd.to_datetime(dff['Entry time'].map(lambda x: "{}-{}-{}".format(x.year, x.month, x.day)))
    dff = dff.groupby('Day').max()
    return {
        'data': [
            dict(
                x=dff['Entry time'],
                y=dff['BTC Price']
            ),
        ],
        'layout':
            go.Layout(
                title='Daily BTC Price',
		height=400
            )
    }


@app.callback(
    Output('balance', 'figure'),
    [
        Input('exchange-select', 'value'),
        Input('leverage-select', 'value'),
        Input('date-range-select', 'start_date'),
        Input('date-range-select', 'end_date')
    ]
)
def update_balance(exchange, leverage, start_date, end_date):
    dff = get_filter_df(exchange, leverage, start_date, end_date)
    return {
        'data': [
            dict(
                x=dff['Entry time'],
                y=dff['Exit balance']
            )
        ],
        'layout':
            go.Layout(
                title='Balance overtime',
		height=400
            )
    }


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
