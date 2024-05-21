#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --tasks-per-node=1
#SBATCH --gpus-per-node=1
#SBATCH --time=16:00:00

export DATA_DIR='/cluster/home/estamkopoulo/plmfit_workspace/plmfit/plmfit'
export HF_HOME='/cluster/scratch/estamkopoulo/'
export HF_HUB_CACHE='/cluster/scratch/estamkopoulo/'
module load eth_proxy
module load gcc/8.2.0  python_gpu/3.11.2

nvcc --version
nvidia-smi
python3 plmfit --function $1 --layer $5 --reduction $4 \
         --data_type $2 --plm $3 --output_dir $6 --experiment_dir $7 --experiment_name $8
