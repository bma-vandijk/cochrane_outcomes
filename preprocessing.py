#-- Setup 
import os, torch, gc

import pandas as pd
pd.options.mode.chained_assignment = None
import google.generativeai as genai
import numpy as np


from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from groq import Groq
from transformers import AutoTokenizer, pipeline, AutoModelForSequenceClassification, TrainingArguments, Trainer
from datasets import Dataset
from collections import Counter
from transformers import AutoTokenizer, AutoModelForCausalLM

#-- set directories
output_folder = os.path.join(os.getcwd(),'output')
source_folder = os.path.join(os.getcwd(),'source')

#-- dataloader
def get_main_df(path):

    df = pd.read_csv(os.path.join(source_folder, path),index_col=0) #-- this is the original dataframe without LLM responses
    df = df.rename(columns={'comparison.name':'comparison_name', 'outcome.name':'outcome_name', 'response_ChatGPT':'gold_answer_GPT4'}) #-- GPT4 column provides gold answers here
    df['human_response'] = pd.read_csv(os.path.join(source_folder,'human_gold_labels.csv'),index_col=0)
    df['MV'] = ['negative'] * len(df) #-- naive MV that votes 'negative'

    return df

##### API access #####

#-- groq API access is used for querying several large LLMs
def get_api_key(path):

    with open(os.path.join(source_folder, path), 'r') as file:
        key = file.readline()

    return key

#-- prompting groq models
def prompt_groq(df, n_rows, api_key, call_kwargs, model):

    client = Groq(api_key=api_key) #-- load Groq client + API key

    preds = [] #-- container for output
    
    print(f'Generator: {model}')
    
    for i in range(len(df))[:n_rows]:
        
        print(f'Row {i} of {len(df)}')
        print('='*30)

        prompt=[
            {"role": "system", "content": "You are a helpful and knowledgeable assistant in the medical domain who always responds accurately and concisely."}, #-- set system message
            {"role": "user", "content": f"In a medical study on '{df.comparison_name[i]}', the outcome is '{df.outcome_name[i]}'. Is this considered a positive or negative health outcome? Please only respond with 'positive', 'negative' or 'neutral'."} #-- custom prompt input
            ]
                
        call_kwargs['messages'] = prompt
        call_kwargs['model'] = model
    
        chat_completion = client.chat.completions.create(**call_kwargs)
        response = chat_completion.choices[0].message.content

        preds.append(response)
    
    #-- add columns
    df.loc[:, model] = [pred.lower() for pred in preds]
    
    return df

#-- Google Cloud, generate gemini output

def prompt_gemini(df, n_rows, model):

    llm = genai.GenerativeModel(model)
    generation_config = genai.GenerationConfig(temperature=0, max_output_tokens=5, response_logprobs=True if model == 'gemini-1.5-flash-002' else False)

    preds,tokens,probs = [],[],[]

    for i in range(len(df))[:n_rows]:
        print(f'Row {i} of {len(df)}')
        print('='*30)

        prompt=f"In a medical study on '{df.comparison_name[i]}', the outcome is '{df.outcome_name[i]}'. Is this considered a positive or negative health outcome? Please respond only with 'positive', 'negative' or 'neutral'."

        response = llm.generate_content(prompt, generation_config=generation_config)
        preds.append(response.text)
        
        if model == 'gemini-1.5-flash-002':
            token = response.to_dict()['candidates'][0]['logprobs_result']['chosen_candidates'][0]['token']
            prob = response.to_dict()['candidates'][0]['logprobs_result']['chosen_candidates'][0]['log_probability']

            tokens.append(token)
            probs.append(prob)
    
    #-- add columns
    df.loc[:, model] = [pred.lower() for pred in preds]
    
    if model == 'gemini-1.5-flash-002':
        df.loc[:, model + '_tokens'] = tokens
        df.loc[:, model + '_logprobs'] = np.exp(probs)

    return df


##### Local models ######

#-- prompt model
def get_local_output(df, n_rows, model):
    
    preds = [] #-- container for output
    device = 'mps'
    
    tokenizer = AutoTokenizer.from_pretrained(model)
    tokenizer.pad_token = tokenizer.eos_token #-- llama3.2 specific setting

    generator = pipeline(model=model, tokenizer=tokenizer, device=device, torch_dtype=torch.float16)
    torch.set_default_device("mps")

    for i in range(len(df))[:n_rows]:
        print(f'Row {i} of {len(df)}')
        print('='*30)
        if 'gemma' not in model:
            prompt = [
                {"role": "system", "content": "You are a helpful and knowledgeable assistant in the medical domain who always responds accurately and concisely."},
                {"role": "user", "content": f"In a medical study on '{df.comparison_name[i]}', the outcome is '{df.outcome_name[i]}'. Is this considered a positive or negative health outcome? Please only respond with 'positive', 'negative' or 'neutral'."}
            ]
        else:
            prompt = [
                {"role": "user", "content": f"You are a helpful and knowledgeable assistant in the medical domain who always responds accurately and concisely. In a medical study on '{df.comparison_name[i]}', the outcome is '{df.outcome_name[i]}'. Is this considered a positive or negative health outcome? Please only respond with 'positive', 'negative' or 'neutral'."}
            ] 
        
        generation = generator(prompt,do_sample=False, max_new_tokens=3,temperature=None,top_p=None, return_full_text=False,)
        preds.append(generation[0]['generated_text'])
    
    df.loc[:, model] = [pred.lower() for pred in preds]

    #-- clear memory for next model
    torch.mps.empty_cache()
    gc.collect()

    return df

