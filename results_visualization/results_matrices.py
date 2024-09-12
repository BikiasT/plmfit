
index_tl_techniqes = {0:'FE', 1: 'LoRA', 2:'LoRA-', 3:'Adapters' , 4:'Adapters-'}
index_layers = {0:0, 1: 25, 2:50, 3:75 , 4:100}


aav_sampled_dict = {
    'ohe_baseline':0.864,
    'feature_extraction': {
        'ProteinBERT': [0.748, 0.811, 0.815, 0.819, 0.788],
        'ProGen2-small': [0.595, 0.833, 0.779, 0.817, 0.771],
        'ProGen2-medium': [0.557, 0.839, 0.823, 0.835, 0.667],
        'ProGen2-xlarge': [0.59, 0.85, 0.843, 0.85, 0.636],
        'ESM-650M':[0.52,0.82,0.64,0.65,0.62],
        'ESM-3B':[0.55,0.84,0.76,0.69,0.66],
        'ESM-15B':[0.65,0.88,0.86,0.8,0.84]
        },
    'lora': {
      'ProteinBERT': [0.729, 0.879, 0.775, 0.893, 0.811],
      'ProGen2-small': [0.526, 0.86, 0.835, 0.895, 0.845],
      'ProGen2-medium': [0.757, 0.88, 0.899, 0.891, 0.899],
      'ProGen2-xlarge': [0.471, 0.917, 0.92, 0.926, 0.916],
        'ESM-650M':[0.635,0.910,0.907,0.901,0.917],
        'ESM-3B':[0.626,0.907,0.908,0.911,0],
        'ESM-15B':[0.826,0,0,0,0]
        },
    'adapters': {
        'ProteinBERT': [0.866, 0.896, 0.903, 0.907, 0.907],
        'ProGen2-small': [0.595, 0.576, 0.736, 0.686, 0.865],
        'ProGen2-medium': [0.609, 0.606, 0.64, 0.663, 0.826],
        'ProGen2-xlarge': [0.615, 0.923, 0.926, 0.928, 0.916],
        'ESM-650M':[0.470,0.913,0.900,0.904,0.913],
        'ESM-3B':[0.318,0.913,0.912,0.906,0.917],
        'ESM-15B':[0.498,0,0,0,0]
        },
    'best_models': {
        'ProteinBERT': [0.819, 0.893, 0.898, 0.907, 0.895],
        'ProGen2-small': [0.833, 0.895, 0.889, 0.865, 0.909],
        'ProGen2-medium': [0.839, 0.899, 0.890, 0.826, 0.905],
        'ProGen2-xlarge': [0.851, 0.926, 0.897, 0.928, 0.902],
        'ESM-650M':[0.82,0.917,0,0.913,0],
        'ESM-3B':[0.84,0.911,0,0.917,0],
        'ESM-15B':[0.88,0.826,0,0.498,0]
        }
}


aav_one_vs_rest_dict = {
    'ohe_baseline': 0.565,
    'feature_extraction': {
        'ProteinBERT': [0.313, 0.288, 0.378, 0.359, 0.392],
        'ProGen2-small': [0.289, 0.271, 0.38, 0.322, 0.33],
        'ProGen2-medium': [0.308, 0.315, 0.265, 0.415, 0.183],
        'ProGen2-xlarge': [0.347, 0.201, 0.231, 0.215, 0.267]
    },
    'lora': {
        'ProteinBERT': [0.545, 0.548, 0.675, 0.726, 0.797],
        'ProGen2-small': [0.375, 0.702, 0.751, 0.787, 0.818],
        'ProGen2-medium': [0.347, 0.773, 0.793, 0.76, 0.643],
        'ProGen2-xlarge': [0.284, 0.775, 0.736, 0.831, 0.783]
    },
    'adapters': {
        'ProteinBERT': [0.554, 0.531, 0.69, 0.757, 0.795],
        'ProGen2-small': [0.265, 0.657, 0.69, 0.784, 0.827],
        'ProGen2-medium': [0.283, 0.809, 0.818, 0.799, 0.79],
        'ProGen2-xlarge': [0.232, 0.796, 0.793, 0.825, 0.794]
    },
    'best_models': {
       'ProteinBERT': [0.392, 0.797, 0.640, 0.795, 0.652],
       'ProGen2-small': [0.380, 0.818, 0.727, 0.827, 0.751],
       'ProGen2-medium': [0.415, 0.793, 0.770, 0.818, 0.721],
       'ProGen2-xlarge': [0.347, 0.831, 0.749, 0.825, 0.757]
   }
}

