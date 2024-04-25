import torch
from plmfit.logger import Logger
import os
import argparse
from plmfit.models.fine_tuning import FullRetrainFineTuner, LowRankAdaptationFineTuner
from plmfit.models.lightning_model import LightningModel
import plmfit.shared_utils.utils as utils
import plmfit.shared_utils.data_explore as data_explore
import plmfit.models.downstream_heads as heads
import traceback
import lightning as L
from lightning.pytorch.loggers import TensorBoardLogger
from lightning.pytorch.utilities.deepspeed import convert_zero_checkpoint_to_fp32_state_dict
from lightning.pytorch.callbacks import DeviceStatsMonitor
import torch.nn.functional as F
from deepspeed.runtime.zero.stage3 import estimate_zero3_model_states_mem_needs_all_live

parser = argparse.ArgumentParser(description='plmfit_args')
# options ['progen2-small', 'progen2-xlarge', 'progen2-oas', 'progen2-medium', 'progen2-base', 'progen2-BFD90' , 'progen2-large']
parser.add_argument('--plm', type=str, default='progen2-small')
parser.add_argument('--ft_method', type=str, default='feature_extraction')
parser.add_argument('--data_type', type=str, default='aav')
# here you specifcy the different splits
parser.add_argument('--data_file_name', type=str, default='data_train')

parser.add_argument('--head_config', type=str, default='linear_head_config.json')
parser.add_argument('--ray_tuning', type=str, default="False")

parser.add_argument('--split', default=None)

parser.add_argument('--function', type=str, default='extract_embeddings')
parser.add_argument('--reduction', type=str, default='mean',
                    help='Reduction technique')
parser.add_argument('--layer', type=str, default='last',
                    help='PLM layer to be used')
parser.add_argument('--output_dir', type=str, default='default',
                    help='Output directory for created files')
parser.add_argument('--experiment_name', type=str, default='default',
                    help='Output directory for created files')
parser.add_argument('--experiment_dir', type=str, default='default',
                    help='Output directory for created files')

parser.add_argument('--logger', type=str, default='remote')

parser.add_argument('--cpus', default=1)
parser.add_argument('--gpus', default=0)
parser.add_argument('--nodes', type=int, default=1)

parser.add_argument('--beta', default="False")
parser.add_argument('--experimenting', default="False")

NUM_WORKERS = 0

# Deprecated. Moved to utils.
def init_plm(model_name, logger):
    from plmfit.models.pretrained_models import Antiberty, BetaESMFamily, ProGenFamily, ProteinBERTFamily, AnkhFamily
    model = None
    supported_progen2 = ['progen2-small', 'progen2-medium', 'progen2-xlarge']
    supported_ESM = ["esm2_t6_8M_UR50D", "esm2_t12_35M_UR50D",
                     "esm2_t30_150M_UR50D", "esm2_t33_650M_UR50D","esm2_t36_3B_UR50D"]
    supported_Ankh = ['ankh-base', 'ankh-large', 'ankh2-large']
    supported_Proteinbert = ['proteinbert']

    if 'progen' in model_name:
        assert model_name in supported_progen2, 'Progen version is not supported'
        model = ProGenFamily(model_name, logger)

    elif 'esm' in model_name:
        assert model_name in supported_ESM, 'ESM version is not supported'
        model = ESMFamily(model_name,logger)
        #model = BetaESMFamily(model_name, logger)

    elif 'ankh' in model_name:
        assert model_name in supported_Ankh, 'Ankh version is not supported'
        model = AnkhFamily(model_name)
    elif 'antiberty' in args.plm:
        model = Antiberty()
    elif 'proteinbert' in model_name:
        assert model_name in supported_Proteinbert, 'ProteinBERT version is not supported'
        model = ProteinBERTFamily(logger)
    else:
        raise 'PLM not supported'

    return model

# MODULARITY DONE
# TODO: Lightning implementation
def run_extract_embeddings(args, logger):
    from plmfit.functions import extract_embeddings
    extract_embeddings(args=args, logger=logger)

