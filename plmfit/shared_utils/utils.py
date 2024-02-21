#from plmfit.language_models.progen2.models.progen.modeling_progen import ProGenForCausalLM
import torch
import json
import pandas as pd
from tokenizers import Tokenizer


#def load_model(model_name):
#   return ProGenForCausalLM.from_pretrained(f'./plmfit/language_models/progen2/checkpoints/{model_name}')


def load_embeddings(data_type, embs):
    embs_file = f'./plmfit/data/{data_type}/embeddings/{embs}'
    return torch.load(f'{embs_file}.pt', map_location=torch.device('cpu'))


def load_dataset(data_type):
    return pd.read_csv(f'./plmfit/data/{data_type}/{data_type}_data_full.csv')


def get_wild_type(data_type):
    file = f'./plmfit/data/{data_type}'
    wild_type_f = open(f'{file}/wild_type.json')
    wt = json.load(wild_type_f)['wild_type']
    return wt


def load_tokenizer(model_name):
    model_file = ''
    if 'progen2' in model_name:
        model_file = 'progen2'
    file = f'./plmfit/language_models/{model_file}/tokenizer.json'

    with open(file, 'r') as f:
        return Tokenizer.from_str(f.read())


def load_head_config(config_file):
    file = f'./plmfit/models/{config_file}'
    config_f = open(f'{file}.json')
    config = json.load(config_f)
    print(config)
    return config


def one_hot_encode(seqs):
    return torch.tensor([0])


def categorical_encode(seqs, tokenizer, max_len, add_bos=False, add_eos=False, logger = None):
    if logger != None:
        logger.log(f'Initiating categorical encoding')
        logger.log(f'Memory needed for encoding: {len(seqs) * max_len * 4}B')

    # Adjust max_len if BOS or EOS tokens are to be added
    internal_max_len = max_len + int(add_bos) + int(add_eos)

    seq_tokens = tokenizer.get_vocab()['<|pad|>'] * torch.ones((len(seqs), internal_max_len), dtype=int)
    for itr, seq in enumerate(seqs):
         # Encode the sequence without adding special tokens by the tokenizer itself
        encoded_seq_ids = tokenizer.encode(seq, add_special_tokens=False).ids

        # Prepare sequence with space for BOS and/or EOS if needed
        sequence = []
        if add_bos:
            sequence.append(tokenizer.get_vocab()['<|bos|>'])
        sequence.extend(encoded_seq_ids[:max_len])  # Ensure the core sequence does not exceed user-specified max_len
        if add_eos:
            sequence.append(tokenizer.get_vocab()['<|eos|>'])

        # Truncate the sequence if it exceeds internal_max_len
        truncated_sequence = sequence[:internal_max_len]

        # Update the seq_tokens tensor
        seq_len = len(truncated_sequence)
        seq_tokens[itr, :seq_len] = torch.tensor(truncated_sequence, dtype=torch.long)

        if itr == 0 and logger is not None:
            logger.log(f'First sequence tokens: {seq_tokens[0].tolist()}')
    if logger != None:
        logger.log(f'Categorical encoding finished')
    return seq_tokens


def get_parameters(model, print_w_mat=False):
    s = 0
    c = 0
    for name, p in model.named_parameters():

        c += 1
        if print_w_mat:
            print(f' {name} size : {p.shape} trainable:{p.requires_grad}')
        s += p.numel()

    return s


def set_trainable_parameters(model, ft='all'):

    for name, p in model.named_parameters():
        p.requires_grad = True

    return


def read_fasta(file_path):
    sequences = {}
    current_sequence_id = None
    current_sequence = []

    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            if line.startswith('>'):
                # This line contains the sequence identifier
                if current_sequence_id is not None:
                    sequences[current_sequence_id] = ''.join(current_sequence)
                current_sequence_id = line[1:]
                current_sequence = []
            else:
                # This line contains sequence data
                if current_sequence_id is not None:
                    current_sequence.append(line)

    # Add the last sequence to the dictionary
    if current_sequence_id is not None:
        sequences[current_sequence_id] = ''.join(current_sequence)

    return sequences

def log_model_info(log_file_path, data_params, model_params, training_params, eval_metrics):
    with open(log_file_path, 'w') as log_file:
        log_file.write("Data Parameters:\n")
        for param, value in data_params.items():
            log_file.write(f"{param}: {value}\n")

        log_file.write("\nModel Parameters:\n")
        for param, value in model_params.items():
            log_file.write(f"{param}: {value}\n")
        
        log_file.write("\nTraining Parameters:\n")
        for param, value in training_params.items():
            log_file.write(f"{param}: {value}\n")
        
        log_file.write("\nEvaluation Metrics:\n")
        for metric, value in eval_metrics.items():
            log_file.write(f"{metric}: {value}\n")
    
    print(f"Model information logged to {log_file_path}")

def convert_to_number(s):
    try:
        # First, try to convert the string to an integer
        return int(s)
    except ValueError:
        # If converting to an integer fails, try to convert it to a float
        try:
            return float(s)
        except ValueError:
            # If both conversions fail, return the original string or an indication that it's not a number
            return None  # or return s to return the original string