import sqlite3, random
import pandas as pd
import streamlit as st
from streamlit import session_state as ss


#@st.cache_resource 2
def prepare_database(path):
    
    df = pd.read_csv(path, index_col=0)
    df = df[['id','study.name','specialty','outcome_name','comparison_name','microsoft/Phi-3.5-mini-instruct_probs']]

    #-- add label col
    df['label'] = pd.Series(dtype='str')

    #-- add q col
    #question = f"In a medical study on '{df.comparison_name}', the outcome is '{df.outcome_name}'. Is this considered a positive or negative health outcome? Please only respond with 'positive', 'negative' or 'neutral'."
    df['question'] = df.apply(lambda row: f"In a medical study on '{row.comparison_name}', the outcome is '{row.outcome_name}'. Is this considered a positive or negative health outcome?", axis=1)  
    df['question_id'] = ['Q' + str(i) for i in range(len(df))]

    #-- Connect to SQLite database (or create it)
    conn = sqlite3.connect('cochrane_labeling.db')

    #-- define cursor
    cur = conn.cursor()

    # Write the DataFrame to SQL (replace if it already exists)
    df.to_sql('rct_df', conn, if_exists='replace', index=False)

    #-- check if column is created
    cur.execute("ALTER TABLE rct_df ADD COLUMN status TEXT DEFAULT available")
    cur.execute("ALTER TABLE rct_df ADD COLUMN user_id TEXT DEFAULT empty")

    return conn, cur

#@st.cache_data
def sample_questions(user_id,_conn,_cur):

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
        _cur.execute(f"UPDATE rct_df SET status = ?, user_id = ? WHERE question_id = ?", ('in-progress',user_id,question[1],))
        _conn.commit()
    
    # Commit the changes
    
    return [q[0] for q in sampled_questions], [q[1] for q in sampled_questions]


#-- update labels in DB
def update_label(cursor, label, labeling_done, question_id, user, conn):
    
    # Update the label and mark the question as labeled
    cursor.execute("UPDATE rct_df SET label = ?, status = ? WHERE question_id = ? AND user_id = ?", (label, labeling_done, question_id, user))
    
    # Commit the changes
    conn.commit()

    print(label)
    print(question_id)

def update_cb(label,Qs_ids):
    """A callback function to update the answer. Whenever a button is used, try the callback method as much as possible.
    """
    # That ans is the key we assign in radio button.
    if ss.ans:
        ss.labels.append(label)
        ss.q_index.append(Qs_ids)

    ss.a_index += 1  # load next animal

def restart_cb():
    """Enable the answer form button again."""
    ss.done = False



def main():
    
    if 'a_index' not in ss:
        ss.a_index = 0

    if 'labels' not in ss:
        ss.labels = []
    
    if 'q_index' not in ss:
        ss.q_index = []

    # Once labelling is done
    if 'done' not in ss:
        ss.done = False

    
    conn, cur = prepare_database('source/rct_df.csv') #-- set up db hooks
    
    st.title('RCT Outcomes Labelling App') #-- st markup
    
    #-- fetch user id 
    user_id = st.text_input("Please enter user ID:", value="",key='user_id')
    
    st.write(f"You are user: {user_id}")

    if st.checkbox('Check this box to save ID and start labelling!',key=f"user_id_start"):

        Qs, Qs_ids = sample_questions(user_id, conn, cur) #-- sample qs

        if ss.a_index > len(Qs) - 1:
            Qs = 'The round is complete.'  # avoid index overflow
            ss.done = True
        else:
            Qs = Qs[ss.a_index]
            Qs_ids = Qs_ids[ss.a_index]

        with st.form('form_k'):
            st.subheader(f"{Qs}")
            label = st.radio('Select', ['Positive', 'Neutral', 'Negative'], horizontal=True, key='ans')
            st.form_submit_button('Submit', on_click=update_cb(label, Qs_ids), disabled=ss.done)


        print(ss.a_index)
        print(ss.labels[1:]) #-- bug, check this later
        print(ss.q_index[:-1])#-- bug, check this later
        
    
        if ss.a_index > len(Qs_ids):
            #if st.checkbox('Up for another round?',key="go_on"):
            st.button(':+1: I want to do another round', on_click=restart_cb)
            ss.a_index = 0
            ss.labels = []
            ss.q_index = []

    
        #         # Report after exhausting the number of animals
        # if ss.a_index > len(Qs_ids) - 1:
            
        #     # Reset variables values ready for next round.
        #     ss.a_index = 0
        #     ss.labels = []
        #     ss.q_index = []

        #     # Once labelling is done
        #     if 'done' not in ss:
        #         ss.done = False

        #     # Build a button for next round.
        #     st.button(':+1: Next round', on_click=restart_cb)


    # if st.checkbox('Check this box to save ID and continue',key=f"user_id"):
            
    #     sample_qs,question_ids = sample_questions(user_id, conn, cur) #-- sample qs

    #     #-- fetch questions to label
    #     qs_ids = list(zip(sample_qs,question_ids))

    #     for i in range(len(qs_ids)):
    #         q_text, q_id = qs_ids[i][0], qs_ids[i][1] 
    #         st.subheader(f"Question: {q_text}")
            
    #         label = st.text_input("Please enter label:", value="",key=q_id + '_label') #-- fetch user label

    #         if not st.checkbox('Click to save your answer and go to next item',key=f"{'save_answer' + q_id}"):
    #             continue

    #         # # When the user submits a label
    #         # if st.button("Submit Label", key=f'{user_id + q_id}'):
                
    #         #     if label:
    #         #         # Update label in the database
    #         #         update_label(cursor=cur, label=label, labeling_done='done', question_id=q_id, user=user_id, conn=conn)
    #         #         #-- sanity writeout
    #         #         table = pd.read_sql_query("SELECT * from rct_df", conn)
    #         #         table.to_csv('dbtest.csv', index_label='index')
    #         #         st.success(f"Label '{label}' has been submitted for question ID {q_id}")

    #         #         if st.checkbox('Click to save your answer and go to next item',key=f"{'save_answer' + q_id}"):
    #         #             continue
    #         #         else:
    #         #             print('errorrrr')
                    
    #         #     else:
    #         #         st.error("Please enter a label.")
            
            

    #     else:
    #         st.write("No available questions to label at the moment.")



    #     # conn.close()


if __name__ == "__main__":

    main()


    # #-- questions, labels and ids for updating
    # qs_labels_ids = list(zip(sample_qs, test_labels,question_ids))

    # #-- fake an update of returned labels
    # for i in range(len(list(qs_labels_ids))):
    #     update_label(cursor=cur, label=qs_labels_ids[i][1], labeling_done='done', question_id=qs_labels_ids[i][2], user='testuser01')