gb1_three_vs_rest_dict = {
    'ohe_baseline': 0.838,
    'feature_extraction': {
        'ProteinBERT': [0.637, 0.64, 0.72, 0.703, 0.646],
        'ProGen2-small': [0.555, 0.672, 0.762, 0.701, 0.555],
        'ProGen2-medium': [0.547, 0.757, 0.751, 0.734, 0.487],
        'ProGen2-xlarge': [0.242, 0.759, 0.792, 0.751, 0.378],
        'ESM-650M':[0.549535522,0.797767354,0.743038555	,0.696164185,	0.767890405],
        'ESM-3B':[0.50574511,	0.790685326,	0.772713223,	0.694206017,	0.718571312],
        'ESM-15B':[0.512260364,	0.804470966,	0.782850202,	0.770702695,	0.769497189]
    },
    'lora': {
        'ProteinBERT': [0.806, 0.839, 0.862, 0.862, 0.857],
        'ProGen2-small': [0.422, 0.79, 0.871, 0.855, 0.862],
        'ProGen2-medium': [0.407, 0.865, 0.866, 0.874, 0.87],
        'ProGen2-xlarge': [0.412, 0.871, 0.874, 0.871, 0.877],
        'ESM-650M':[0.737700641,	0.873421311,	0.868119359,	0.870582104,	0.864818752],
        'ESM-3B':[0.684197664,	0.872933745,	0.873821318,	0.874630094,	0.873257399],
        'ESM-15B':[0.758637786,	0.865879476	,0.877082169,	0.864358246,	0.876690328]
    },
    'adapters': {
        'ProteinBERT': [0.771, 0.846, 0.847, 0.86, 0.872],
        'ProGen2-small': [0.467, 0.82, 0.868, 0.87, 0.866],
        'ProGen2-medium': [0.497, 0.857, 0.879, 0.878, 0.864],
        'ProGen2-xlarge': [0.192, 0.875, 0.874, 0.865, 0.868],
        'ESM-650M':[0.506489933,	0.871071875,	0.867695332	,0.859199047	,0.863181114],
        'ESM-3B':[0.135820985	,0.870723546	,0.859747708	,0.862793565	,0.860208035],
        'ESM-15B':[0.44622311,	0.872413158	,0.873741448	,0.867499888,	0]
    },
    'best_models': {
         'ProteinBERT': [0.720, 0.862, 0.823, 0.872, 0.810],
         'ProGen2-small': [0.762, 0.871, 0.800, 0.870, 0.825],
         'ProGen2-medium': [0.757, 0.874, 0.817, 0.879, 0.838],
         'ProGen2-xlarge': [0.792, 0.877, 0.843, 0.875, 0.862],
         'ESM-650M':[0.7977,0.87,0,0.871,0],
         'ESM-3B':[0.790,0.874,0,0.87,0],
         'ESM-15B':[0.804,0.87,0,0.87,0]
 }
}

