import os
from plmfit.language_models.progen2.models.progen.modeling_progen import ProGenForCausalLM
from plmfit.language_models.proteinbert import load_pretrained_model
from plmfit.language_models.proteinbert.conv_and_global_attention_model import get_model_with_hidden_layers_as_outputs


import plmfit.shared_utils.utils as utils
import torch.nn as nn
import plmfit.logger as l
import torch
import torch.utils.data as data_utils
from torch.utils.data import DataLoader
import time
from abc import abstractmethod
from plmfit.models.fine_tuning import *
from tokenizers import Tokenizer
from transformers import AutoTokenizer, AutoModel, EsmForMaskedLM
from antiberty import AntiBERTyRunner
from numpy import array


class IPretrainedProteinLanguageModel(nn.Module):

    name: str
    py_model: nn.Module
    head: nn.Module
    head_name: str
    no_parameters: int
    emb_layers_dim: int
    output_dim: int

    def __init__(self):
        super().__init__()
        self.head_name = 'none'
        pass

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def get_py_model(self):
        return self.py_model

    def set_py_model(self, py_model):
        self.py_model = py_model

    def get_tokenizer(self):
        return self.tokenizer

    def set_tokenizer(self, tokenizer):
        self.tokenizer = tokenizer

    @abstractmethod
    def concat_task_specific_head(self, head):
        pass

    @abstractmethod
    def extract_embeddings(self, data_type, batch_size, layer=11, reduction='mean'):
        pass

    @abstractmethod
    def fine_tune(self, data_type, fine_tuner, train_split_name, optimizer, loss_f):
        pass

    @abstractmethod
    def evaluate(self, data_type):
        pass

    @abstractmethod
    def forward(self, src):
        pass

# TODO: infere based on aa_seq list
    @abstractmethod
    def infere(self, aa_seq_list):
        pass

  # Implement class for every supported Portein Language Model family


class Antiberty(IPretrainedProteinLanguageModel):
    def __init__(self):
        super().__init__()
        self.name = 'antiberty'
        self.logger = l.Logger(
            f'{self.name}')
        self.model = AntiBERTyRunner()

    def extract_embeddings(self, data_type, layer, reduction, output_dir = 'default'):
        logger = self.logger
        device = 'cpu'
        fp16 = False
        device_ids = []
        if torch.cuda.is_available():
            device = "cuda:0"
            fp16 = True
            logger.log(f'Available GPUs : {torch.cuda.device_count()}')
            for i in range(torch.cuda.device_count()):
                logger.log(
                    f'Running on {torch.cuda.get_device_properties(i).name}')
                device_ids.append(i)

        else:
            logger.log(f'No gpu found rolling device back to {device}')

        batch_size = 1
        if output_dir == 'default':
            output_path = f'./plmfit/data/{data_type}/embeddings/'
        else:
            output_path = f'{output_dir}/{data_type}/embeddings/'
        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)

        start_emb_time = time.time()
        data = utils.load_dataset(data_type)
            
        logger = l.Logger(
            f'extract_embeddings_{data_type}_{self.name}_{reduction}')
        
        embs = torch.zeros((len(data), 1024)).to(device)

        for vh, vl in zip(data['V_h'], data['V_l']):
            start = time.time()
            out = self.model.embed([vh, vl])
            if reduction == 'mean':
                embs[i, 0:512] = torch.mean(out[0], dim=0)
                embs[i, 512:1024] = torch.mean(out[1], dim=0)
            elif reduction == 'sum':
                embs[i, 0:512] = torch.sum(out[0], dim=0)
                embs[i, 512:1024] = torch.sum(out[1], dim=0)
            elif reduction == 'bos':
                # Select the embeddings for the first token of each sequence in the batch
                embs[i, 0:512] = out[0][0, :]
                embs[i, 512:1024] = out[1][0, :]
            elif reduction == 'eos':
                # Select the embeddings for the last token of each sequence in the batch
                embs[i, 0:512] = out[0][-1, :]
                embs[i, 512:1024] = out[1][-1, :]
            else:
                raise ValueError('Unsupported reduction option')
            del out
            i = i + batch_size
            logger.log(
                f' {i} / {len(data)} | {time.time() - start:.2f}s ')
        
        torch.save(
            embs, os.path.join(output_path, f'{data_type}_{self.name}_embs_layer{layer}_{reduction}.pt'))
        t = torch.load(
            os.path.join(output_path, f'{data_type}_{self.name}_embs_layer{layer}_{reduction}.pt'))
        logger.log(
            f'Saved embeddings ({t.shape[1]}-d) as "{data_type}_{self.name}_embs_layer{layer}_{reduction}.pt" ({time.time() - start_emb_time:.2f}s)')
        return
                
        
