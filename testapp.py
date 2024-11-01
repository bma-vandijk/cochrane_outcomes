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
    easy = supabase.table("rct_df").select("user,question,question_id,label,status,microsoft_Phi-3_5-mini-instruct_probs").gte('microsoft_Phi-3_5-mini-instruct_probs',.7).eq('status','available').execute()
    hard = supabase.table("rct_df").select("user,question,question_id,label,status,microsoft_Phi-3_5-mini-instruct_probs").lt('microsoft_Phi-3_5-mini-instruct_probs',.7).eq('status','available').execute()

    return easy,hard

@st.cache_data
def row_sampler(_easy,_hard):

    rint = random.randint(1, 10) #-- easy or hard Q? Sample random number and specify proportion
    
    if rint < 7: #-- 60% easy, 40% hard 
        sampled_row = random.sample(_easy.data, min(1, len(_easy.data)))
    else:
        sampled_row = random.sample(_hard.data, min(1, len(_hard.data)))
                        
    for row in sampled_row: #-- update sampled row: in progress
        #response = (supabase.table("rct_df").update({"status": "in_progress_3"}).eq("question_id", row['question_id']).execute())
        pass

    Qs, Qs_ids = [row['question'] for row in sampled_row], [row['question_id'] for row in sampled_row]

    return Qs, Qs_ids

#-- update db with label
def submit(label,status,user,question_id):
    #response = (supabase.table("rct_df").update({"label":label, "status":status, "user":user}).eq("question_id", question_id).execute())
    ss['disable'] = True
    
#-- fetch next item and empty cache + session state
def next():
    for key in ss.keys():
        del ss[key]
    st.cache_data.clear()

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

#-- add sidebar element for controlling flow + id
with st.sidebar:
    user_id = st.text_input("Enter username and press enter:",value=None,key='user_id',disabled=ss['user_id_start'])
    if ss['disable']:
        st.button(label="Next example", on_click=next)

#-- here the actual labelling happens
if st.checkbox('Check this box to save ID and start labelling!',key=f"user_id_start",disabled=ss['checkbox_closed']):
    if ss['user_id_start'] and user_id: #-- stop if no user id present
        ss['checkbox_closed'] = True #-- prevent getting disabled answer box
        st.subheader(ss['Q'])
        #st.write(ss['Q_id'])
        with st.form('form_k'):
            label = st.radio('Select', ['Positive', 'Neutral', 'Negative'], horizontal=True,index=None,key='label', disabled=ss['disable']) #--disabled=st.session_state['disable']
            #st.write(ss.label)
            st.form_submit_button('Submit', on_click=submit(label,'done',user_id,ss['Q_id']))
    else:
        st.write('You did not submit a user ID.')

