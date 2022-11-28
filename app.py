#!/usr/bin/env python
# coding: utf-8

import garminconnect as gc
import datetime
import json
import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import requests
import logging

def init_api(email, password):
    """Initialize Garmin API with your credentials."""

    try:

        api = gc.Garmin(email, password)
        api.login()

        # Save session dictionary to json file for future use
        with open("session.json", "w", encoding="utf-8") as f:
            json.dump(api.session_data, f, ensure_ascii=False, indent=4)
    except (
        gc.GarminConnectConnectionError,
        gc.GarminConnectAuthenticationError,
        gc.GarminConnectTooManyRequestsError,
        requests.exceptions.HTTPError,
    ) as err:
        logger.error("Error occurred during Garmin Connect communication: %s", err)
        st.error(err)
        return None

    return api


logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

st.set_page_config(layout="wide")

state=st.session_state

if 'api' not in state:
    state['api']=None
    
st.title("A simple running form webapp")
st.header("Analyze your stride length and cadence versus pace :runner:")

st.write("First, login to Garmin Connect")

# if 'submit' not in st.session_state:
#     st.session_state['submit']=False

with st.sidebar:
    with st.form(key='login'):
        st.markdown("**Garmin Connect**")
        user=st.text_input("Username",key='user')
        pwd=st.text_input("Password",type="password", key='pwd')
        log_butt=st.form_submit_button(label="Login")
        if log_butt and user and pwd:
            # state.user=user
            # state.pwd=pwd
            with st.spinner("Accessing..."):
                state.api=init_api(user,pwd)

#st.text(st.session_state)

