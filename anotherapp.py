import streamlit as st
import os, random
#from streamlit_img_label import st_img_label
#from streamlit_img_label.manage import ImageManager, ImageDirManager
from supabase import create_client, Client

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

    #-- Randomly sample 3 easy and 1 hard question
    sampled_rows = random.sample(_easy.data, min(3, len(_easy.data))) + \
                        random.sample(_hard.data, min(1, len(_hard.data)))

    for row in sampled_rows:
        pass
        #st.write(row['question_id'])
        #response = (supabase.table("rct_df").update({"status": "in_progress"}).eq("question_id", row['question_id']).execute())

    Qs, Qs_ids = [row['question'] for row in sampled_rows], [row['question_id'] for row in sampled_rows]

    return Qs, Qs_ids


easy, hard = run_query()


def run(img_dir, labels):

    if "Qs" and 'QS_ids' and 'Q_index' and 'Q_labels' not in st.session_state:
        easy, hard = run_query()
        st.session_state["Qs"], st.session_state["Qs_ids"] = row_sampler(easy,hard)
        st.session_state["Q_index"] = 0
        st.session_state["Q_labels"] = []
    else:
        pass
        #idm.set_all_files(st.session_state["files"])
        #idm.set_annotation_files(st.session_state["annotation_files"])
     
    def refresh():
        
        st.cache_data.clear()
        st.session_state["Qs"], st.session_state["Qs_ids"] = row_sampler(easy,hard)
        st.session_state["Q_index"] = 0
        st.session_state["Q_labels"] = []

    def next_image():
        Q_index = st.session_state["Q_index"]
        if Q_index < len(st.session_state["Qs"]) - 1:
            st.session_state["Q_index"] += 1
        else:
            st.warning('This is the last Q of this round.')

    def previous_image():
        Q_index = st.session_state["Q_index"]
        if Q_index > 0:
            st.session_state["Q_index"] -= 1
        else:
            st.warning('This is the first Q of this round.')


    # def next_annotate_file():
    #     image_index = st.session_state["image_index"]
    #     next_image_index = idm.get_next_annotation_image(image_index)
    #     if next_image_index:
    #         st.session_state["image_index"] = idm.get_next_annotation_image(image_index)
    #     else:
    #         st.warning("All images are annotated.")
    #         next_image()

    # def go_to_image():
    #     file_index = st.session_state["files"].index(st.session_state["file"])
    #     st.session_state["image_index"] = file_index

    # Sidebar: show status
    # n_files = len(st.session_state["Qs"])
    # n_annotate_files = len(st.session_state["Q_labels"])
    # st.sidebar.write("Total files:", n_files)
    # st.sidebar.write("Total annotate files:", n_annotate_files)
    # st.sidebar.write("Remaining files:", n_files - n_annotate_files)

    # st.sidebar.selectbox(
    #     "Files",
    #     st.session_state["files"],
    #     index=st.session_state["image_index"],
    #     on_change=go_to_image,
    #     key="file",
    # )
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.button(label="Previous image", on_click=previous_image)
    with col2:
        st.button(label="Next image", on_click=next_image)
    st.sidebar.button(label="Next need annotate", on_click=next_annotate_file)
    st.sidebar.button(label="Refresh", on_click=refresh)

    st.write(session_state['Qs'][session_state['Q_index']])
    
    # # Main content: annotate images
    # img_file_name = idm.get_image(st.session_state["image_index"])
    # img_path = os.path.join(img_dir, img_file_name)
    # im = ImageManager(img_path)
    # img = im.get_img()
    # resized_img = im.resizing_img()
    # resized_rects = im.get_resized_rects()
    # rects = st_img_label(resized_img, box_color="red", rects=resized_rects)

    # def annotate():
    #     im.save_annotation()
    #     image_annotate_file_name = img_file_name.split(".")[0] + ".xml"
    #     if image_annotate_file_name not in st.session_state["annotation_files"]:
    #         st.session_state["annotation_files"].append(image_annotate_file_name)
    #     next_annotate_file()

    # if rects:
    #     st.button(label="Save", on_click=annotate)
    #     preview_imgs = im.init_annotation(rects)

    #     for i, prev_img in enumerate(preview_imgs):
    #         prev_img[0].thumbnail((200, 200))
    #         col1, col2 = st.columns(2)
    #         with col1:
    #             col1.image(prev_img[0])
    #         with col2:
    #             default_index = 0
    #             if prev_img[1]:
    #                 default_index = labels.index(prev_img[1])

    #             select_label = col2.selectbox(
    #                 "Label", labels, key=f"label_{i}", index=default_index
    #             )
    #             im.set_annotation(i, select_label)

if __name__ == "__main__":
    custom_labels = ["", "dog", "cat"]
    run("img_dir", custom_labels)