# MODULARITY DONE
# TODO: Lightning implementation
def run_feature_extraction(args, logger):
    from plmfit.functions import feature_extraction
    feature_extraction(args=args, logger=logger)

def lora_lightning(args, logger):
    # Load dataset
    data = utils.load_dataset(args.data_type)
    if args.experimenting == "True": data = data.sample(1000)
    split = None if args.split is None else data[args.split]

    model = init_plm(args.plm, logger)
    assert model != None, 'Model is not initialized'
    utils.disable_dropout(model)

    head_config = utils.load_config(args.head_config)
    
    logger.save_data(vars(args), 'arguments')
    logger.save_data(head_config, 'head_config')
    
    network_type = head_config['architecture_parameters']['network_type']
    if network_type == 'linear':
        head_config['architecture_parameters']['input_dim'] = model.emb_layers_dim
        pred_model = heads.LinearHead(head_config['architecture_parameters'])
    elif network_type == 'mlp':
        head_config['architecture_parameters']['input_dim'] = model.emb_layers_dim
        pred_model = heads.MLP(head_config['architecture_parameters'])
    else:
        raise ValueError('Head type not supported')
    
    model.py_model.set_head(pred_model)
    meta_data = None # This is only used for 'mut_mean' reduction
    if args.reduction == 'mut_mean': 
        meta_data = data['mut_mask'].values
    model.py_model.reduction = args.reduction
    model.set_layer_to_use(args.layer)
    model.py_model.layer_to_use = model.layer_to_use
    encs = model.categorical_encode(data)

    scores = data['score'].values if head_config['architecture_parameters']['task'] == 'regression' else data['binary_score'].values
    training_params = head_config['training_parameters']
    data_loaders = utils.create_data_loaders(
            encs, scores, scaler=training_params['scaler'], 
            batch_size=training_params['batch_size'], 
            validation_size=training_params['val_split'], 
            dtype=torch.int8, 
            split=split,
            num_workers=NUM_WORKERS,
            meta_data=meta_data
        )
    
    fine_tuner = LowRankAdaptationFineTuner(training_config=training_params, model_name=args.plm, logger=logger)
    model = fine_tuner.set_trainable_parameters(model)
 
    utils.trainable_parameters_summary(model, logger)
    model.py_model.task = pred_model.task
    
    model = LightningModel(model.py_model, head_config['training_parameters'], plmfit_logger=logger, log_interval=100)
    lightning_logger = TensorBoardLogger(save_dir=logger.base_dir, version=0, name="lightning_logs")
    model.experimenting = args.experimenting == "True" # If we are in experimenting mode

    trainer = L.Trainer(
        default_root_dir=logger.base_dir,
        logger=lightning_logger, 
        max_epochs=model.hparams.epochs, 
        enable_progress_bar=False, 
        accumulate_grad_batches=model.gradient_accumulation_steps(),
        gradient_clip_val=model.gradient_clipping(),
        limit_train_batches=model.epoch_sizing(),
        limit_val_batches=model.epoch_sizing(),
        devices=args.gpus,
        strategy='deepspeed_stage_3_offload',
        precision=16,
        callbacks=[model.early_stopping()]
    )

    estimate_zero3_model_states_mem_needs_all_live(model, num_gpus_per_node=int(args.gpus), num_nodes=1)

    trainer.strategy.load_full_weights = True
    trainer.strategy.initial_scale_power = 20
    trainer.strategy.loss_scale_window = 2000
    trainer.strategy.min_loss_scale = 0.25

    try:
        trainer.fit(model, data_loaders['train'], data_loaders['val'])
    except Exception as e:
        # Check if the specific deepspeed minimum loss scale exception is raised
        if "Current loss scale already at minimum" in str(e):
            logger.log("Minimum loss reached. Ending training...")
        else:
            # If it's a different kind of exception, you might want to re-raise it
            raise e

    model = convert_zero_checkpoint_to_fp32_state_dict(f'{logger.base_dir}/lightning_logs/best_model.ckpt', f'{logger.base_dir}/best_model.ckpt')
    
    trainer.test(model=model, ckpt_path=f'{logger.base_dir}/best_model.ckpt', dataloaders=data_loaders['test'])

    loss_plot = data_explore.create_loss_plot(json_path=f'{logger.base_dir}/{logger.experiment_name}_loss.json')
    logger.save_plot(loss_plot, "training_validation_loss")

    if pred_model.task == 'classification':
        fig, _ = data_explore.plot_roc_curve(json_path=f'{logger.base_dir}/{logger.experiment_name}_metrics.json')
        logger.save_plot(fig, 'roc_curve')
        fig = data_explore.plot_confusion_matrix_heatmap(json_path=f'{logger.base_dir}/{logger.experiment_name}_metrics.json')
        logger.save_plot(fig, 'confusion_matrix')
    elif pred_model.task == 'regression':
        fig = data_explore.plot_actual_vs_predicted(json_path=f'{logger.base_dir}/{logger.experiment_name}_metrics.json')
        logger.save_plot(fig, 'actual_vs_predicted')

