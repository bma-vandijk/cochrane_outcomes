# streamlit_app.py

import streamlit as st
from supabase import create_client, Client
import random
import pandas as pd
import os
from streamlit import session_state as ss

# Initialize connection.
# Uses st.cache_resource to only run once.
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()


#-- Uses st.cache_data to only rerun when the query changes or after 10 min.
@st.cache_resource(ttl=600)
def run_query():

    easy = supabase.table("rct_df").select("user,question,question_id,label,status,microsoft_Phi-3_5-mini-instruct_probs").gte('microsoft_Phi-3_5-mini-instruct_probs',.7).eq('status','available').execute()
    hard = supabase.table("rct_df").select("user,question,question_id,label,status,microsoft_Phi-3_5-mini-instruct_probs").lt('microsoft_Phi-3_5-mini-instruct_probs',.7).eq('status','available').execute()

    return easy,hard

@st.cache_data
def row_sampler(_easy,_hard):

    # easy or hard Q
    rint = random.randint(1, 10)
    
    if rint < 7:
        sampled_row = random.sample(_easy.data, min(1, len(_easy.data)))
    else:
        sampled_row = random.sample(_hard.data, min(1, len(_hard.data)))
                        
    for row in sampled_row:
        pass
        #st.write(row['question_id'])
        #response = (supabase.table("rct_df").update({"status": "in_progress"}).eq("question_id", row['question_id']).execute())

    Qs, Qs_ids = [row['question'] for row in sampled_row], [row['question_id'] for row in sampled_row]

    return Qs, Qs_ids

def submit(user,label):
    #response = (supabase.table("rct_df").update({"status": "in_progress"}).eq("question_id", row['question_id']).execute())
    ss['disable'] = True
    

def next():
    #st.write(ss)
    for key in ss.keys():
        del ss[key]
    st.cache_data.clear()

easy, hard = run_query()
Q, Q_id = row_sampler(easy,hard)

if 'Q' not in ss:
    ss['Q'] = Q[0]
if 'Qs_id' not in ss:
    ss['Q_id'] = Q_id[0]
if 'disable' not in ss:
    ss['disable'] = False
# if 'user_id' not in ss:
#     ss['user_id'] = None 
if 'user_id_start' not in ss:
    ss['user_id_start'] = False

col1, col2 = st.sidebar.columns(2)
with col1:
    st.button(label="Next example", on_click=next)
with col2:
    user_id = st.text_input("Please enter user ID:",value=None,key='user_id')

#user_id = st.text_input("Please enter user ID:",value=None,key='user_id',disabled=ss['disable'])
if st.checkbox('Check this box to save ID and start labelling!',key=f"user_id_start"):
    st.subheader(ss['Q'])
    st.write(ss['Q_id'])
    with st.form('form_k'):
        label = st.radio('Select', ['Positive', 'Neutral', 'Negative'], horizontal=True,index=None,key='label', disabled=ss['disable']) #--disabled=st.session_state['disable']
        st.write(ss.label)
        st.form_submit_button('Submit', on_click=submit('testuser',label))

# #-- standard stuff
# st.title('RCT Outcomes Labelling App') #-- st markup
# user_id = st.text_input("Please enter user ID:",key='user_id')
# st.write(f"You are user: {user_id}")
#     #-- actual labelling
# if st.checkbox('Check this box to save ID and start labelling!',key=f"user_id_start"):

#     with st.form('form_k'):
#         st.subheader(ss['Q'])
#         st.write(ss['Q_id'])
#         label = st.radio('Select', ['Positive', 'Neutral', 'Negative'], horizontal=True,index=None,disabled=ss['disable']) #--disabled=st.session_state['disable']
#         st.write(label)
#         st.form_submit_button('Submit', on_click=submit('testuser',label))
#         st.write(label)


# st.write(Qs)
# st.write(Qs_ids)

#-- update labels in DB
# def update_label(label, status, question_id, user):    
#     #-- update database
#     #response = (supabase.table("rct_df").update({"label": label,"status":status,"user":user}).eq("question_id", question_id).execute())


# #---- sandbox
# def run ():
    
#     if "Qs" and 'QS_ids' and 'Q_index' and 'Q_labels' not in st.session_state:
#         easy, hard = run_query()
#         st.session_state["Qs"], st.session_state["Qs_ids"] = row_sampler(easy,hard)
#         st.session_state["Q_index"] = 0
#         st.session_state["Q_labels"] = []
#         st.session_state["disable"] = False

#     else:
#         pass
    
#     def submit(label,user):
#         #response = (supabase.table("rct_df").update({"label": label,"status":status,"user":user}).eq("question_id", question_id).execute())
#         st.session_state['disable']=True
#         st.session_state["Q_labels"].append(label)
        

#     def refresh():

#         st.cache_data.clear()
        