# #-- obtain logprobs of base model

def get_logprobs_local_models(df,n_rows, model_str):
    
    #-- load model locally
    device='mps'
    model = AutoModelForCausalLM.from_pretrained(model_str, device_map=device, torch_dtype=torch.float16)
    tokenizer = AutoTokenizer.from_pretrained(model_str)
    tokenizer.pad_token = None

    probs = []
    #validation = []
    
    for i in range(len(df))[:n_rows]:

        #-- Prepare the input as before
        
        if 'gemma' not in model_str:
            chat = [
                {"role": "system", "content": "You are a helpful and knowledgeable assistant in the medical domain who always responds accurately and concisely."},
                {"role": "user", "content": f"In a medical study on '{df.comparison_name[i]}', the outcome is '{df.outcome_name[i]}'. Is this considered a positive or negative health outcome? Please only respond with 'positive', 'negative' or 'neutral'."}
            ]
        else:
            chat = [
                {"role": "user", "content": f"You are a helpful and knowledgeable assistant in the medical domain who always responds accurately and concisely. In a medical study on '{df.comparison_name[i]}', the outcome is '{df.outcome_name[i]}'. Is this considered a positive or negative health outcome? Please only respond with 'positive', 'negative' or 'neutral'."}
            ] 

        #-- Apply chat template
        formatted_chat = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        
        #-- Tokenize chat 
        inputs = tokenizer(formatted_chat, return_tensors="pt", add_special_tokens=False)
        #-- to same device the model is on (mps)
        inputs = {key: tensor.to(model.device) for key, tensor in inputs.items()}
        
        #-- get model outputs
        outputs = model.generate(**inputs, max_new_tokens=1, do_sample=None, temperature=None,
                                 return_dict_in_generate=True, output_scores=True,
                                 pad_token_id=tokenizer.eos_token_id)
        
        #-- compute transition scores
        transition_scores = model.compute_transition_scores(outputs.sequences, outputs.scores, normalize_logits=True)
        #-- postprocessing
        input_length = inputs['input_ids'].shape[1]
        generated_tokens = outputs.sequences[:, input_length:]
        for tok, score in zip(generated_tokens[0], transition_scores[0]):
            #-- | token | token string | logits | probability
            # print(f"| {tok:5d} | {tokenizer.decode(tok):8s} | {score.cpu():.4f} | {np.exp(score.cpu()):.2%}") #-- if validation is needed
            probs.append(np.exp(score.cpu().item()))
            #validation.append(tokenizer.decode(tok))
    
    df.loc[:, model_str + '_probs'] = [p for p in probs]
    #df.loc[:, model_str + '_validation'] = [v for v in validation] #-- to see if predictions align

    #-- clear memory for next model
    torch.mps.empty_cache()
    gc.collect()

    return df


##### Postprocessing ######

#-- postprocessing/tidying output
def standardise_output(output_col):
    
    neg,neu,pos = 'negative','neutral','positive'
    
    if neg in output_col:
        return 'neg'
    elif neu in output_col:
        return 'neu'
    elif pos in output_col:
        return 'pos'
    else:
        return 'neg' #-- replace with most frequent label
 
def standardise_all_output(df,output_col):

    df[output_col + '_cleaned'] = df.apply(lambda row: standardise_output(row[output_col]), axis=1)
    
    return df

#-- getting MV labels for RCTs belonging to multiple reviews
def get_MV_reviews(df, models):

    dict = {key + '_MV_review': value for key, value in zip(models, [[] for _ in range(len(models))])} #-- ugly but to prevent shallow copies

    for id in df.id.unique():

        df_tmp = df[df.id == id]
        #print(id)

        for model in models:
            #print(model)
            vals = df_tmp[model+'_cleaned'].tolist()      
            #print(vals)
            dict[model + '_MV_review'].append(Counter(vals).most_common(1)[0][0])

        #print()
    
    return pd.DataFrame.from_dict(dict)