gb1_one_vs_rest_dict = {
    'ohe_baseline': 0.332,
    'feature_extraction': {
        'ProteinBERT': [0.297, 0.251, 0.229, 0.065, 0.346],
        'ProGen2-small': [0.222, 0.288, 0.388, 0.457, 0.241],
        'ProGen2-medium': [0.204, 0.313, 0.438, 0.208, 0.169],
        'ProGen2-xlarge': [0.254, 0.236, 0.276, 0.366, 0.407]
    },
    'lora': {
        'ProteinBERT': [0.178, 0.302, 0.296, 0.281, 0.044],
        'ProGen2-small': [0.067, 0.291, 0.12, 0.271, 0.359],
        'ProGen2-medium': [0.1, 0.291, 0.347, 0.309, 0.159],
        'ProGen2-xlarge': [0.337, 0.077, 0.279, 0.215, 0.322]
    },
    'adapters': {
        'ProteinBERT': [0.206, 0.303, 0.303, 0.283, 0.336],
        'ProGen2-small': [0.084, 0.287, 0.31, 0.381, 0.254],
        'ProGen2-medium': [0.184, 0.332, 0.396, 0.416, 0.272],
        'ProGen2-xlarge': [0.214, 0.119, 0.235, 0.311, 0.207]
    },
    'best_models': {
        'ProteinBERT': [0.346, 0.302, 0.304, 0.336, 0.239],
        'ProGen2-small': [0.457, 0.359, 0.348, 0.381, 0.306],
        'ProGen2-medium': [0.438, 0.347, 0.340, 0.416, 0.322],
        'ProGen2-xlarge': [0.276, 0.322, 0.431, 0.311, 0.300]
    }
}

meltome_mixed_dict = {
    'ohe_baseline': 0.332,
    'feature_extraction': {
        'ProteinBERT': [0.535, 0.524, 0.499, 0.507, 0.561],
        'ProGen2-small': [0.544, 0.56, 0.515, 0.501, 0.476],
        'ProGen2-medium': [0.473, 0.508, 0.529, 0.532, 0.499],
        'ProGen2-xlarge': [0.409, 0.569, 0.497, 0.544, 0.542],
        'ESM-650M':[0.507095923	,0.503846241	,0.512877256,	0.45557736,	0.524944586],
        'ESM-3B':[0.401708236,	0.466586642	,0.37442453	,0.407598532	,0.454094942],
        'ESM-15B':[0.454526745	,0.587892292,	0.560003542	,0.54897314,	0.671378331]
        
    },
    'lora': {
        'ProteinBERT': [0.341, 0.505, 0.536, 0.545, 0.556],
        'ProGen2-small': [0.376, 0.504, 0.574, 0.555, 0.571],
        'ProGen2-medium': [0.38, 0.567, 0.582, 0.581, 0.649],
        'ProGen2-xlarge': [0.376, 0.538, 0.593, 0.578, 0.723],
        'ESM-650M':[0.398111463	,0.560635805	,0.565366149,	0.581270814	,0.531969428],
        'ESM-3B':[0.327240229,	0.547375917	,0.464524627,	0.510675073	,0.511676133],
        'ESM-15B':[0.421247423,	0.58646208,	0.554667473,	0.612445176	,0.585783541]
    },
    'adapters': {
        'ProteinBERT': [0.496, 0.557, 0.557, 0.55, 0.57],
        'ProGen2-small': [0.338, 0.546, 0.56, 0.575, 0.572],
        'ProGen2-medium': [0.324, 0.572, 0.572, 0.582, 0.583],
        'ProGen2-xlarge': [0.324, 0.566, 0.579, 0.61, 0.709],
        'ESM-650M':[0.445205659	,0.482391566,	0.543717921	,0.526174128	,0.531419456],
        'ESM-3B':[0.330693394	,0.477570474,	0.477629423	,0.509340227,	0.533092856],
        'ESM-15B':[0.403330564,	0.555931449,	0.36227867	,0.676321089	,0.374235839]
    },
    'best_models': {
        'ProteinBERT': [0.561, 0.556, 0.501, 0.570, 0.564],
        'ProGen2-small': [0.560, 0.574, 0.556, 0.575, 0.531],
        'ProGen2-medium': [0.532, 0.649, 0.626, 0.583, 0.537],
        'ProGen2-xlarge': [0.569, 0.723, 0.699, 0.709, 0.544],
        'ESM-650M':[	0.524,0.581,0,0.543,0],
        'ESM-3B':[0.466,0.547,00.533,0],
        'ESM-15B':[0.67,0.612,0,0.67,0]
    }
}