class ProGenFamily(IPretrainedProteinLanguageModel):

    tokenizer: Tokenizer

    def __init__(self, progen_model_name: str):
        # IPretrainedProteinLanguageModel.__init__(self)
        super().__init__()
        self.name = progen_model_name
        self.logger = l.Logger(
            f'{self.name}')
        self.py_model = ProGenForCausalLM.from_pretrained(
            f'./plmfit/language_models/progen2/checkpoints/{progen_model_name}')

        self.logger.log("Initialized model")
        self.logger.log(self.py_model)
        self.no_parameters = utils.get_parameters(self.py_model)
        self.no_layers = len(self.py_model.transformer.h)
        self.output_dim = self.py_model.lm_head.out_features
        self.emb_layers_dim = self.py_model.transformer.h[0].attn.out_proj.out_features
        self.tokenizer = utils.load_tokenizer(progen_model_name)
        

    def concat_task_specific_head(self, head):
        # assert head.in_.in_features == self.output_dim, f'Head\'s input dimension ({head.in_.in_features}) is not compatible with {self.name}\'s output dimension ({self.output_dim}). To concat modules these must be equal.'
        # TODO: Add concat option with lm head or final transformer layer.
        self.head = head
        self.head_name = head.__class__.__name__  # parse name from variable
        self.no_parameters += utils.get_parameters(head)
        return

    def extract_embeddings(self, data_type, batch_size = 2, layer=11, reduction='mean', output_dir = 'default'):
        if output_dir == 'default':
            output_path = f'./plmfit/data/{data_type}/embeddings/'
        else:
            output_path = f'{output_dir}/{data_type}/embeddings/'
        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)
            
        logger = l.Logger(
            f'extract_embeddings_{data_type}_{self.name}_layer-{layer}_{reduction}')
        device = 'cpu'
        fp16 = False
        device_ids = []
        if torch.cuda.is_available():
            device = "cuda:0"
            fp16 = True
            logger.log(f'Available GPUs : {torch.cuda.device_count()}')
            for i in range(torch.cuda.device_count()):
                logger.log(
                    f'Running on {torch.cuda.get_device_properties(i).name}')
                device_ids.append(i)

        else:
            logger.log(f'No gpu found rolling device back to {device}')
        data = utils.load_dataset(data_type)
        start_enc_time = time.time()
        logger.log(f'Encoding {data.shape[0]} sequences....')
        encs = utils.categorical_encode(
            data['aa_seq'].values, self.tokenizer, max(data['len'].values), add_bos=True, add_eos=True, logger=logger)
        logger.log(
            f'Encoding completed! {time.time() -  start_enc_time:.4f}s')
        encs = encs.to(device)
        seq_dataset = data_utils.TensorDataset(encs)
        seq_loader = data_utils.DataLoader(
            seq_dataset, batch_size=batch_size, shuffle=False)
        logger.log(
            f'Extracting embeddings for {len(seq_dataset)} sequences...')

        # FIX: Find embeddings dimension either hard coded for model or real the pytorch model of ProGen. Maybe add reduction dimension as well
        embs = torch.zeros((len(seq_dataset), self.emb_layers_dim)).to(device)
        self.py_model = self.py_model.to(device)
        i = 0
        self.py_model.eval()
        logger.log(self.py_model)
        with torch.no_grad():
            with torch.cuda.amp.autocast(enabled=fp16):
                for batch in seq_loader:
                    start = time.time()
                    if layer == 'logits':
                        out = self.py_model(batch[0]).logits
                    else:
                        model_output = self.py_model(batch[0])
                        hidden_states = model_output.hidden_states  # Get all hidden states

                        # Log the shape of each layer's embeddings for the first batch
                        if i == 0:  # Assuming 'i' tracks the batch index; make sure it's reset appropriately
                            for layer_index, layer_output in enumerate(hidden_states):
                                logger.log(f'Layer {layer_index} shape: {layer_output.shape}')

                        # Determine the layer index based on the 'layer' description
                        if layer == 'last':
                            # The last hidden layer (not counting the logits layer)
                            selected_layer_index = len(hidden_states) - 1
                        elif layer == 'middle':
                            # Adjusted to consider the first transformer block as the "first" layer
                            selected_layer_index = 1 + (len(hidden_states) - 1) // 2
                        elif layer == 'first':
                            # The first transformer block after the input embeddings
                            selected_layer_index = 1  # Adjusted to 1 to skip the input embeddings
                        else:
                            # Fallback for numeric layer specification or unexpected strings
                            selected_layer_index = int(layer) if layer.isdigit() else 0

                        # Now select the specific layer's output
                        out = hidden_states[selected_layer_index]
                    # Log the shape of each layer's embeddings for the first batch
                    if i == 0:  # Assuming 'i' tracks the batch index; make sure it's reset appropriately
                        logger.log(f'{out[:, 0, :].size()}')
                    if reduction == 'mean':
                        embs[i: i + batch_size, :] = torch.mean(out, dim=1)
                        if i == 0:  # Assuming 'i' tracks the batch index; make sure it's reset appropriately
                            logger.log(f'{(torch.mean(out, dim=1)).size()}')
                    elif reduction == 'sum':
                        embs[i: i + batch_size, :] = torch.sum(out, dim=1)
                    elif reduction == 'bos':
                        # Select the embeddings for the first token of each sequence in the batch
                        embs[i: i + batch_size, :] = out[:, 0, :]
                    elif reduction == 'eos':
                        # Select the embeddings for the last token of each sequence in the batch
                        embs[i: i + batch_size, :] = out[:, -1, :]
                    elif utils.convert_to_number(reduction) is not None:
                        # Select the embeddings for the i token of each sequence in the batch
                        embs[i: i + batch_size, :] = out[:, utils.convert_to_number(reduction), :]
                    else:
                        raise ValueError('Unsupported reduction option')
                    del out
                    i = i + batch_size
                    logger.log(
                        f' {i} / {len(seq_dataset)} | {time.time() - start:.2f}s ')

        torch.save(
            embs, os.path.join(output_path, f'{data_type}_{self.name}_embs_layer{layer}_{reduction}.pt'))
        t = torch.load(
            os.path.join(output_path, f'{data_type}_{self.name}_embs_layer{layer}_{reduction}.pt'))
        logger.log(
            f'Saved embeddings ({t.shape[1]}-d) as "{data_type}_{self.name}_embs_layer{layer}_{reduction}.pt" ({time.time() - start_enc_time:.2f}s)')
        return

    def fine_tune(self, data_type, fine_tuner, train_split_name, optimizer, loss_f):

        assert self.head != None, 'Task specific head haven\'t specified.'
        logger = l.Logger(
            f'logger_fine_tune_{self.name}_{self.head_name}_{fine_tuner.method}_{data_type}.txt')
        data = utils.load_dataset(data_type)
        logger.log(f' Encoding {data.shape[0]} sequences....')
        start_enc_time = time.time()
        encs = utils.categorical_encode(
            data['aa_seq'].values, self.tokenizer, max(data['len'].values), add_bos=True, add_eos=True, logger=logger)
        logger.log(
            f' Encoding completed! {time.time() -  start_enc_time:.4f}s')
        data_train = data[data[train_split_name] == 'train']
        data_test = data[data[train_split_name] == 'test']
        encs_train = encs[data_train.index]
        encs_test = encs[data_test.index]
        train_dataset = data_utils.TensorDataset(
            encs_train, torch.tensor(data_train['score'].values))
        n_val_samples = int(fine_tuner.val_split * len(train_dataset))
        n_train_samples = len(train_dataset) - n_val_samples
        train_set, val_set = torch.utils.data.random_split(
            train_dataset, [n_train_samples, n_val_samples])
        test_dataset = data_utils.TensorDataset(
            encs_test, torch.tensor(data_test['score'].values))
        train_dataloader = DataLoader(
            train_set, batch_size=fine_tuner.batch_size, shuffle=True)
        valid_dataloader = DataLoader(
            val_set, batch_size=fine_tuner.batch_size, shuffle=True)
        test_dataloader = DataLoader(
            test_dataset, batch_size=fine_tuner.batch_size, shuffle=True)

        dataloader_dict = {'train': train_dataloader, 'val': valid_dataloader}

        fine_tuner .set_trainable_parameters(self)
        # Check if parameters of self model are affected just by calling them as argument
        # TODO: move the whole training loop in tuner method train
        training_start_time = time.time()
        fine_tuner.train(self, dataloader_dict, optimizer, loss_f, logger)
        logger.log(' Finetuning  ({}) on {} data completed after {:.4f}s '.format(
            fine_tuner.method, data_type, time.time() - training_start_time))
        self.fine_tuned = fine_tuner.method
        return

    def evaluate(self):
        return 0

    def forward(self, src):
        src = self.py_model(src).hidden_states[-1]
        src = torch.mean(src, dim=1)
        if self.head != None:
            src = self.head(src)
        return src

