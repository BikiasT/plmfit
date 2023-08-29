import os
import math
import pandas as pd
from language_models.progen2.models.progen.modeling_progen import ProGenForCausalLM
from tokenizers import Tokenizer
import torch
import time
from scipy.stats.stats import pearsonr   
import json
import matplotlib.pyplot as plt
from transformers import AutoTokenizer, EsmForSequenceClassification
import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import torch.nn as nn
import torch.utils.data as data_utils
from torch.nn import init
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler

import logger as l
import argparse
import utils

from models.models import MLP, LogisticRegression, AdapterLayer
import ft_frameworks


parser = argparse.ArgumentParser(description='plmfit_args')
parser.add_argument('--model_name', type=str, default='progen2-small') ## options ['progen2-small', 'progen2-xlarge', 'progen2-oas', 'progen2-medium', 'progen2-base', 'progen2-BFD90' , 'progen2-large']
parser.add_argument('--ft_method', type=str , default='feature_extraction')
parser.add_argument('--data_type', type=str , default= 'gb1')
parser.add_argument('--data_file_name', type=str , default= 'data_train')############# here you specifcy the different splits
parser.add_argument('--embs', type=str , default= 'gb1_embs_progen2-small_0_mean')
parser.add_argument('--head', type=str , default= 'mlp')
parser.add_argument('--head_config', type=str , default= 'config_mlp')
parser.add_argument('--task', type=str , default= 'cls')

parser.add_argument('--gpus', type=int , default=0) 
parser.add_argument('--gres', type=str , default='gpumem:24g') 
parser.add_argument('--mem-per-cpu', type=int , default= 0)
parser.add_argument('--nodes', type=int , default= 1)



parser.add_argument('--batch_size', type=int , default= 1)
parser.add_argument('--epochs', type=int , default= 1)


args = parser.parse_args()  

logger = l.Logger(f'logger_{args.model_name}_{args.ft_method}_{args.head}_{args.data_type}_SPECS:_filename:{args.data_file_name}_gpus:{args.gpus}_gres:{args.gres}_nodes:{args.nodes}.txt')
 

if __name__=='__main__':
    
    model = utils.load_model(args.model_name)
    data = utils.load_dataset(args.data_type , args.data_file_name)
    tokenizer = utils.load_tokenizer(args.model_name)
    wild_type = utils.get_wild_type(args.data_type)
  
    
############# Preparing input token (embeddings, one hot encoded or categorical encoded)
    embs = None
    
    if args.ft_method == 'feature_extraction' : ## added False here to not load embedding during development
    
        embs = utils.load_embeddings(args.data_type, args.embs)
        
    elif args.ft_method == 'feature_extraction' and  args.embs == 'one-hot-encode':
        
        embs = utils.one_hot_encode(data['aa_seq'].values)
              
    else:
        
        embs = utils.categorical_encode(data['aa_seq'].values)
        
        
    assert embs!= None, ' embeddings did not intialize'
    
########### Initializing the task specific head

    head = None
    
    if args.head == 'mlp' :
        
        config = utils.load_head_config(args.head_config)
        assert args.head == config["network_type"], f'The loaded configuration ("{config["network_type"]}") does not match the specified architecture "{args.head}". Make sure to upload a configuration with "network_type":"{args.head}"'
        head = MLP(config['input_len'], config['hidden_len'], config['output_len'], config['activation_function'], config['dropout'])

    assert head != None, f' {args.task} head did not initialize'
    
########### Prepare data loaders

    data_train = data[data['set'] == 'train']
    embs_train = embs[data_train.index]
    data_valid = data[data['set'] == 'test'] # TODO: instead of 'test' save as 'valid' in training set
    embs_test = embs[data_valid.index]
    
    train_dataset = data_utils.TensorDataset( embs_train , torch.tensor(data_train['score'].values))  
    valid_dataset = data_utils.TensorDataset( embs_test  , torch.tensor(data_valid['score'].values))  
    
    
########### Concat pretraind model with task specific head (need to validate that dimenison match)
    
    #TODO : Check combatibility
    assert head.in_.in_features == embs.shape[1], f'Embeddings dimension ({embs.shape[1]}) is not compatible with the input size of the task specific head ({head.in_.in_features}) . Change "input_len" to {embs.shape[1]} in config file : {args.head_config}'
    
    ft_model = None
    
    if args.ft_method == 'feature_extraction':
        
        ft_model = ft_frameworks.feature_extraction(train_dataset , head, lr = 0.1 , epochs = 5 )
        
    elif args.ft_method == 'retrain':
        
        ft_model = nn.Sequential(
          model,
          head
         )
        
    elif args.ft_method == 'ulmfit':
        
        print('ULMFIT')
        
    elif args.ft_method == 'lightweight':
        
        print('LIGHTWEIGHT')

    assert ft_model != None, f' {args.task} head did not initialize'


    #TODO : Save ft_model after finetuning
    
    
    
    
    
    
    
    
