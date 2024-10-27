import sqlite3, random
import pandas as pd
import streamlit as st
import os
from streamlit import session_state as ss

# Tom > source > human game > server.py > r 258

#-- dir
main_dir = os.getcwd()
print(main_dir)
data_dir = os.path.join(main_dir, 'source','rct_df.csv')

print('update')
@st.cache_resource
def prepare_database(path):
    
    df = pd.read_csv(path, index_col=0)
    df = df[['id','study.name','specialty','outcome_name','comparison_name','microsoft/Phi-3.5-mini-instruct_probs']]

    #-- add label col
    df['label'] = pd.Series(dtype='str')

    #-- add q col
    df['question'] = df.apply(lambda row: f"In a medical study on '{row.comparison_name}', the outcome is '{row.outcome_name}'. Is this considered a positive or negative health outcome?", axis=1)  
    df['question_id'] = ['Q' + str(i) for i in range(len(df))]

    #-- Connect to SQLite database (or create it)
    conn = sqlite3.connect(os.path.join(main_dir,'cochrane_labeling.db'), check_same_thread=False)

    #-- define cursor
    cur = conn.cursor()

    # Write the DataFrame to SQL (replace if it already exists)
    df.to_sql('rct_df', conn, if_exists='replace', index=False)

    #-- check if column is created
    cur.execute("ALTER TABLE rct_df ADD COLUMN status TEXT DEFAULT available")
    cur.execute("ALTER TABLE rct_df ADD COLUMN user_id TEXT DEFAULT empty")

    return conn, cur

#@st.cache_data
@st.cache_data 
def sample_questions(_conn,_cur):

    #-- Select easy rows
    _cur.execute("""SELECT question, question_id FROM rct_df WHERE "microsoft/Phi-3.5-mini-instruct_probs" < 0.7 AND status = 'available'""")
    hard_questions = _cur.fetchall()

    #-- Select select hard rows
    _cur.execute("""SELECT question, question_id FROM rct_df WHERE "microsoft/Phi-3.5-mini-instruct_probs" >= 0.7 AND status = 'available'""")
    easy_questions = _cur.fetchall()

    # Randomly sample 3 easy and 1 hard question
    sampled_questions = random.sample(easy_questions, min(3, len(easy_questions))) + \
                        random.sample(hard_questions, min(1, len(hard_questions)))

    # Mark them as 'in-progress' for the user
    for question in sampled_questions:
        #print(question)
        _cur.execute(f"UPDATE rct_df SET status = ? WHERE question_id = ?", ('in-progress',question[1],))
        _conn.commit()
    
    # Commit the changes
    print('sample_questions: executed')
    return [q[0] for q in sampled_questions], [q[1] for q in sampled_questions]


#-- update labels in DB
def update_label(cur, label, labeling_done, question_id, user, conn):
    print('update_label')
    # Update the label and mark the question as labeled
    #cur.execute("UPDATE rct_df SET label = ?, status = ? WHERE question_id = ? AND user_id = ?", (label, labeling_done, question_id, user))
    
    # Commit the changes
    #conn.commit()
        
    if ss.index == len(ss.Qs) - 1:
        del ss['Qs']
        del ss['index']
        del ss['Qs_ids']
        st.cache_data.clear()

    else:
        ss.index += 1

def main():
    
    conn, cur = prepare_database(data_dir) #-- set up db hooks

    if 'index' not in ss:
        ss.index = 0

    if 'Qs' or 'QS_ids' not in ss:
        ss.Qs, ss.Qs_ids = sample_questions(conn, cur) #-- sample qs

    #st.write(st.session_state)

    #-- standard stuff
    st.title('RCT Outcomes Labelling App') #-- st markup
    user_id = st.text_input("Please enter user ID:", value="",key='user_id')
    st.write(f"You are user: {user_id}")
    
    #-- actual labelling
    if st.checkbox('Check this box to save ID and start labelling!',key=f"user_id_start"):

        #-- mock Q and index    
        # st.write(ss.Qs[ss.index], ss.Qs_ids[ss.index])
        
        with st.form('form_k'):

            st.markdown("""<style>
            div[role=radiogroup] label:first-of-type {
            visibility: hidden;
            height: 0px;
            }</style>""",
        unsafe_allow_html=True,)
            
            st.subheader(f"{ss.Qs[ss.index]}")
            label = st.radio('Select', ['Positive', 'Neutral', 'Negative'], horizontal=True, key='ans',index=None)            
            st.form_submit_button('Submit', on_click=update_label(cur,label,'done',ss.Qs_ids[ss.index],user_id,conn))

    # #-- clunky writeout
    # table = pd.read_sql_query("SELECT * from rct_df", conn)
    # table.to_csv('rct_df_dbtest.csv', index_label='index')

            
if __name__ == "__main__":

    main()