# TODO: Implement handler classes for different PLM families
class ESMFamily(IPretrainedProteinLanguageModel):
    tokenizer : AutoTokenizer
    
    def __init__(self , esm_version : str):
        super().__init__()
        self.version = esm_version 
        self.py_model = EsmForMaskedLM.from_pretrained(f'facebook/{esm_version}' , output_hidden_states = True)
        self.no_parameters = utils.get_parameters(self.py_model)
        self.no_layers = len(self.py_model.esm.encoder.layer)
        self.output_dim = self.py_model.lm_head.decoder.out_features
        self.emb_layers_dim =  self.py_model.esm.encoder.layer[0].attention.self.query.in_features
        self.tokenizer = AutoTokenizer.from_pretrained(f'facebook/{esm_version}') 
   
    
    def extract_embeddings(self , data_type , batch_size = 4 , layer = 48, reduction = 'mean',mut_pos = None):
        logger = l.Logger(f'logger_extract_embeddings_{data_type}_{self.version}_layer{layer}_{reduction}')
        device = 'cpu'
        fp16 = False
        device_ids = []
        if torch.cuda.is_available():
            device = "cuda:0"
            fp16 = True
            logger.log(f'Available GPUs : {torch.cuda.device_count()}')
            for i in range(torch.cuda.device_count()):
                logger.log(f' Running on {torch.cuda.get_device_properties(i).name}')
                device_ids.append(i)

        else:
            logger.log(f' No gpu found rolling device back to {device}')
        data = utils.load_dataset(data_type)
        start_enc_time = time.time()
        logger.log(f' Encoding {data.shape[0]} sequences....')
        encs = self.categorical_encode(data['aa_seq'].values, self.tokenizer,max(data['len'].values)) 
        logger.log(f' Encoding completed! {time.time() -  start_enc_time:.4f}s')
        encs = encs.to(device)
        
        seq_dataset = data_utils.TensorDataset(encs)
        seq_loader =  data_utils.DataLoader(seq_dataset, batch_size= batch_size, shuffle=False)
        logger.log(f'Extracting embeddings for {len(seq_dataset)} sequences...')
        
        if type(layer) == int:
            layer = [layer]
        
        if type(reduction) == str:
            reduction = [reduction]
        
        embs = torch.zeros(len(layer),len(reduction),len(seq_dataset), self.emb_layers_dim).to(device) ### FIX: Find embeddings dimension either hard coded for model or real the pytorch model of ProGen. Maybe add reduction dimension as well
        
        self.py_model = self.py_model.to(device)
        self.py_model.eval()
        
        i = 0
        with torch.no_grad():
            with torch.cuda.amp.autocast(enabled= fp16):
                for batch in seq_loader:
                    start = time.time()
                    out = self.py_model(batch[0]).hidden_states
                    for j in range(len(layer)):
                        lay = layer[j]
                        for k in range(len(reduction)):
                            if reduction[k] == 'mean':
                                embs[j,k,i : i+ batch_size, : ] = torch.mean(out[lay] , dim = 1)
                            elif reduction[k] == 'sum':
                                embs[j,k,i : i+ batch_size, : ] = torch.sum(out[lay] , dim = 1)
                            elif reduction[k] == 'eos':
                                embs[j,k,i : i+ batch_size, : ] = out[lay][:,-1]
                            elif reduction[k] == 'bos':
                                embs[j,k,i : i+ batch_size, : ] = out[lay][:,0]
                            elif reduction[k].startswith('pos'):
                                embs[j,k,i : i+ batch_size, : ] = out[lay][:,int(reduction[k][3:])]
                            elif reduction[k] == 'mut_mean':
                                n_pos = len(mut_pos)
                                f_pos = mut_pos[0]
                                for pos in mut_pos[1:]:
                                    out[lay][:,f_pos] = torch.add(out[lay][:,f_pos],out[lay][:,pos])
                                embs[j,k,i : i+ batch_size, : ] = torch.div(out[lay][:,f_pos],n_pos)
                            else:
                                raise 'Unsupported reduction option'
                    del out
                    i = i + batch_size
                    logger.log(f' {i} / {len(seq_dataset)} | {time.time() - start:.2f}s ') # | memory usage : {100 - memory_usage.percent:.2f}%

           
        os.makedirs(f'./plmfit/data/{data_type}/embeddings', exist_ok = True)
        for j in range(len(layer)):
            lay = layer[j]
            for k in range(len(reduction)):
                tmp = embs[j,k].detach().clone()
                torch.save(tmp,f'./plmfit/data/{data_type}/embeddings/{data_type}_{self.version}_embs_layer{layer[j]}_{reduction[k]}.pt')
                logger.log(f'Saved embeddings ({tmp.shape[1]}-d) as "{data_type}_{self.version}_embs_layer{layer[j]}_{reduction[k]}.pt" ({time.time() - start_enc_time:.2f}s)')
                del tmp
        return

    
    def fine_tune(self, data_type, fine_tuner , train_split_name, optimizer , loss_f ):
        assert self.head != None , 'Task specific head haven\'t specified.'
        logger = l.Logger(f'logger_fine_tune_{self.version}_{self.head_type}_{fine_tuner.method}_{data_type}.txt')
        data = utils.load_dataset(data_type) 
        #data = data[data[train_split_name] == 'train'].head(50)
        #data.reset_index(inplace = True) #### Remove after testing          
        logger.log(f' Encoding {data.shape[0]} sequences....')
        start_enc_time = time.time()
        encs = self.categorical_encode(data['aa_seq'].values, self.tokenizer , max(data['len'].values))
        logger.log(f' Encoding completed! {time.time() -  start_enc_time:.4f}s')
        data_train = data[data[train_split_name] == 'train']
        data_test = data[data[train_split_name] == 'test']
        encs_train = encs[data_train.index]
        encs_test = encs[data_test.index]
        train_dataset = data_utils.TensorDataset( encs_train , torch.tensor(data_train['score'].values))  
        n_val_samples = int(fine_tuner.val_split * len(train_dataset))
        n_train_samples = len(train_dataset) - n_val_samples 
        train_set, val_set = torch.utils.data.random_split(train_dataset , [n_train_samples, n_val_samples]) 
        test_dataset = data_utils.TensorDataset( encs_test  , torch.tensor(data_test['score'].values))             
        train_dataloader = DataLoader(train_set, batch_size = fine_tuner.batch_size , shuffle=True)
        valid_dataloader = DataLoader(val_set, batch_size = fine_tuner.batch_size , shuffle=True)
        #test_dataloader = DataLoader(test_dataset, batch_size = fine_tuner.batch_size, shuffle=True)
        
        dataloader_dict = { 'train' : train_dataloader , 'val' : valid_dataloader}
    
        fine_tuner .set_trainable_parameters(self)
        ## Check if parameters of self model are affected just by calling them as argument
            ##TODO: move the whole training loop in tuner method train
        training_start_time = time.time()
        fine_tuner.train(self, dataloader_dict , optimizer , loss_f , logger)
        logger.log(' Finetuning  ({}) on {} data completed after {:.4f}s '.format(fine_tuner.method , data_type , time.time() - training_start_time))
        self.fine_tuned = fine_tuner.method
        return

    
    def evaluate(self, data_type ):
        pass
    
    
    def categorical_encode(self, seqs, tokenizer , max_len):
        seq_tokens =  tokenizer.get_vocab()['<pad>'] * torch.ones((len(seqs) , max_len + 2) , dtype = int) ### Adding  to max_len because ESMTokenizer adds cls and eos tokens in the begging and the neding of aa_seq
        for itr , seq in enumerate(seqs):
            tok_seq = torch.tensor(tokenizer.encode(seq))
            seq_tokens[itr][:tok_seq.shape[0]] = tok_seq
        return seq_tokens



