import paramiko
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import tempfile
import getpass
from tqdm import tqdm


def establish_ssh_sftp_sessions(hostname, username, key_path=None):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if key_path and os.path.exists(key_path):
        print("Logging in with private key...")
        private_key = paramiko.RSAKey.from_private_key_file(key_path)
        ssh.connect(hostname, username=username, pkey=private_key)
    else:
        print("Private key not found or not specified. Falling back to password authentication...")
        password = getpass.getpass(prompt="Password for SSH connection: ")
        ssh.connect(hostname, username=username, password=password)
    sftp = ssh.open_sftp()
    return ssh, sftp


def find_and_download_json_files(ssh, sftp, base_folder, data_type, task_type, temp_dir):
    # Execute remote find command to get list of matching JSON files
    stdin, stdout, stderr = ssh.exec_command(
        f"find {base_folder} -type f -name '*{data_type}*{task_type}*_data.json'")
    file_paths = stdout.read().decode().splitlines()

    # Download each file to the temporary directory
    for remote_path in file_paths:
        filename = os.path.basename(remote_path)
        local_path = os.path.join(temp_dir, filename)
        sftp.get(remote_path, local_path)

    return [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if f.endswith('.json')]


def collect_metrics(json_files=None, csv_file=None, data_type='aav', task_type='regression', method_type='feature_extraction', use_mlp=False):
    # Ensure the categorical order
    model_order = ['proteinbert', 'progen2-small', 'esm2_t33_650M_UR50D',
                   'progen2-medium', 'esm2_t36_3B_UR50D', 'progen2-xlarge', 'esm2_t48_15B_UR50D']
    layer_order = ['first', 'quarter1', 'middle', 'quarter3', 'last']
    reduction_order = ['mean', 'cls']
    head_order = ['linear'] if not use_mlp else ['linear', 'mlp']
    reduction_methods = ['mean', 'bos', 'eos']

    # Initialize a list to store the collected data
    data = []
    seen_filenames = set()

    if json_files is not None:
        # Iterate over the found JSON files and extract the required metrics and details
        for file_path in json_files:
            with open(file_path, 'r') as file:
                json_data = json.load(file)
                metrics = json_data.get('metrics', {})

                # Extract details from the filename
                filename = os.path.basename(file_path)
                # Find model name
                model_name = next(
                    (m for m in model_order if m in filename), None)
                # Find layer
                layer = next((l for l in layer_order if l in filename), None)
                # Find reduction
                reduction = next(
                    (r for r in reduction_methods if r in filename), None)
                # Find head type
                head_type = next(
                    (h for h in head_order if h in filename), None)

                # Check if filename has already been processed
                if filename not in seen_filenames:
                    seen_filenames.add(filename)
                else:
                    continue

                # Depending on the task type, extract the relevant metrics
                entry = {
                    'File': filename,
                    'Model Name': model_name,
                    'Layer': layer,
                    'Reduction': reduction,
                    'Head Type': head_type
                }
                if task_type == 'classification':
                    entry['Accuracy'] = metrics.get('accuracy', None)
                    entry['MCC'] = metrics.get('mcc', None)
                    column_name = "MCC"
                elif task_type == 'regression':
                    entry['RMSE'] = metrics.get('rmse', None)
                    entry['Spearman'] = metrics.get('spearman', None)
                    column_name = "Spearman"
                data.append(entry)

        # Convert the collected data into a pandas DataFrame for easy tabular representation
        df = pd.DataFrame(data)

        # Combine 'bos' and 'eos' into 'cls' for the 'Reduction' column
        df['Reduction'] = df['Reduction'].replace({'bos': 'cls', 'eos': 'cls'})
        df['Model + Head'] = df['Model Name'] + ' + ' + df['Head Type']
        df['Layer + Reduction'] = df['Layer'] + ' + ' + df['Reduction']
    else:
        df = pd.read_csv(csv_file)
        column_name = "MCC" if task_type == 'classification' else "Spearman"

    # If use_mlp is True, remove columns related to mlp
    if not use_mlp:
        df = df[~df['Model + Head'].str.contains('mlp')]

    # Check for duplicate entries
    duplicates = df.duplicated(subset=['Layer + Reduction', 'Model + Head'])
    if duplicates.any():
        print(
            "Duplicate entries found for the combo 'Layer + Reduction' and 'Model + Head'")
        print(df[duplicates])
    # Pivot without sorting
    heatmap_data = df.pivot(index="Layer + Reduction",
                            columns="Model + Head", values=column_name)

    # Step 2: Reorder the pivoted DataFrame directly
    # Define the desired order for the axes
    model_head_order = [m + ' + ' + h for m in model_order for h in head_order]
    layer_reduction_order = [l + ' + ' +
                             r for l in layer_order for r in reduction_order]

    # Reindex the pivoted DataFrame to enforce the order
    heatmap_data = heatmap_data.reindex(
        index=layer_reduction_order, columns=model_head_order)

    # Plotting the heatmap with the color scale adjusted from -1 to 1
    # Slightly larger figure size for better readability
    plt.figure(figsize=(20 if use_mlp else 12, 10))
    sns.set(font_scale=1.05)  # Adjust font scale for better readability
    ax = sns.heatmap(heatmap_data, annot=True, cmap="RdBu_r", fmt=".3f", linewidths=.5,
                     cbar_kws={'label': column_name}, center=0, vmin=-1, vmax=1)
    # Main title and subtitle setup
    main_title = f'{data_type.upper()} - {task_type.upper()} Task | {method_type}'
    subtitle = f'{column_name} Across Models, Heads, Layers, and Reduction Methods'

    # Set the main title with more emphasis
    plt.suptitle(main_title, fontsize=20)

    # Set the subtitle with less emphasis and adjust its position
    plt.title(subtitle, fontsize=18, pad=20)

    # Adjust font size for x-axis labels
    plt.xticks(rotation=45, ha="right", fontsize=12)
    plt.yticks(rotation=0, fontsize=12)  # Adjust font size for y-axis labels
    plt.xlabel('Model + Head', fontsize=14)  # Explicit x-axis label
    plt.ylabel('Layer + Reduction', fontsize=14)  # Explicit y-axis label
    plt.tight_layout(pad=3)  # Adjust layout to not cut off labels

    # default name for saving same as title
    plt.savefig(f"./results/{data_type}_{task_type}_{method_type}_heatmap.png")
    # print(f"Heatmap '{main_title}' saved")
    # plt.show()

    # Optionally, save the table to a CSV file
    output_csv = os.path.join(
        f"./results/csv/{data_type}_{task_type}_{method_type}_metrics_summary.csv")
    df.to_csv(output_csv, index=False)
    # print(f"Summary table saved to {output_csv}")


