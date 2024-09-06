import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats, interpolate
from sklearn.metrics import matthews_corrcoef


def calc_mcc(group, pred_col):
    mcc = matthews_corrcoef(group['binary_score'], group[pred_col])
    return pd.Series({'MCC': mcc})


# Load the JSON files
with open('./results_visualization/rbd_one_vs_rest_progen2-small_lora_middle_mean_linear_classification_metrics.json', 'r') as file:
    lora_data = json.load(file)

with open('./results_visualization/rbd_one_vs_rest_esm2_t33_650M_UR50D_bottleneck_adapters_quarter1_bos_linear_classification_metrics.json', 'r') as file:
    ada_data = json.load(file)

with open('./results_visualization/rbd_one_vs_rest_progen2-small_feature_extraction_middle_mean_linear_classification_data.json', 'r') as file:
    fe_data = json.load(file)

# with open('./results_visualization/aav_one_vs_many_mlp_regression_pred_vs_true.json', 'r') as file:
#     ohe_data = json.load(file)

# Extract the 'pred' array
lora_pred_scores = lora_data['pred_data']['preds']
ada_pred_scores = ada_data['pred_data']['preds']
fe_pred_scores = fe_data['metrics']['testing_data']['y_pred']
# ohe_pred_scores = ohe_data['y_pred']

# Load the dataset
dataset = pd.read_csv('./plmfit/data/rbd/rbd_data_full.csv')

# Filter the dataset for the test split
test_data = dataset[dataset['one_vs_rest'] == 'test']

test_data['lora_pred_score'] = np.round(np.array(lora_pred_scores))
test_data['ada_pred_score'] = np.round(np.array(ada_pred_scores))
test_data['fe_pred_score'] = np.round(np.array(fe_pred_scores))
# test_data['ohe_pred_score'] = ohe_pred_scores

# Ensure 'no_mut' is in numerical form and label everything over 20 as 20+
test_data['no_mut'] = test_data['no_mut'].astype(float)
# test_data['no_mut'] = test_data['no_mut'].apply(lambda x: 20 if x > 20 else x)

# cols_to_keep = ['no_mut', 'binary_score', 'lora_pred_score', 'ada_pred_score', 'fe_pred_score', 'ohe_pred_score']
cols_to_keep = ['no_mut', 'binary_score', 'lora_pred_score', 'ada_pred_score', 'fe_pred_score']
test_data = test_data[cols_to_keep]

# Calculate Spearman correlations for each edit distance group
correlations_lora = test_data.groupby('no_mut').apply(calc_mcc, 'lora_pred_score')
correlations_ada = test_data.groupby('no_mut').apply(calc_mcc, 'ada_pred_score')
correlations_fe = test_data.groupby('no_mut').apply(calc_mcc, 'fe_pred_score')
# correlations_ohe = test_data.groupby('no_mut').apply(calc_spearman, 'ohe_pred_score')

# Interpolate for smoothing
def interpolate_smooth(x, y, kind='cubic', num=500):
    x_smooth = np.linspace(x.min(), x.max(), num)
    y_smooth = interpolate.interp1d(x, y, kind=kind)(x_smooth)
    return x_smooth, y_smooth

# Plotting
fig, axs = plt.subplots(2, 1, figsize=(10, 10))

def plot_with_fill(ax, x, y, label, color, alpha=0.05):
    x_smooth, y_smooth = interpolate_smooth(x, y)
    _, y_lower = interpolate_smooth(x, y)
    _, y_upper = interpolate_smooth(x, y)
    ax.plot(x, y, label=label, color=color, marker='o')
    ax.fill_between(x_smooth, y_lower, y_upper, color=color, alpha=alpha)

plot_with_fill(axs[0], correlations_lora.index, correlations_lora['MCC'], 'LoRA', 'blue')
plot_with_fill(axs[0], correlations_ada.index, correlations_ada['MCC'], 'Ada', 'orange')
plot_with_fill(axs[0], correlations_fe.index, correlations_fe['MCC'], 'FE', 'green')
# plot_with_fill(axs[0], correlations_ohe.index, correlations_ohe['Correlation'], correlations_ohe['P-value'], 'OHE', 'red')

axs[0].set_xlabel('Edit Distance')
axs[0].set_ylabel("MCC")
axs[0].set_title("MCC by Edit Distance")
str_month_list = ['2','4','6','8']
axs[0].set_xticks([2, 4, 6, 8])
axs[0].set_xticklabels(str_month_list)
axs[0].legend()

# Subplot for counts
counts = test_data['no_mut'].value_counts().sort_index()
bars = axs[1].bar(counts.index, counts.values, label='Count')

# Add counts above the bars
for bar in bars:
    height = bar.get_height()
    axs[1].text(bar.get_x() + bar.get_width() / 2, height, '%d' % int(height), ha='center', va='bottom', fontsize=8)

axs[1].set_xlabel('Edit Distance')
axs[1].set_ylabel('Count')
axs[1].set_title('Number of Entries by Edit Distance')
axs[1].legend()
str_month_list = ['2', '4', '6', '8']
axs[1].set_xticks([2, 4, 6, 8])
axs[1].set_xticklabels(str_month_list)

plt.tight_layout()
plt.show()