def full_retrain(args, logger):
    # Load dataset
    data = utils.load_dataset(args.data_type)
    split = None if args.split is None else data[args.split]

    model = init_plm(args.plm, logger)
    assert model != None, 'Model is not initialized'
    
    head_config = utils.load_config(args.head_config)
    
    logger.save_data(vars(args), 'arguments')
    logger.save_data(head_config, 'head_config')

    network_type = head_config['architecture_parameters']['network_type']
    if network_type == 'linear':
        head_config['architecture_parameters']['input_dim'] = model.emb_layers_dim
        pred_model = heads.LinearHead(head_config['architecture_parameters'])
    elif network_type == 'mlp':
        head_config['architecture_parameters']['input_dim'] = model.emb_layers_dim
        pred_model = heads.MLP(head_config['architecture_parameters'])
    else:
        raise ValueError('Head type not supported')
    
    utils.freeze_parameters(model.py_model)
    utils.set_trainable_parameters(pred_model)
    model.py_model.set_head(pred_model)
    utils.get_parameters(model.py_model, logger=logger)
    encs = model.categorical_encode(data)
    logger.log(model.py_model)
    scores = data['score'].values if head_config['architecture_parameters']['task'] == 'regression' else data['binary_score'].values
    training_params = head_config['training_parameters']
    data_loaders = utils.create_data_loaders(
            encs, scores, scaler=training_params['scaler'], batch_size=training_params['batch_size'], validation_size=training_params['val_split'], dtype=torch.int8, split=split)
    fine_tuner = FullRetrainFineTuner(training_config=training_params, logger=logger)
    model.py_model.task = pred_model.task
    fine_tuner.train(model.py_model, dataloaders_dict=data_loaders)