if state.api is not None:
    # if "api" not in st.session_state:
    #     st.session_state['api'] = init_api(st.session_state.user,st.session_state.pwd)
    # st.session_state['api'] = init_api(st.session_state.user,st.session_state.pwd)
    # if st.session_state.api is not None:
    #     #api = st.session_state.api
        st.markdown("Logged in! :key:")

        with st.form(key='dates'):
            start_date, end_date=st.date_input('Time interval to consider',
                [datetime.date(2022,9,1),datetime.date.today()],
                max_value=datetime.date.today(),
                #disabled=(not st.session_state['FormSubmitter:login-Login']) and (st.session_state.api is not None)
                )
            dates_butt=st.form_submit_button(label='Search activities')
        #st.text(st.session_state)

        if dates_butt:
            with st.spinner("Getting activities"):
                activities = state.api.get_activities_by_date(
                        start_date, end_date, "running"
                        )
            st.markdown("Found **{}** running activities.".format(len(activities)))
            
            data=[]
            if len(activities) > 1:
                with st.spinner("Checking laps and processing data..."):
                    for activity in activities:
                        activity_id = activity["activityId"]
                        # display_text(activity)
                        # print("\n")
                        laps=state.api.get_activity_splits(activity_id)['lapDTOs']
                        data.extend([
                            {"activity_type" : activity['activityType']['typeKey'],
                            "activity_start": activity['startTimeGMT'],
                            "activity_distance": activity['distance'],
                            "lap_start": l['startTimeGMT'], 
                            "lap_distance": l['distance'],
                            "lap_duration": l['duration'],
                            "elev_gain": l['elevationGain'],
                            "elev_loss": l['elevationLoss'],
                            "speed": l['averageSpeed'],
                            "stride_length": l['strideLength']/100,
                            "cadence": l['averageRunCadence']} for l in laps])

                    lap_df=pd.DataFrame(data)

                    lap_df=lap_df.astype({'activity_start':'datetime64[ns]','lap_start':'datetime64[ns]'})
                    #lap_df.dtypes
                    lap_df['activity_start']=lap_df.activity_start.dt.tz_localize('GMT')
                    lap_df['lap_start']=lap_df.lap_start.dt.tz_localize('GMT')


                    lap_df['pace']=lap_df.apply(lambda x: '{}\'{:.0f}"'.format(math.floor((x.lap_duration/x.lap_distance*1000)//60),(x.lap_duration/x.lap_distance*1000)%60), axis=1)


                    clean_df=(lap_df.query('(activity_type == "track_running" and lap_distance >= 400) or (activity_type == "running" and lap_distance >= 1000)')
                        .query('(elev_gain/lap_distance < 0.06) and (elev_loss/lap_distance < 0.06)'))


                    c1, c0 = np.polyfit(clean_df.speed,clean_df.stride_length,1)
                    a1, a0 = np.polyfit(clean_df.speed,clean_df.cadence,1)

                    width=700


                    fig1 = px.scatter(clean_df,
                        x="speed", 
                        y="stride_length", 
                        title="Stride length vs speed",
                        width=width,
                        #height=400,
                        labels={'speed':'speed (m/s)','stride_length':'stride length (m)'},
                        hover_data=['activity_start','pace','lap_distance'],
                        size=clean_df['lap_distance'].clip(0,10**3.5),
                        size_max=10,
                        color='activity_type',
                        template='plotly_dark'
                    )
                    fig1.update_layout(title_x=0.5, title_font_size=20, legend={'yanchor':'bottom','y':0, 'xanchor':'right','x':1})
                    fig1.update_xaxes(showgrid=True,gridwidth=1,gridcolor='lavender')
                    fig1.update_yaxes(showgrid=True,gridwidth=1,gridcolor='lavender')
                    #fig.layout.update(xaxis2 = go.layout.XAxis(overlaying='x',side='top'))
                    fig1.add_shape(
                            type='line',
                            x0=clean_df.speed.min()*0.98,
                            y0=c0+c1*clean_df.speed.min()*0.98,
                            x1=clean_df.speed.max()*1.02,
                            y1=c0+c1*clean_df.speed.max()*1.02,
                            line=dict(
                                dash='dot', color='gray'
                            )
                    )

                    fig2 = px.scatter(clean_df,
                        x="speed", 
                        y="cadence", 
                        title="Cadence vs speed",
                        width=width,
                        #height=400,
                        labels={'speed':'speed (m/s)','cadence':'steps per minute'},
                        hover_data=['activity_start','pace','lap_distance'],
                        size=clean_df['lap_distance'].clip(0,10**3.5),
                        size_max=10,
                        color='activity_type',
                        template='plotly_dark'
                    )
                    fig2.update_layout(title_x=0.5, title_font_size=20, legend={'yanchor':'bottom','y':0, 'xanchor':'right','x':1})
                    fig2.update_xaxes(showgrid=True,gridwidth=1,gridcolor='lavender')
                    fig2.update_yaxes(showgrid=True,gridwidth=1,gridcolor='lavender')
                    #fig.layout.update(xaxis2 = go.layout.XAxis(overlaying='x',side='top'))
                    fig2.add_shape(
                            type='line',
                            x0=clean_df.speed.min()*0.98,
                            y0=a0+a1*clean_df.speed.min()*0.98,
                            x1=clean_df.speed.max()*1.02,
                            y1=a0+a1*clean_df.speed.max()*1.02,
                            line=dict(
                                dash='dot', color='gray'
                            )
                    )

                    col1, col2=st.columns(2)

                    with col1:
                        st.plotly_chart(fig1, theme=None)
                        st.caption("The linear regression coefficient for your stride vs speed plot is **{:.2f}** (measured in units of seconds)".format(c1))

                    with col2:
                        st.plotly_chart(fig2, theme=None)
                        st.caption("The linear regression coefficient for your cadence vs speed plot is **{:.2f}** (measured in units of steps/m)".format(a1/60))
                
                avg_str_c=0.27
                avg_cad_c=0.16

                url = 'https://journals.physiology.org/doi/full/10.1152/jappl.2000.89.5.1991'
                url1= 'https://runblogger.com/2011/09/running-speed-human-variability-and.html'
                url2= 'https://runblogger.com/2011/09/running-speed-human-variability-and.html'

                st.markdown("#")
                st.write(f"The values for average runners appear to be around **{avg_str_c}** for the stride coefficient and **{avg_cad_c}** for the cadence one (see e.g. *[Weyand et al., 2000]({url})*), particularly Figure 2 therein. See also the blog posts by [Hutchinson]({url1}) and [Larson]({url2}).")
                st.write("Comparing your values to typical ones may give you hints on your running style, assessing the role played by stride widening and cadence increase when you run faster.")
                st.write("Usually, the higher than average is the stride coefficient (and the lower the cadence one), the more you tend to be *stride runner*. Instead, the lower than average is the former coefficient and the higher the latter, the more you should be classified as a *cadence runner*.")


            else:
                "Please load at least two activities!"