#         easy,hard = run_query()
#         st.session_state["Qs"], st.session_state["Qs_ids"] = row_sampler(easy,hard)
#         st.session_state["Q_index"] = 0
#         st.session_state["Q_labels"] = []
#         st.session_state["disable"] = False
#         st.session_state['ans'] = st.empty() 

#     def next():
#         Q_index = st.session_state["Q_index"]
#         if Q_index < len(st.session_state["Qs"]) - 1:
#             st.session_state["Q_index"] += 1
#             #st.session_state['disable']=True
#         else:
#             st.warning('This is the last Q of this round.')
#             #st.session_state['disable']=True
        
#         #del st.session_state['ans']

#     def previous():
#         Q_index = st.session_state["Q_index"]
#         if Q_index > 0:
#             st.session_state["Q_index"] -= 1
#         else:
#             st.warning('This is the first Q of this round.')
#         #st.session_state['disable']=True
#         #del st.session_state['ans']


#     col1, col2 = st.sidebar.columns(2)
#     with col1:
#         st.button(label="Previous", on_click=previous)
#     with col2:
#         st.button(label="Next", on_click=next)
#     st.sidebar.button(label="Load new round!", on_click=refresh)

#     st.write(st.session_state)

#     #-- standard stuff
#     st.title('RCT Outcomes Labelling App') #-- st markup
#     user_id = st.text_input("Please enter user ID:",key='user_id')
#     st.write(f"You are user: {user_id}")
#     #-- actual labelling
#     if st.checkbox('Check this box to save ID and start labelling!',key=f"user_id_start"):

#         #st.subheader(st.session_state['Qs'][st.session_state['Q_index']])
#         #st.write(st.session_state['Qs_ids'][st.session_state['Q_index']])
        

#         with st.form('form_k'):
#             st.markdown(
#         """ <style>
#                 div[role="radiogroup"] >  :first-child{
#                     display: none !important;
#                 }
#             </style>
#             """,
#         unsafe_allow_html=True
#     )
#             st.subheader(st.session_state['Qs'][st.session_state['Q_index']])
#             st.write(st.session_state['Qs_ids'][st.session_state['Q_index']])
#             label = st.radio('Select', ['','Positive', 'Neutral', 'Negative'], key='ans', horizontal=True,index=0,disabled=True) #--disabled=st.session_state['disable']
#             st.write(label)
#             st.form_submit_button('Submit', on_click=submit(label,'testuser'))


# if __name__ == "__main__":
#     #custom_labels = ["", "dog", "cat"]
#     #run("img_dir", custom_labels)
#     run()

# #easy,hard = run_query()

# #Qs, Qs_ids = row_sampler(easy,hard)


# # if 'index' not in ss:
# #     ss.index = 0

# # if 'disable' not in ss:
# #     ss.disable = False

# # # if 'ans' not in ss:
# # #     ss.ans = None

# # # if 'prev_label' not in ss:
# # #     ss.prev_label = None

# # if 'label' not in ss:
# #     ss.label=None

# # if 'Qs' or 'QS_ids' not in ss:
# #     ss.Qs, ss.Qs_ids = Qs, Qs_ids

# # #-- standard stuff
# # st.title('RCT Outcomes Labelling App') #-- st markup
# # user_id = st.text_input("Please enter user ID:", value="",key='user_id')
# # st.write(f"You are user: {user_id}")

# # st.write(ss.Qs)
# # st.write(ss.Qs_ids)

# # # #-- actual labelling
# # # if st.checkbox('Check this box to save ID and start labelling!',key=f"user_id_start"):

# # #     with st.form('form_k'):
# # #         st.subheader(f"{ss.Qs[ss.index]}")
# # #         label = st.radio('Select', ['Positive', 'Neutral', 'Negative'],key='ans', horizontal=True,index=0,disabled=ss.disable)
# # #         #st.write(label)
# # #         st.form_submit_button('Submit', on_click=update_label(label,'Done',ss.Qs_ids[ss.index],user_id))
        
        
        


    


# # # pos = st.checkbox(
# # # "Positive",
# # # key="op1",
# # # on_change=disable_other_checkboxes,
# # # args=("op2", "op3", "op4"),)
# # # neu = st.checkbox(
# # # "Neutral",
# # # key="op2",
# # # on_change=disable_other_checkboxes,
# # # args=("op1", "op3", "op4"),)
# # # neg = st.checkbox(
# # # "Negative",
# # # key="op3",
# # # on_change=disable_other_checkboxes,
# # # args=("op2", "op1", "op4"),)

# # # st.write(pos, neu, neg)

# # #label = next((name for name, value in zip(['pos', 'neg', 'neu'], [pos, neg, neu]) if value), None)
# # #st.write(label)
# # #update_label(label,'Done',ss.Qs_ids[ss.index],user_id)


