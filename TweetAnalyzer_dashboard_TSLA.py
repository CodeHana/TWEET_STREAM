# Load data from MySQL to perform exploratory data analysis
import settings
import mysql.connector
import pandas as pd
import time
import itertools
import math

import seaborn as sns
import matplotlib.pyplot as plt
#%matplotlib inline
import plotly.express as px
import datetime
from IPython.display import clear_output

import plotly.offline as py
import plotly.graph_objects as go
from plotly.subplots import make_subplots
py.init_notebook_mode()
    
import re
import nltk
nltk.download('vader_lexicon')
from nltk.sentiment.vader import SentimentIntensityAnalyzer

from nltk.probability import FreqDist
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

# Filter constants for states in US
STATES = ['Alabama', 'AL', 'Alaska', 'AK', 'American Samoa', 'AS', 'Arizona', 'AZ', 'Arkansas', 'AR', 'California', 'CA', 'Colorado', 'CO', 'Connecticut', 'CT', 'Delaware', 'DE', 'District of Columbia', 'DC', 'Federated States of Micronesia', 'FM', 'Florida', 'FL', 'Georgia', 'GA', 'Guam', 'GU', 'Hawaii', 'HI', 'Idaho', 'ID', 'Illinois', 'IL', 'Indiana', 'IN', 'Iowa', 'IA', 'Kansas', 'KS', 'Kentucky', 'KY', 'Louisiana', 'LA', 'Maine', 'ME', 'Marshall Islands', 'MH', 'Maryland', 'MD', 'Massachusetts', 'MA', 'Michigan', 'MI', 'Minnesota', 'MN', 'Mississippi', 'MS', 'Missouri', 'MO', 'Montana', 'MT', 'Nebraska', 'NE', 'Nevada', 'NV', 'New Hampshire', 'NH', 'New Jersey', 'NJ', 'New Mexico', 'NM', 'New York', 'NY', 'North Carolina', 'NC', 'North Dakota', 'ND', 'Northern Mariana Islands', 'MP', 'Ohio', 'OH', 'Oklahoma', 'OK', 'Oregon', 'OR', 'Palau', 'PW', 'Pennsylvania', 'PA', 'Puerto Rico', 'PR', 'Rhode Island', 'RI', 'South Carolina', 'SC', 'South Dakota', 'SD', 'Tennessee', 'TN', 'Texas', 'TX', 'Utah', 'UT', 'Vermont', 'VT', 'Virgin Islands', 'VI', 'Virginia', 'VA', 'Washington', 'WA', 'West Virginia', 'WV', 'Wisconsin', 'WI', 'Wyoming', 'WY']
STATE_DICT = dict(itertools.zip_longest(*[iter(STATES)] * 2, fillvalue=""))
INV_STATE_DICT = dict((v,k) for k,v in STATE_DICT.items())

#connect to DB
def connect_db(): 
    db_connection = mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="11223344",
        database="tweetdb",
        charset = 'utf8'
     )
    return db_connection

def query_db(st_time):
    db_connection = connect_db()
    # query tweet data every 30 mins
    query = "SELECT * FROM {} WHERE created_at >= '{}'".format(settings.TABLE_NAME, st_time)
    df = pd.read_sql(query, con=db_connection)
    df['created_at'] = pd.to_datetime(df['created_at'])
    return df


vader_sid = SentimentIntensityAnalyzer()