########################################
ed_gb1_one_vs_rest = {
    'OHE - baseline': [0.18413462, 0.202962204, 0.299111309],
    'FE_model': 'progen2-small-q3',
    'FE': [0.335841581 , 0.330046208, 0.516648351],
    'LoRA_model': 'progen2-small-last',
    'LoRA': [0.508770187, 0.437840674, 0.312169006],
    'Adapters_model': 'progen2-medium-q3',
    'Adapters': [0.521519613, 0.434268972, 0.388192353]
    }

ed_aav_one_vs_rest = {
    'OHE - baseline': [0.601093051, 0.344148591, 0.310738778, 0.263013395, 0.188849701, 
    0.122343869, 0.013268832, -0.022199887, 0.001200543, -0.033007621, 
    -0.046922107, -0.07906464, -0.03171529, -0.01190838, -0.049467017, 
    -0.030629318, 0.01536307, 0.043101789, 0.145105377],
    'FE_model': 'esm2_t48_15B_UR50D-q1',
    'FE': [0.747891502, 0.400801882, 0.379987215, 0.399312278, 0.400844128, 
    0.318601802, 0.265679277, 0.243531762, 0.292168908, 0.244071223, 
    0.218738855, 0.160707214, 0.20071582, 0.146152746, 0.13354582, 
    0.162897136, 0.085629723, 0.066571961, 0.046119245],
    'LoRA_model': 'progen2-small-last',
    'LoRA': [ 0.810051173, 0.509956459, 0.493760068, 0.530513423, 0.547706449, 
    0.487471309, 0.514504082, 0.527881628, 0.531360262, 0.503867326, 
    0.467478082, 0.444469991, 0.453298654, 0.421502609, 0.395274724, 
    0.358488709, 0.308145123, 0.230980105, 0.144978051],
    'Adapters_model': 'progen2-small-last',
    'Adapters': [0.832026404, 0.54751714, 0.521120068, 0.550459082, 0.549405517, 
    0.486584612, 0.505472591, 0.529598584, 0.528387572, 0.503102591, 
    0.520164924, 0.491715041, 0.501476712, 0.472427644, 0.426019176, 
    0.380142232, 0.361388909, 0.247127467, 0.217342471]
    }
ed_rbd_one_vs_rest = {
    'OHE - baseline': [0,0,0,0,0,0],
    'FE_model': 'progen2-xlarge-q3',
    'FE':  [0.31609858, 0.385604982, 0.31859601, 0.073075695, 0.007789612, 
    -0.014323591],
    'LoRA_model': 'progen2-small-middle',
    'LoRA':[0.449701986, 0.564744099, 0.464587883, 0.207658667, 0.083952509, 
    0.014981519],
    'Adapters_model': 'esm2_t33_650M_UR50D-q1',
    'Adapters': [ 0.42621114, 0.523799718, 0.381435132, 0.177772357, 0.065316119, 
    -0.012853043]
    }
ed_herh3_one_vs_rest = {
    'OHE - baseline':  [ 0, 0.025854384, 0.083068824, 0.164217059, 0.151246495, 
    0.119362872, 0.085986821, 0.053091445, 0.068200408],
    'FE_model': 'esm2_t48_15B_UR50D-q1',
    'FE': [ 0.166666667, 0.080412542, 0.120863656, 0.157128448, 0.163252139, 
    0.170236073, 0.1311125, 0.089742261, 0.118852237],
    'LoRA_model': 'progen2-xlarge-last',
    'LoRA': [1, 0.339463828, 0.046339554, 0.174141541, 0.187980097, 
    0.21734682, 0.196675995, 0.088664178, 0.019492541],
    'Adapters_model': 'progen2-medium-q3',
    'Adapters': [ 0.471404521, 0.372877236, 0.159377216, 0.230770001, 0.218789368, 
    0.207673668, 0.153415425, 0.045753268, -0.016424573]
    }
