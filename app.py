import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.graph_objs as go
import settings
import itertools
import math
import base64
from flask import Flask
import os
import datetime
 
import re
import nltk
nltk.download('punkt')
nltk.download('stopwords')
from nltk.probability import FreqDist
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from textblob import TextBlob

# external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
# # meta_tags are required for the app layout to be mobile responsive
# app = dash.Dash(__name__, suppress_callback_exceptions=True,
#                 external_stylesheets=external_stylesheets,
#                 meta_tags=[{'name': 'viewport',
#                             'content': 'width=device-width, initial-scale=1.0'}]
#                 )
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.title = 'Real-Time Twitter Monitor'

server = app.server
app.layout = html.Div(children=[
    html.H2('Real-time Twitter Sentiment Analysis for Brand Improvement and Topic Tracking ', style={
        'textAlign': 'center'
    }),
    html.Div(id='live-update-graph'),
    html.Div(id='live-update-graph-bottom'),
        dcc.Interval(
        id='interval-component-slow',
        interval=1*10000, # in milliseconds
        n_intervals=0
    )

    ], style={'padding': '20px'})



# Multiple components can update everytime interval gets fired.
@app.callback(Output('live-update-graph', 'children'),
              [Input('interval-component-slow', 'n_intervals')])
def update_graph_live(n):

    df = pd.read_csv('tsla_df_day.csv')
    df['created_at'] = pd.to_datetime(df['created_at'])
    # # Convert UTC into PDT
    # df['created_at'] = pd.to_datetime(df['created_at']).apply(lambda x: x - datetime.timedelta(hours=7))
    
    # Clean and transform data to enable time series
    result = df.groupby([pd.Grouper(key='created_at', freq='10s'), 'polarity']).count().unstack(fill_value=0).stack().reset_index()
    result = result.rename(columns={"id_str": "Num of '{}' mentions".format(settings.TRACK_WORDS[0]), "created_at":"Time"})  
    time_series = result["Time"][result['polarity']==0].reset_index(drop=True)

    min10 = datetime.datetime.now() - datetime.timedelta(hours=7, minutes=10)
    min20 = datetime.datetime.now() - datetime.timedelta(hours=7, minutes=20)

    neu_num = result[result['Time']>min10]["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][result['polarity']==0].sum()
    neg_num = result[result['Time']>min10]["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][result['polarity']==-1].sum()
    pos_num = result[result['Time']>min10]["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][result['polarity']==1].sum()
    


    # Percentage Number of Tweets changed in Last 10 mins

    count_now = df[df['created_at'] > min10]['id_str'].count()
    count_before = df[ (min20 < df['created_at']) & (df['created_at'] < min10)]['id_str'].count()
    percent = (count_now-count_before)/count_before*100
    # Create the graph 
    children = [
                html.Div([
                    html.Div([
                        dcc.Graph(
                            id='crossfilter-indicator-scatter',
                            figure={
                                'data': [
                                    go.Scatter(
                                        x=time_series,
                                        y=result["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][result['polarity']==0].reset_index(drop=True),
                                        name="Neutrals",
                                        opacity=0.8,
                                        mode='lines',
                                        line=dict(width=0.5, color='rgb(131, 90, 241)'),
                                        stackgroup='one' 
                                    ),
                                    go.Scatter(
                                        x=time_series,
                                        y=result["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][result['polarity']==-1].reset_index(drop=True).apply(lambda x: -x),
                                        name="Negatives",
                                        opacity=0.8,
                                        mode='lines',
                                        line=dict(width=0.5, color='rgb(255, 50, 50)'),
                                        stackgroup='two' 
                                    ),
                                    go.Scatter(
                                        x=time_series,
                                        y=result["Num of '{}' mentions".format(settings.TRACK_WORDS[0])][result['polarity']==1].reset_index(drop=True),
                                        name="Positives",
                                        opacity=0.8,
                                        mode='lines',
                                        line=dict(width=0.5, color='rgb(184, 247, 212)'),
                                        stackgroup='three' 
                                    )
                                ]
                            }
                        )
                    ], style={'width': '73%', 'display': 'inline-block', 'padding': '0 0 0 20'}),
                    
                    html.Div([
                        dcc.Graph(
                            id='pie-chart',
                            figure={
                                'data': [
                                    go.Pie(
                                        labels=['Positives', 'Negatives', 'Neutrals'], 
                                        values=[pos_num, neg_num, neu_num],
                                        name="View Metrics",
                                        marker_colors=['rgba(184, 247, 212, 0.6)','rgba(255, 50, 50, 0.6)','rgba(131, 90, 241, 0.6)'],
                                        textinfo='value',
                                        hole=.65)
                                ],
                                'layout':{
                                    'showlegend':False,
                                    'title':'Tweets In Last 10 Mins',
                                    'annotations':[
                                        dict(
                                            text='{0:.1f}K'.format((pos_num+neg_num+neu_num)/1000),
                                            font=dict(
                                                size=40
                                            ),
                                            showarrow=False
                                        )
                                    ]
                                }

                            }
                        )
                    ], style={'width': '27%', 'display': 'inline-block'})
                ]),
                
                html.Div(
                    className='row',
                    children=[
                        html.Div(
                            children=[
                                html.P('Tweets/10 Mins Changed By',
                                    style={
                                        'fontSize': 17
                                    }
                                ),
                                html.P('{0:.2f}%'.format(percent) if percent <= 0 else '+{0:.2f}%'.format(percent),
                                    style={
                                        'fontSize': 40
                                    }
                                )
                            ], 
                            style={
                                'width': '20%', 
                                'display': 'inline-block'
                            }

                        ),
                        html.Div(
                            children=[
                                html.P('Potential Impressions Today',
                                    style={
                                        'fontSize': 17
                                    }
                                ),
                                html.P('{0:.1f}K'.format(daily_impressions/1000) \
                                        if daily_impressions < 1000000 else \
                                            ('{0:.1f}M'.format(daily_impressions/1000000) if daily_impressions < 1000000000 \
                                            else '{0:.1f}B'.format(daily_impressions/1000000000)),
                                    style={
                                        'fontSize': 40
                                    }
                                )
                            ], 
                            style={
                                'width': '20%', 
                                'display': 'inline-block'
                            }
                        ),
                        html.Div(
                            children=[
                                html.P('Tweets Posted Today',
                                    style={
                                        'fontSize': 17
                                    }
                                ),
                                html.P('{0:.1f}K'.format(daily_tweets_num/1000),
                                    style={
                                        'fontSize': 40
                                    }
                                )
                            ], 
                            style={
                                'width': '20%', 
                                'display': 'inline-block'
                            }
                        ),

                        html.Div(
                            children=[
                                html.P("Currently tracking \"Facebook\" brand (NASDAQ: FB) on Twitter in Pacific Daylight Time (PDT).",
                                    style={
                                        'fontSize': 25
                                    }
                                ),
                            ], 
                            style={
                                'width': '40%', 
                                'display': 'inline-block'
                            }
                        ),

                    ],
                    style={'marginLeft': 70}
                )
            ]
    return children


@app.callback(Output('live-update-graph-bottom', 'children'),
              [Input('interval-component-slow', 'n_intervals')])
def update_graph_bottom_live(n):

    df = pd.read_csv('tsla_df_day.csv')
    df['created_at'] = pd.to_datetime(df['created_at'])
    # # Convert UTC into PDT
    # df['created_at'] = pd.to_datetime(df['created_at']).apply(lambda x: x - datetime.timedelta(hours=7))

    # Clean and transform data to enable word frequency
    content = ' '.join(df["text"])
    content = re.sub(r"http\S+", "", content)
    content = content.replace('RT ', ' ').replace('&amp;', 'and')
    content = re.sub('[^A-Za-z0-9]+', ' ', content)
    content = content.lower()

    # Filter constants for states in US
    STATES = ['Alabama', 'AL', 'Alaska', 'AK', 'American Samoa', 'AS', 'Arizona', 'AZ', 'Arkansas', 'AR', 'California', 'CA', 'Colorado', 'CO', 'Connecticut', 'CT', 'Delaware', 'DE', 'District of Columbia', 'DC', 'Federated States of Micronesia', 'FM', 'Florida', 'FL', 'Georgia', 'GA', 'Guam', 'GU', 'Hawaii', 'HI', 'Idaho', 'ID', 'Illinois', 'IL', 'Indiana', 'IN', 'Iowa', 'IA', 'Kansas', 'KS', 'Kentucky', 'KY', 'Louisiana', 'LA', 'Maine', 'ME', 'Marshall Islands', 'MH', 'Maryland', 'MD', 'Massachusetts', 'MA', 'Michigan', 'MI', 'Minnesota', 'MN', 'Mississippi', 'MS', 'Missouri', 'MO', 'Montana', 'MT', 'Nebraska', 'NE', 'Nevada', 'NV', 'New Hampshire', 'NH', 'New Jersey', 'NJ', 'New Mexico', 'NM', 'New York', 'NY', 'North Carolina', 'NC', 'North Dakota', 'ND', 'Northern Mariana Islands', 'MP', 'Ohio', 'OH', 'Oklahoma', 'OK', 'Oregon', 'OR', 'Palau', 'PW', 'Pennsylvania', 'PA', 'Puerto Rico', 'PR', 'Rhode Island', 'RI', 'South Carolina', 'SC', 'South Dakota', 'SD', 'Tennessee', 'TN', 'Texas', 'TX', 'Utah', 'UT', 'Vermont', 'VT', 'Virgin Islands', 'VI', 'Virginia', 'VA', 'Washington', 'WA', 'West Virginia', 'WV', 'Wisconsin', 'WI', 'Wyoming', 'WY']
    STATE_DICT = dict(itertools.zip_longest(*[iter(STATES)] * 2, fillvalue=""))
    INV_STATE_DICT = dict((v,k) for k,v in STATE_DICT.items())

    # Clean and transform data to enable geo-distribution
    is_in_US=[]
    geo = df[['user_location']]
    df = df.fillna(" ")
    for x in df['user_location']:
        check = False
        for s in STATES:
            if s in x:
                is_in_US.append(STATE_DICT[s] if s in STATE_DICT else s)
                check = True
                break
        if not check:
            is_in_US.append(None)

    geo_dist = pd.DataFrame(is_in_US, columns=['State']).dropna().reset_index()
    geo_dist = geo_dist.groupby('State').count().rename(columns={"index": "Number"}) \
        .sort_values(by=['Number'], ascending=False).reset_index()
    geo_dist["Log Num"] = geo_dist["Number"].apply(lambda x: math.log(x, 2))


    geo_dist['Full State Name'] = geo_dist['State'].apply(lambda x: INV_STATE_DICT[x])
    geo_dist['text'] = geo_dist['Full State Name'] + '<br>' + 'Num: ' + geo_dist['Number'].astype(str)


    tokenized_word = word_tokenize(content)
    stop_words=set(stopwords.words("english"))
    filtered_sent=[]
    for w in tokenized_word:
        if (w not in stop_words) and (len(w) >= 3):
            filtered_sent.append(w)
    fdist = FreqDist(filtered_sent)
    fd = pd.DataFrame(fdist.most_common(16), columns = ["Word","Frequency"]).drop([0]).reindex()
    fd['Polarity'] = fd['Word'].apply(lambda x: TextBlob(x).sentiment.polarity)
    fd['Marker_Color'] = fd['Polarity'].apply(lambda x: 'rgba(255, 50, 50, 0.6)' if x < -0.1 else \
        ('rgba(184, 247, 212, 0.6)' if x > 0.1 else 'rgba(131, 90, 241, 0.6)'))
    fd['Line_Color'] = fd['Polarity'].apply(lambda x: 'rgba(255, 50, 50, 1)' if x < -0.1 else \
        ('rgba(184, 247, 212, 1)' if x > 0.1 else 'rgba(131, 90, 241, 1)'))



    # Create the graph 
    children = [
                html.Div([
                    dcc.Graph(
                        id='x-time-series',
                        figure = {
                            'data':[
                                go.Bar(                          
                                    x=fd["Frequency"].loc[::-1],
                                    y=fd["Word"].loc[::-1], 
                                    name="Neutrals", 
                                    orientation='h',
                                    marker_color=fd['Marker_Color'].loc[::-1].to_list(),
                                    marker=dict(
                                        line=dict(
                                            color=fd['Line_Color'].loc[::-1].to_list(),
                                            width=1),
                                        ),
                                )
                            ],
                            'layout':{
                                'hovermode':"closest"
                            }
                        }        
                    )
                ], style={'width': '49%', 'display': 'inline-block', 'padding': '0 0 0 20'}),
                html.Div([
                    dcc.Graph(
                        id='y-time-series',
                        figure = {
                            'data':[
                                go.Choropleth(
                                    locations=geo_dist['State'], # Spatial coordinates
                                    z = geo_dist['Log Num'].astype(float), # Data to be color-coded
                                    locationmode = 'USA-states', # set of locations match entries in `locations`
                                    #colorscale = "Blues",
                                    text=geo_dist['text'], # hover text
                                    geo = 'geo',
                                    colorbar_title = "Num in Log2",
                                    marker_line_color='white',
                                    colorscale = ["#fdf7ff", "#835af1"],
                                    #autocolorscale=False,
                                    #reversescale=True,
                                ) 
                            ],
                            'layout': {
                                'title': "Geographic Segmentation for US",
                                'geo':{'scope':'usa'}
                            }
                        }
                    )
                ], style={'display': 'inline-block', 'width': '49%'})
            ]
        
    return children


if __name__ == '__main__':
    app.run_server(debug=True)
    