class ProteinBERTFamily(IPretrainedProteinLanguageModel):
    def __init__(self, bert_model_name: str):
        super().__init__()
        self.name = bert_model_name
        # Load the pre-trained BERT model. Replace with the appropriate method for BERT.
        pretrained_model_generator, input_encoder = load_pretrained_model()
        model = get_model_with_hidden_layers_as_outputs(pretrained_model_generator.create_model(1024))
        print(model)

    # Implement the abstract methods for BERT
    def concat_task_specific_head(self, head):
        # Implementation for BERT...
        pass

    def extract_embeddings(self, data_type, batch_size, layer, reduction):
        # Implementation for BERT...
        pass

    def fine_tune(self, data_type, fine_tuner, train_split_name, optimizer, loss_f):
        # Implementation for BERT...
        pass

class AnkhFamily(IPretrainedProteinLanguageModel):
    
    tokenizer : AutoTokenizer
    
    def __init__(self , ankh_version : str):
        super().__init__()
        self.version = ankh_version 
        self.py_model = AutoModel.from_pretrained(f'ElnaggarLab/{ankh_version}' , output_hidden_states = True)
        self.no_parameters = utils.get_parameters(self.py_model.encoder)
        self.no_layers = self.py_model.config.num_layers
        self.output_dim = self.py_model.config.vocab_size
        self.emb_layers_dim =  self.py_model.config.hidden_size
        self.tokenizer = AutoTokenizer.from_pretrained(f'ElnaggarLab/{ankh_version}')
        
    def extract_embeddings(self , data_type , batch_size = 4 , layer = 48, reduction = 'mean', mut_pos= None):
        logger = l.Logger(f'logger_extract_embeddings_{data_type}_{self.version}_layer{layer}_{reduction}')
        device = 'cpu'
        fp16 = False
        device_ids = []
        if torch.cuda.is_available():
            device = "cuda:0"
            fp16 = True
            logger.log(f'Available GPUs : {torch.cuda.device_count()}')
            for i in range(torch.cuda.device_count()):
                logger.log(f' Running on {torch.cuda.get_device_properties(i).name}')
                device_ids.append(i)

        else:
            logger.log(f' No gpu found rolling device back to {device}')
        data = utils.load_dataset(data_type)
        start_enc_time = time.time()
        logger.log(f' Encoding {data.shape[0]} sequences....')
        encs = self.categorical_encode(data['aa_seq'].values, self.tokenizer,max(data['len'].values)) 
        logger.log(f' Encoding completed! {time.time() -  start_enc_time:.4f}s')
        encs = encs.to(device)
        
        seq_dataset = data_utils.TensorDataset(encs)
        seq_loader =  data_utils.DataLoader(seq_dataset, batch_size= batch_size, shuffle=False)
        logger.log(f'Extracting embeddings for {len(seq_dataset)} sequences...')
        
        if type(layer) == int:
            layer = [layer]
        
        if type(reduction) == str:
            reduction = [reduction]
        
        embs = torch.zeros(len(layer),len(reduction),len(seq_dataset), self.emb_layers_dim).to(device) ### FIX: Find embeddings dimension either hard coded for model or real the pytorch model of ProGen. Maybe add reduction dimension as well
        
        self.py_model = self.py_model.encoder.to(device)
        self.py_model.eval()
        
        i = 0
        with torch.no_grad():
            #with torch.cuda.amp.autocast(enabled= fp16):
            for batch in seq_loader:
                start = time.time()
                out = self.py_model(batch[0]).hidden_states
                for j in range(len(layer)):
                    lay = layer[j]
                    for k in range(len(reduction)):
                        if reduction[k] == 'mean':
                            embs[j,k,i : i+ batch_size, : ] = torch.mean(out[lay] , dim = 1)
                        elif reduction[k] == 'sum':
                            embs[j,k,i : i+ batch_size, : ] = torch.sum(out[lay] , dim = 1)
                        elif reduction[k] == 'eos':
                            embs[j,k,i : i+ batch_size, : ] = out[lay][:,-1]
                        elif reduction[k].startswith('pos'):
                            embs[j,k,i : i+ batch_size, : ] = out[lay][:,int(reduction[k][3:])]
                        elif reduction[k] == 'mut_mean':
                            n_pos = len(mut_pos)
                            f_pos = mut_pos[0]
                            for pos in mut_pos[1:]:
                                out[lay][:,f_pos] = torch.add(out[lay][:,f_pos],out[lay][:,pos])
                            embs[j,k,i : i+ batch_size, : ] = torch.div(out[lay][:,f_pos],n_pos)
                        else:
                            raise 'Unsupported reduction option'
                del out
                i = i + batch_size
                logger.log(f' {i} / {len(seq_dataset)} | {time.time() - start:.2f}s ') # | memory usage : {100 - memory_usage.percent:.2f}%

           
        os.makedirs(f'./plmfit/data/{data_type}/embeddings', exist_ok = True)
        for j in range(len(layer)):
            lay = layer[j]
            for k in range(len(reduction)):
                tmp = embs[j,k].detach().clone()
                torch.save(tmp,f'./plmfit/data/{data_type}/embeddings/{data_type}_{self.version}_embs_layer{layer[j]}_{reduction[k]}.pt')
                logger.log(f'Saved embeddings ({tmp.shape[1]}-d) as "{data_type}_{self.version}_embs_layer{layer[j]}_{reduction[k]}.pt" ({time.time() - start_enc_time:.2f}s)')
                del tmp
        return
    
    def categorical_encode(self, seqs, tokenizer, max_len):
        seq_tokens =  tokenizer.get_vocab()['<pad>'] * torch.ones((len(seqs) , max_len + 1) , dtype = int) ### Adding  to max_len because ESMTokenizer adds cls and eos tokens in the begging and the neding of aa_seq
        for itr , seq in enumerate(seqs):
            tok_seq = torch.tensor(tokenizer.encode(seq))
            seq_tokens[itr][:tok_seq.shape[0]] = tok_seq
        return seq_tokens


class SapiesFamily():
    pass