while True:

    clear_output()

        # set data collect/display time interval - every 30 mins
    st_time_before_30mins = (datetime.datetime.utcnow() - datetime.timedelta(hours=0, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
    st_time_before_day = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')


    df_30mins = query_db(st_time_before_30mins)
    df_day = query_db(st_time_before_day)

    # run vader sentiment analysis

    df_30mins['vader_compound'] = df_30mins['text'].apply(lambda text: vader_sid.polarity_scores(text)['compound'])
    df_30mins['vader_polarity'] = df_30mins['vader_compound'].apply(lambda score: 'positive' if score >=0.01 else ('negative' if score <= -0.01 else 'neutral'))


    fig = make_subplots(
        rows=2, cols=2,
    #         column_widths=[1, 0.4],
    #         row_heights=[0.6, 0.4],
        specs=[[{"type": "scatter", "rowspan": 2}, {"type": "choropleth"}], [  None  , {"type": "bar"}]]
        )

    result_vader_polarity = df_30mins.groupby( [pd.Grouper(key='created_at', freq='10s'), 'vader_polarity']).count().unstack(fill_value=0).stack().reset_index()
    result_vader_polarity = result_vader_polarity.rename(columns= { "id_str": "Num of Tweets about '{}'".format(settings.TRACK_WORDS), "created_at":"Time in UTC" })

    result_vader_score =  df_30mins.groupby( [pd.Grouper(key='created_at', freq='10s'), 'vader_polarity']).mean().unstack(fill_value=0).stack().reset_index()
    result_vader_score = result_vader_score.rename(columns= { "created_at":"Time in UTC" })

    result_vader = pd.merge(result_vader_polarity, result_vader_score , on=["Time in UTC", "vader_polarity"] )
    columns = ["Time in UTC", "vader_polarity", "vader_compound_y", "Num of Tweets about '{}'".format(settings.TRACK_WORDS)]
    result_vader = result_vader[columns]

    '''
    Plot the Line Chart
    '''
    time_series = result_vader["Time in UTC"].reset_index(drop=True)
    fig.add_trace(go.Scatter(
        x=time_series,
        y=result_vader["Num of Tweets about '{}'".format(settings.TRACK_WORDS)][result_vader['vader_polarity']=='neutral'].reset_index(drop=True),name="neutral"), row=1, col=1)   
    fig.add_trace(go.Scatter(
        x=time_series,
        y=result_vader["Num of Tweets about '{}'".format(settings.TRACK_WORDS)][result_vader['vader_polarity']=='negative'].reset_index(drop=True),name="negative"), row=1, col=1) 

    fig.add_trace(go.Scatter(
        x=time_series,
        y=result_vader["Num of Tweets about '{}'".format(settings.TRACK_WORDS)][result_vader['vader_polarity']=='positive'].reset_index(drop=True),
        name="positive"), row=1, col=1) 


    '''
    Plot the Bar Chart
    '''
    content = ' '.join(df_30mins["text"])
    content = re.sub(r"http\S+", "", content)
    content = content.replace('RT ', ' ').replace('&amp;', 'and')
    content = re.sub('[^A-Za-z0-9]+', ' ', content)
    content = content.lower()

    tokenized_word = word_tokenize(content)
    stop_words=set(stopwords.words("english")).union('today', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'time', 'get')
    filtered_sent=[]
    for w in tokenized_word:
        if w not in stop_words:
            filtered_sent.append(w)
    fdist = FreqDist(filtered_sent)
    fd = pd.DataFrame(fdist.most_common(10), columns = ["Word","Frequency"]).drop([0]).reindex().sort_values(by = ['Frequency'])
    fig.add_trace(go.Bar(x=fd["Frequency"], y=fd["Word"], orientation='h'), row=2, col=2)

    '''
    Plot the Geo-Distribution
    '''

    is_in_US=[]
    geo = df_day[['user_location']]
    df_day = df_day.fillna(" ")
    for x in df_day['user_location']:
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
    #geo_dist["Log Num"] = geo_dist["Number"].apply(lambda x: math.log(x, 2))


    geo_dist['Full State Name'] = geo_dist['State'].apply(lambda x: INV_STATE_DICT[x])
    geo_dist['text'] = geo_dist['Full State Name'] + '<br>' + 'Num: ' + geo_dist['Number'].astype(str)
    fig.add_trace(go.Choropleth(
        locations=geo_dist['State'], # Spatial coordinates
        z = geo_dist['Number'].astype(float), # Data to be color-coded
        locationmode = 'USA-states', # set of locations match entries in `locations`
        colorscale = "Blues",
        text=geo_dist['text'], # hover text
        marker_line_color='white', # line markers between states
        showscale=False,
        geo = 'geo'
        ),
        row=1, col=2)


    fig.update_layout(
        title_text= "Real-time tracking '{}' mentions on Twitter {} UTC".format(settings.TRACK_WORDS[0] ,datetime.datetime.utcnow().strftime('%m-%d %H:%M')),
        geo = dict( scope='usa',),
        margin=dict(r=20, t=50, b=50, l=20),
        annotations=[
            go.layout.Annotation(
                text="Source: Twitter",
                showarrow=True,
                xref="paper",
                yref="paper",
                x=0,
                y=0)
        ],
        showlegend=False,
        xaxis_rangeslider_visible=True
    )

    
    fig.show()

    time.sleep(120)