def main():
    use_cache = False
    hostname = 'euler.ethz.ch'

    ssh_details = [
        {'username': 'estamkopoulo', 'key_path': '/Users/vaggelis/Projects/Config/.ssh/id_rsa_euler',
            'base_folder': '/cluster/scratch/estamkopoulo/fine_tuning/'},
        {'username': 'tbikias', 'key_path': '/Users/vaggelis/Projects/Config/.ssh/id_rsa_euler_thomas',
            'base_folder': '/cluster/scratch/tbikias/plmfit/fine_tuning/'}
    ]

    parameter_sets = [
        {'method_type': 'feature_extraction', 'data_type': 'meltome',
         'split': 'mixed', 'use_mlp': True, 'task_type': 'regression'},
        {'method_type': 'feature_extraction', 'data_type': 'aav',
         'split': 'one_vs_many', 'use_mlp': True, 'task_type': 'regression'},
        {'method_type': 'feature_extraction', 'data_type': 'aav',
         'split': 'sampled', 'use_mlp': True, 'task_type': 'regression'},
        {'method_type': 'feature_extraction', 'data_type': 'gb1',
         'split': 'one_vs_rest', 'use_mlp': True, 'task_type': 'regression'},
        {'method_type': 'feature_extraction', 'data_type': 'gb1',
         'split': 'three_vs_rest', 'use_mlp': True, 'task_type': 'regression'},
        {'method_type': 'feature_extraction', 'data_type': 'herH3',
         'split': 'one_vs_rest', 'use_mlp': True, 'task_type': 'classification'},
        {'method_type': 'feature_extraction', 'data_type': 'rbd',
         'split': 'one_vs_rest', 'use_mlp': True, 'task_type': 'classification'},
        {'method_type': 'lora_all', 'data_type': 'meltome',
            'split': 'mixed', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'lora_last', 'data_type': 'meltome',
            'split': 'mixed', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'bottleneck_adapters_all',
            'data_type': 'meltome', 'split': 'mixed', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'bottleneck_adapters_last',
            'data_type': 'meltome', 'split': 'mixed', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'lora_all', 'data_type': 'aav',
            'split': 'one_vs_many', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'lora_last', 'data_type': 'aav',
            'split': 'one_vs_many', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'bottleneck_adapters_all',
            'data_type': 'aav', 'split': 'one_vs_many', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'bottleneck_adapters_last',
            'data_type': 'aav', 'split': 'one_vs_many', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'lora_all', 'data_type': 'aav',
            'split': 'sampled', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'lora_last', 'data_type': 'aav',
            'split': 'sampled', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'bottleneck_adapters_all',
            'data_type': 'aav', 'split': 'sampled', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'bottleneck_adapters_last',
            'data_type': 'aav', 'split': 'sampled', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'lora_all',
            'data_type': 'gb1', 'split': 'one_vs_rest', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'lora_last',
            'data_type': 'gb1', 'split': 'one_vs_rest', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'bottleneck_adapters_all',
            'data_type': 'gb1', 'split': 'one_vs_rest', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'bottleneck_adapters_last',
            'data_type': 'gb1', 'split': 'one_vs_rest', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'lora_all',
            'data_type': 'gb1', 'split': 'three_vs_rest', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'lora_last',
            'data_type': 'gb1', 'split': 'three_vs_rest', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'bottleneck_adapters_all',
            'data_type': 'gb1', 'split': 'three_vs_rest', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'bottleneck_adapters_last',
            'data_type': 'gb1', 'split': 'three_vs_rest', 'use_mlp': False, 'task_type': 'regression'},
        {'method_type': 'lora_all',
            'data_type': 'herH3', 'split': 'one_vs_rest', 'use_mlp': False, 'task_type': 'classification'},
        {'method_type': 'lora_last',
            'data_type': 'herH3', 'split': 'one_vs_rest', 'use_mlp': False, 'task_type': 'classification'},
        {'method_type': 'bottleneck_adapters_all',
            'data_type': 'herH3', 'split': 'one_vs_rest', 'use_mlp': False, 'task_type': 'classification'},
        {'method_type': 'bottleneck_adapters_last',
            'data_type': 'herH3', 'split': 'one_vs_rest', 'use_mlp': False, 'task_type': 'classification'},
        {'method_type': 'lora_all',
            'data_type': 'rbd', 'split': 'one_vs_rest', 'use_mlp': False, 'task_type': 'classification'},
        {'method_type': 'lora_last',
            'data_type': 'rbd', 'split': 'one_vs_rest', 'use_mlp': False, 'task_type': 'classification'},
        {'method_type': 'bottleneck_adapters_all',
            'data_type': 'rbd', 'split': 'one_vs_rest', 'use_mlp': False, 'task_type': 'classification'},
        {'method_type': 'bottleneck_adapters_last',
            'data_type': 'rbd', 'split': 'one_vs_rest', 'use_mlp': False, 'task_type': 'classification'}
    ]

    for details in ssh_details:
        details['ssh'], details['sftp'] = establish_ssh_sftp_sessions(
            hostname, details['username'], key_path=details['key_path'])

    for params in tqdm(parameter_sets, desc="Processing parameter sets"):
        method_type = params['method_type']
        data_type = params['data_type']
        split = params['split']
        use_mlp = params['use_mlp']
        task_type = params['task_type']

        if use_cache:
            collect_metrics(csv_file=f"{data_type}_{task_type}_{method_type}_metrics_summary.csv",
                            data_type=data_type, task_type=task_type)
            continue

        with tempfile.TemporaryDirectory() as temp_dir:
            all_json_files = []
            for details in ssh_details:
                path = f'{details["base_folder"]}{method_type}'

                json_files = find_and_download_json_files(
                    details['ssh'], details['sftp'], path, data_type+'_'+split, task_type, temp_dir)
                all_json_files.extend(json_files)

                
            collect_metrics(json_files=all_json_files, data_type=data_type+'_'+split,
                            task_type=task_type, method_type=method_type, use_mlp=use_mlp)

    for details in ssh_details:
        details['sftp'].close()
        details['ssh'].close()

if __name__ == "__main__":
    main()
