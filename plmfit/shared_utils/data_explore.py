import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import plmfit.shared_utils.utils as utils
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA
import torch

def plot_label_distribution(data, label="binary_score", path=None, text="Keep"):
    sns.set(style="whitegrid")
    plt.figure(figsize=(10, 6))
    ax = sns.countplot(x=label, data=data, hue=label, palette=["coral", "skyblue"])
    plt.title('Label Distribution', fontsize=16)
    plt.xlabel(text + ' Label', fontsize=14)
    plt.ylabel('Count', fontsize=14)
    plt.xticks(rotation=45, fontsize=12)

    # Annotate each bar with the count value
    for p in ax.patches:
        ax.annotate(f'{int(p.get_height())}', (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', fontsize=12, color='black', xytext=(0, 5),
                    textcoords='offset points')
    plt.tight_layout()
    if path is not None:
        plt.savefig(path, format='png')
    else:
        plt.ion()
        plt.show()



def plot_score_distribution(data, column="score", text="Fitness Score", log_scale=False, path=None):
    sns.set(style="whitegrid")
    plt.figure(figsize=(10, 6))
    sns.histplot(data[column], bins=1000, kde=True, log_scale=(False, log_scale))
    plt.title(text + ' Distribution', fontsize=16)
    plt.xlabel(text, fontsize=14)
    y_label = 'Frequency (Log Scale)' if log_scale else 'Frequency'
    plt.ylabel(y_label, fontsize=14)
    plt.grid(True, which="both", ls="--", linewidth=0.5)
    plt.tight_layout()
    if path is not None:
        plt.savefig(path, format='png')
    else:
        plt.ion()
        plt.show()

def normalized_score(data, column="score"):
    # Calculate the minimum and maximum values of the score column
    min_score = data[column].min()
    max_score = data[column].max()

    # Apply Min-Max Normalization
    return (data[column] - min_score) / (max_score - min_score)

def plot_normalized_score_distribution(data, column="normalized_score", text="Fitness Score", log_scale=False, path=None):
    sns.set(style="whitegrid")
    plt.figure(figsize=(10, 6))
    sns.histplot(data[column], bins=1000, kde=True, log_scale=(False, log_scale))
    plt.title('Normalized ' + text + ' Distribution', fontsize=16)
    plt.xlabel('Normalized ' + text, fontsize=14)
    # Set the y-axis label based on whether log scale is used
    y_label = 'Frequency (Log Scale)' if log_scale else 'Frequency'
    plt.ylabel(y_label, fontsize=14)
    plt.grid(True, which="both", ls="--", linewidth=0.5)
    plt.tight_layout()
    if path is not None:
        plt.savefig(path, format='png')
    else:
        plt.ion()
        plt.show()


def plot_sequence_length_distribution(data, path=None):
    sns.set(style="whitegrid")
    plt.figure(figsize=(10, 6))
    ax = sns.histplot(data['sequence_length'], discrete=True)
    plt.title('Sequence Length Distribution', fontsize=16)
    plt.xlabel('Length (Number of Amino Acids)', fontsize=14)
    plt.ylabel('Frequency', fontsize=14)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    plt.tight_layout()
    if path is not None:
        plt.savefig(path, format='png')
    else: 
        plt.ion()
        plt.show()


def plot_mutations_number(data, column='number_of_mutations', annotation=False, path=None):
    sns.set(style="whitegrid")
    plt.figure(figsize=(10, 6))
    ax = sns.histplot(data[column], color='mediumpurple')
    plt.title('Distribution of Mutation Count', fontsize=16)
    plt.xlabel('Number of Mutations', fontsize=14)
    plt.ylabel('Frequency', fontsize=14)
    plt.grid(True, which="both", ls="--", linewidth=0.5)

    if annotation:
        for p in ax.patches:
            if int(p.get_height()) > 0:
                ax.annotate(f'{int(p.get_height())}', (p.get_x() + p.get_width() / 2., p.get_height()),
                            ha='center', va='center', fontsize=12, color='black', xytext=(0, 5),
                            textcoords='offset points')
    plt.tight_layout()
    if path is not None:
        plt.savefig(path, format='png')
    else:
        plt.ion()
        plt.show()



def parse_fasta(fasta_file, log=False):
    with open(fasta_file, 'r') as file:
        sequence_id = ''
        sequence = ''
        for line in file:
            if line.startswith('>'):
                sequence_id = line[1:].strip()  # Removes the '>' and any trailing newline characters
            else:
                sequence += line.strip()  # Adds the sequence line, removing any trailing newlines
        if log:
            print("Sequence ID:", sequence_id)
            print("Sequence:", sequence)
        return sequence_id, sequence
    
def plot_mutations_heatmap(mutation_counts, zoom_region=None, path=None):
    sns.set(style="white")
    mutation_df = pd.DataFrame(mutation_counts)
    fig = plt.figure() 
    fig, (ax_main, ax_zoom) = plt.subplots(1, 2, figsize=(20, 10), gridspec_kw={'width_ratios': [3, 1]})
    sns.heatmap(np.transpose(mutation_df), cmap='viridis', cbar=True, ax=ax_main)
    ax_main.set_title('Mutation Heatmap per Amino Acid and Position', fontsize=16)
    ax_main.set_xlabel('Position in Sequence', fontsize=14)
    ax_main.set_ylabel('Amino Acids', fontsize=14)

    if zoom_region is not None:
        start, end = zoom_region
        sns.heatmap(np.transpose(mutation_df.iloc[start:end, :]), ax=ax_zoom, cmap='viridis', cbar=True)
        ax_zoom.set_title(f'Zoomed Region: Positions {start} to {end}', fontsize=16)
        ax_zoom.set_xlabel('Position in Sequence', fontsize=14)
        ax_zoom.set_ylabel('Amino Acids', fontsize=14)
    else:
        ax_zoom.axis('off')

    plt.tight_layout()
    if path is not None:
        plt.savefig(path, format='png')
    else:
        plt.ion()
        plt.show()

def PCA_2d(data_type, model, layers, reduction, output_path='default', labels_col='score', labeling='continuous'):
    if output_path == 'default':
        output_path = f'./plmfit/data/{data_type}/embeddings/plots'
    else:
        output_path = output_path
    
    data = utils.load_dataset(data_type)

    if labeling=='discrete':
        # Mapping species to colors for the filtered dataset
        labels_unique = data[labels_col].unique()
        labels_to_int = {labels: i for i, labels in enumerate(labels_unique)}
        labels_colors = data[labels_col].map(labels_to_int).values

        # Generate a discrete colormap
        num_labels = len(labels_unique)
        c = labels_colors
        cmap = plt.get_cmap('tab20', num_labels)  # Using 'tab20' colormap
    else:
        scores = data[labels_col].values
        scaler = MinMaxScaler()
        scores_scaled = scaler.fit_transform(scores.reshape(-1, 1)).flatten()
        c = scores_scaled
        cmap='viridis'

    for layer in layers:
        # Load embeddings
        file_path = f'./plmfit/data/{data_type}/embeddings/{data_type}_{model}_embs_layer{layer}_{reduction}.pt'
        embeddings = torch.load(file_path, map_location=torch.device('cpu'))
        embeddings = embeddings.numpy() if embeddings.is_cuda else embeddings

        # Perform PCA
        pca = PCA(n_components=2)
        reduced_embeddings = pca.fit_transform(embeddings)

        # Plot
        plt.figure(figsize=(10, 10))
        scatter = plt.scatter(
            reduced_embeddings[:, 0], reduced_embeddings[:, 1], c=c, cmap=cmap)
        plt.title(
            f"2D PCA of {data_type} Embeddings\n{labels_col} coloring - Layer {layer} - {reduction} - {model}")
        plt.xlabel("Principal Component 1")
        plt.ylabel("Principal Component 2")

        if labeling == 'continuous':
            plt.colorbar(scatter, label=f'{labels_col}')
        else:
            # Create a color bar with tick marks and labels for each species
            cbar = plt.colorbar(scatter, ticks=range(num_labels))
            cbar.set_ticklabels(labels_unique)
            cbar.set_label(f'{labels_col}')

        # Save the figure to a file
        plt.savefig(
            f'{output_path}/PCA_{data_type}_{model}_Layer-{layer}_{reduction}.png', bbox_inches='tight')

        plt.close()

