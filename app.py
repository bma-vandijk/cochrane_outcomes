import streamlit as st
from supabase import create_client, Client
import random
import pandas as pd
import os
from streamlit import session_state as ss

#-- init db connection
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

#-- fetch db
@st.cache_resource(ttl=600)
def run_query():
    
    #-- split db in easy and hard questions
    easy = supabase.table("rct_df_updated").select("user,question,question_id,label,status,microsoft_Phi-3_5-mini-instruct_probs").gte('microsoft_Phi-3_5-mini-instruct_probs',.7).eq('status','available').execute()
    hard = supabase.table("rct_df_updated").select("user,question,question_id,label,status,microsoft_Phi-3_5-mini-instruct_probs").lt('microsoft_Phi-3_5-mini-instruct_probs',.7).eq('status','available').execute()

    return easy,hard

#-- sample rows
@st.cache_data
def row_sampler(_easy,_hard):

    rint = random.randint(1, 10) #-- easy or hard Q? Sample random number and specify proportion
    
    if rint < 7: #-- 60% easy, 40% hard 
        sampled_row = random.sample(_easy.data, min(1, len(_easy.data)))
    else:
        sampled_row = random.sample(_hard.data, min(1, len(_hard.data)))
                        
    for row in sampled_row: #-- update sampled row: in progress
        response = (supabase.table("rct_df").update({"status": "in_progress"}).eq("question_id", row['question_id']).execute())
        pass

    Qs, Qs_ids = [row['question'] for row in sampled_row], [row['question_id'] for row in sampled_row]

    return Qs, Qs_ids

#-- update db with label
def submit(label,status,user,question_id):
    response = (supabase.table("rct_df").update({"label":label, "status":status, "user":user}).eq("question_id", question_id).execute())
    ss['disable'] = True
    
#-- fetch next item and empty cache + session state
def next():
    for key in ss.keys():
        del ss[key]
    st.cache_data.clear()

def unlock_submit():
    ss['disable_submit'] = True

#-- get first items
easy, hard = run_query()
Q, Q_id = row_sampler(easy,hard)

#-- init session state
if 'Q' not in ss:
    ss['Q'] = Q[0]
if 'Qs_id' not in ss:
    ss['Q_id'] = Q_id[0]
if 'disable' not in ss:
    ss['disable'] = False
if 'user_id_start' not in ss:
    ss['user_id_start'] = False
if 'checkbox_closed' not in ss:
    ss['checkbox_closed'] = False
if 'disable_submit' not in ss:
    ss['disable_submit'] = True

#-- add sidebar element for controlling flow + id
with st.sidebar:
    st.html(""" <style>
            [data-testid="stSidebarContent"] {color: black;background-color: LightSlateGrey;}
            </style>""")
    st.write("**Welcome to this Cochrane labeller app.** \n\n :rocket: To start, please fill out your user initials below. You just need to do this once. Then check the box on the right to display the question.")
 
    # st.markdown("""<style> 
    #             div[data-testid="InputInstructions"] > span:nth-child(1) {visibility: hidden;} 
    #             </style>""",unsafe_allow_html=True)
    user_id = st.text_input("placeholder",value=None,key='user_id',placeholder='User initials here',label_visibility='hidden')
    st.write("")
    st.write(""" :white_check_mark: After reading the question, pick an answer. If you don't know the answer or want to skip the question, just click submit.
             \n\n :arrow_right: After submitting, a 'Next question' button will appear below. Click to load the next question, and check the box on the right again. 
             You can label as many items you want and to stop, simply close this window. To continue later, just navigate to this page again, fill out your initials, and label away!
             \n\n :question: In case of questions or app malfunction send a mail to b.m.a.van_dijk[at]lumc.nl.
             \n\n :handshake: Thank you for your participation!""")
    if ss['disable']:
        st.markdown("""<style> div.stButton > button:first-child {color:white} </style>""", unsafe_allow_html=True)
        st.button(label="Next example", on_click=next)

#-- here the actual labelling happens
if st.checkbox('Display the next question',key="user_id_start",disabled=ss['checkbox_closed']):
    if ss['user_id_start'] and user_id: #-- stop if no user id present
        ss['checkbox_closed'] = True #-- prevent getting disabled answer box
        with st.container(height=None):
            st.subheader(ss['Q'])
            #st.write(ss['Q_id'])
            with st.form('form_k'):
                #st.markdown("""<style> div[class*="stRadio"] > label > div[data-testid="stMarkdownContainer"] > p {font-size: 16px;}</style>""", unsafe_allow_html=True)
                label = st.radio('***Is this considered a Positive, Neutral or Negative health outcome?***', ['Positive', 'Neutral', 'Negative'], horizontal=True,index=None,key='label', disabled=ss['disable'])
                st.form_submit_button('Submit', on_click=submit(label,'done',user_id,ss['Q_id']), disabled= True if label in ['Positive', 'Neutral', 'Negative'] else False)

    else:
        st.write('Uncheck the box above and please enter your user initials first.')