def feature_extraction_lightning(config, args, logger, on_ray_tuning=False):
    # Load dataset
    data = utils.load_dataset(args.data_type)
    head_config = config if not on_ray_tuning else utils.adjust_config_to_int(config)
    split = None if args.split is None else data[args.split]
    
    # Load embeddings and scores
    ### TODO : Load embeddings if do not exist
    embeddings = utils.load_embeddings(emb_path=f'{args.output_dir}/extract_embeddings', data_type=args.data_type, model=args.plm, layer=args.layer, reduction=args.reduction)
    assert embeddings != None, "Couldn't find embeddings, you can use extract_embeddings function to save {}"

    scores = data['score'].values if head_config['architecture_parameters']['task'] == 'regression' else data['binary_score'].values
    scores = torch.tensor(scores, dtype=torch.float32)

    training_params = head_config['training_parameters']
    data_loaders = utils.create_data_loaders(
            embeddings, scores, scaler=training_params['scaler'], batch_size=training_params['batch_size'], validation_size=training_params['val_split'], split=split, num_workers=NUM_WORKERS)
    
    logger.save_data(vars(args), 'arguments')
    logger.save_data(head_config, 'head_config')

    network_type = head_config['architecture_parameters']['network_type']
    if network_type == 'linear':
        head_config['architecture_parameters']['input_dim'] = embeddings.shape[1]
        pred_model = heads.LinearHead(head_config['architecture_parameters'])
    elif network_type == 'mlp':
        head_config['architecture_parameters']['input_dim'] = embeddings.shape[1]
        pred_model = heads.MLP(head_config['architecture_parameters'])
    else:
        raise ValueError('Head type not supported')
    
    utils.set_trainable_parameters(pred_model)
    
    model = LightningModel(pred_model, head_config['training_parameters'], plmfit_logger=logger, log_interval=100)
    lightning_logger = TensorBoardLogger(save_dir=logger.base_dir, version=0, name="lightning_logs")

    callbacks = [DeviceStatsMonitor(True)]
    if model.early_stopping is not None: callbacks.append(model.early_stopping)
    if on_ray_tuning:
        ray_callback = TuneReportCallback(
            {
                "loss": "val_loss"
            },
            on="validation_end"
        )
        callbacks.append(ray_callback)


    trainer = L.Trainer(
        default_root_dir=logger.base_dir,
        logger=lightning_logger, 
        max_epochs=model.hparams.epochs, 
        enable_progress_bar=False, 
        accumulate_grad_batches=model.gradient_accumulation_steps(),
        gradient_clip_val=model.gradient_clipping(),
        limit_train_batches=model.epoch_sizing(),
        limit_val_batches=model.epoch_sizing(),
        strategy='deepspeed_stage_3_offload',
        precision=16,
        callbacks=callbacks
    )

    trainer.strategy.load_full_weights = True

    trainer.fit(model, data_loaders['train'], data_loaders['val'])

    model = convert_zero_checkpoint_to_fp32_state_dict(f'{logger.base_dir}/lightning_logs/best_model.ckpt', f'{logger.base_dir}/best_model.ckpt')
    
    trainer.test(model=model, ckpt_path=f'{logger.base_dir}/best_model.ckpt', dataloaders=data_loaders['test'])

    loss_plot = data_explore.create_loss_plot(json_path=f'{logger.base_dir}/{logger.experiment_name}_loss.json')
    logger.save_plot(loss_plot, "training_validation_loss")

    if pred_model.task == 'classification':
        fig, _ = data_explore.plot_roc_curve(json_path=f'{logger.base_dir}/{logger.experiment_name}_metrics.json')
        logger.save_plot(fig, 'roc_curve')
        fig = data_explore.plot_confusion_matrix_heatmap(json_path=f'{logger.base_dir}/{logger.experiment_name}_metrics.json')
        logger.save_plot(fig, 'confusion_matrix')
    elif pred_model.task == 'regression':
        fig = data_explore.plot_actual_vs_predicted(json_path=f'{logger.base_dir}/{logger.experiment_name}_metrics.json')
        logger.save_plot(fig, 'actual_vs_predicted')

# MODULARITY DONE
# TODO: Lightning implementation
def run_onehot(args, logger):
    from plmfit.functions import onehot
    onehot(args, logger)

if __name__ == '__main__':
    args = parser.parse_args()
    experiment_dir = args.experiment_dir
    if not os.path.exists(experiment_dir):
        os.makedirs(experiment_dir, exist_ok=True)
        
    # Removing the output_dir prefix from experiment_dir
    trimmed_experiment_dir = experiment_dir.removeprefix(f"{args.output_dir}/")
    logger = Logger(
        experiment_name = args.experiment_name, 
        base_dir= args.experiment_dir, 
        log_to_server=args.logger!='local', 
        server_path=f'{trimmed_experiment_dir}'
    )
    try:
        if args.function == 'extract_embeddings': run_extract_embeddings(args, logger)
        elif args.function == 'fine_tuning':
            if args.ft_method == 'feature_extraction': run_feature_extraction(args, logger)
            elif args.ft_method == 'lora':
                lora_lightning(args, logger)
            elif args.ft_method == 'full':
                full_retrain(args, logger)
            else:
                raise ValueError('Fine Tuning method not supported')
        elif args.function == 'one_hot': run_onehot(args, logger)
        else: raise ValueError('Function not supported')

        logger.log("\n\nEnd of process", force_send=True)
    except:
        logger.mute = False
        stack_trace = traceback.format_exc()
        logger.log(stack_trace, force_send=True)
