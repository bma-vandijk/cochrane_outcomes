import streamlit as st
from streamlit import session_state as ss


animals = ['cat', 'dog', 'fish', 'turtle', 'hare', 'hamster']


# Declare some session variables. It is like a global variable
# in python script. It is called session variables because once
# the browser is reset, their values will go back to its initial
# values. We also do this because streamlit reruns the
# code from top to bottom if there are changes to the states
# or an explicit "st.rerun()" command is called.
# By doing this, their values will not be overwritten as you update
# while streamlit reruns the code from top to bottom on your code.
if 'a_index' not in ss:
    ss.a_index = 0

if 'liked_animals' not in ss:
    ss.liked_animals = []

if 'disliked_animals' not in ss:
    ss.disliked_animals = []

# Once all the amimals are shown.
if 'done' not in ss:
    ss.done = False


def update_cb(animal):
    """A callback function to update the answer.
    
    Whenever a button is used, try the callback method as much as possible.
    """

    # That ans is the key we assign in radio button.
    if ss.ans == 'YES':
        ss.liked_animals.append(animal)
    else:
        ss.disliked_animals.append(animal)

    ss.a_index += 1  # load next animal


def restart_cb():
    """Enable the answer form button again."""
    ss.done = False


if ss.a_index > len(animals) - 1:
    animal = animals[0]  # avoid index overflow
    ss.done = True
else:
    animal = animals[ss.a_index]

# The best widget to use when dealing with user input is the form.
with st.form('form_k'):
    st.subheader(f"Do you like {animal}?")
    st.radio('Select', ['YES', 'NO'], horizontal=True, key='ans')
    st.form_submit_button('Submit', on_click=update_cb, disabled=ss.done, args=(animal,))

# Report after exhausting the number of animals
if ss.a_index > len(animals) - 1:
    st.write('### Report')

    with st.container(border=True):
        st.markdown(f'''number of **YES**: {len(ss.liked_animals)}  
            animals: {ss.liked_animals}
        ''')
        st.markdown(f'''number of **NO**: {len(ss.disliked_animals)}  
            animals: {ss.disliked_animals}
        ''')

    # Reset variables values ready for next round.
    ss.a_index = 0
    ss.liked_animals = []
    ss.disliked_animals = []

    # Build a button for next round.
    st.button(':+1: Next round', on_click=restart_cb)