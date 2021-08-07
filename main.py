from googleapiclient.discovery import build
import pandas as pd
import streamlit as st
import plotly.express as px
from plotly.subplots import make_subplots
import base64

## streamlit sidebar
st.set_page_config(layout='wide')
st.sidebar.title('Channel r-index')

channel_id = st.sidebar.text_input("Enter any youtube channel id: ", 'UCwIzJ_UWnn1Uc8d1H8nCuUA')

st.sidebar.markdown(""" <style> .big-font { 
    font-size:11px !important;} </style>
    """, unsafe_allow_html=True)

st.sidebar.markdown('<p class="big-font">* r-index = total views in last 10 uploaded videos / total subscribers</p>', unsafe_allow_html=True)


api_key = 'AIzaSyDeeQd-yrWvVB2pplFO1XjkDTGyqftydFU'

youtube = build('youtube', 'v3', developerKey = api_key)


def get_channel_stats(youtube, channel_id):
    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        id=channel_id
    )
    response = request.execute()
    
    return response['items']


def get_video_list(youtube, upload_id):
    video_list = []
    request = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=upload_id,
        maxResults=50
    )
    next_page = True
    while next_page:
        response = request.execute()
        data = response['items']

        for video in data:
            video_id = video['contentDetails']['videoId']
            if video_id not in video_list:
                video_list.append(video_id)

        # Do we have more pages?
        if 'nextPageToken' in response.keys():
            next_page = True
            request = youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=upload_id,
                pageToken=response['nextPageToken'],
                maxResults=50
            )
        else:
            next_page = False

    return video_list


def get_video_details(youtube, video_list):
    stats_list=[]

    # Can only get 50 videos at a time.
    for i in range(0, len(video_list), 50):
        request= youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_list[i:i+50]
        )

        data = request.execute()
        for video in data['items']:
            title=video['snippet']['title']
            published=video['snippet']['publishedAt']
            description=video['snippet']['description']
            tag_count= len(video['snippet'].get('tags', '0'))
            view_count=video['statistics'].get('viewCount',0)
            like_count=video['statistics'].get('likeCount',0)
            dislike_count=video['statistics'].get('dislikeCount',0)
            comment_count=video['statistics'].get('commentCount',0)
            stats_dict=dict(title=title, description=description, published=published, tag_count=tag_count, view_count=view_count, like_count=like_count, dislike_count=dislike_count, comment_count=comment_count)
            stats_list.append(stats_dict)

    return stats_list


## calling all functions
channel_stats = get_channel_stats(youtube, channel_id)
upload_id = channel_stats[0]['contentDetails']['relatedPlaylists']['uploads']

subscriber_count = channel_stats[0]['statistics']['subscriberCount']
channel_title = channel_stats[0]['snippet']['title']
st.title(channel_title)

## video info from youtube
video_list = get_video_list(youtube, upload_id)
video_data = get_video_details(youtube, video_list)

## dataframe
df = pd.DataFrame(video_data)

df.published = pd.to_datetime(df.published)
df.published = df.published.dt.date
df.tag_count = pd.to_numeric(df.tag_count)
df.view_count = pd.to_numeric(df.view_count)
df.like_count = pd.to_numeric(df.like_count)
df.dislike_count = pd.to_numeric(df.dislike_count)
df.comment_count = pd.to_numeric(df.comment_count)
df.drop('description', axis=1, inplace=True)

## r-index calculation
r_index = format((df.view_count[:10].sum()/10)/int(subscriber_count), '.2f')

col1, col2, col3, col4 = st.beta_columns([1,2.5, 2, 3.5])
with col1:
    if (r_index < str(0.5)):
        st.error(r_index)
    else:
        st.success(r_index)
with col2:
    st.info('Subscribers: ' + subscriber_count)
with col3:
    st.info('Videos: '+ str(len(df)))
with col4:
    st.info('Views: '+ str(df.view_count.sum()))

st.subheader('Views & Comments over time')
st.text('(zoom in & pan for better view)')

subfig = make_subplots(specs=[[{"secondary_y": True}]])

fig = px.bar(df, x="published", y="view_count", hover_name="title")
fig = fig.update_traces(marker={'color': '#345995'})

fig2 = px.line(df, x="published", y="comment_count")
fig2 = fig2.update_traces(yaxis="y2",  line_color='#D4AE96', line_width=.7)

subfig = subfig.add_traces(fig.data + fig2.data)
subfig = subfig.update_layout(yaxis_title=None, xaxis_title=None, showlegend=True, autosize = True, height = 280, margin=dict(l=0,r=0,b=0,t=0))

st.plotly_chart(subfig, use_container_width=True)

st.subheader('Channel data')
st.dataframe(df)

def filedownload(df):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="youtube data.csv">Download these data (csv)</a>'
    return href

st.markdown(filedownload(df), unsafe_allow_html=True)

