import dask_cudf
from dask import array as da
from dask import dataframe as dd
from dask.distributed import Client
from dask_cuda import LocalCUDACluster

import xgboost as xgb
from xgboost import dask as dxgb
from xgboost.dask import DaskDMatrix

from sklearn.metrics import classification_report
import pickle
import time
import os
import sys
import numpy as np
from data_and_loading_functions import create_directory

import matplotlib.pyplot as plt

from guppy import hpy
##################################################################################################################
# LOAD CONFIG PARAMETERS
import configparser
config = configparser.ConfigParser()
config.read("config.ini")
curr_sparta_file = config["MISC"]["curr_sparta_file"]
path_to_MLOIS = config["PATHS"]["path_to_MLOIS"]
path_to_snaps = config["PATHS"]["path_to_snaps"]
path_to_SPARTA_data = config["PATHS"]["path_to_SPARTA_data"]
path_to_hdf5_file = path_to_SPARTA_data + curr_sparta_file + ".hdf5"
path_to_pickle = config["PATHS"]["path_to_pickle"]
path_to_calc_info = config["PATHS"]["path_to_calc_info"]
path_to_pygadgetreader = config["PATHS"]["path_to_pygadgetreader"]
path_to_sparta = config["PATHS"]["path_to_sparta"]
path_to_xgboost = config["PATHS"]["path_to_xgboost"]
create_directory(path_to_MLOIS)
create_directory(path_to_snaps)
create_directory(path_to_SPARTA_data)
create_directory(path_to_hdf5_file)
create_directory(path_to_pickle)
create_directory(path_to_calc_info)
create_directory(path_to_xgboost)
snap_format = config["MISC"]["snap_format"]
global prim_only
prim_only = config.getboolean("SEARCH","prim_only")
t_dyn_step = config.getfloat("SEARCH","t_dyn_step")
global p_snap
p_snap = config.getint("SEARCH","p_snap")
c_snap = config.getint("XGBOOST","c_snap")
model_name = config["XGBOOST"]["model_name"]
radii_splits = config.get("XGBOOST","rad_splits").split(',')
for split in radii_splits:
    model_name = model_name + "_" + str(split)

snapshot_list = [p_snap, c_snap]
global search_rad
search_rad = config.getfloat("SEARCH","search_rad")
total_num_snaps = config.getint("SEARCH","total_num_snaps")
per_n_halo_per_split = config.getfloat("SEARCH","per_n_halo_per_split")
test_halos_ratio = config.getfloat("SEARCH","test_halos_ratio")
curr_chunk_size = config.getint("SEARCH","chunk_size")
global num_save_ptl_params
num_save_ptl_params = config.getint("SEARCH","num_save_ptl_params")

# size float32 is 4 bytes
chunk_size = int(np.floor(1e9 / (num_save_ptl_params * 4)))
###############################################################################################################

def sizeof_fmt(num, suffix='B'):
    ''' by Fred Cirera,  https://stackoverflow.com/a/1094933/1870254, modified'''
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Yi', suffix)


def get_cluster():
    cluster = LocalCUDACluster(
                               device_memory_limit='10GB',

                               jit_unspill=True)

    client = Client(cluster)

    return client

def create_training_matrix(X_loc, y_loc, frac_use_data = 1, calc_scale_pos_weight = False):
    with open(X_loc, "rb") as file:
        X = pickle.load(file) 
    with open(y_loc, "rb") as file:
        y = pickle.load(file)
    
    scale_pos_weight = np.where(y == 0)[0].size / np.where(y == 1)[0].size
    
    num_features = X.shape[1]
    
    num_use_data = int(np.floor(X.shape[0] * frac_use_data))
    print("Tot num of train particles:", X.shape[0])
    print("Num use train particles:", num_use_data)

    print(X[:,0].dtype)
    print(X[:,1].dtype)
    print(X[:,2].dtype)
    X = da.from_array(X,chunks=(chunk_size,num_features))
    y = da.from_array(y,chunks=(chunk_size))
    print("converted to array")
        
    print("X Number of total bytes:", X.nbytes, "X Number of Gigabytes:", (X.nbytes)/(10**9))
    print("y Number of total bytes:", y.nbytes, "y Number of Gigabytes:", (y.nbytes)/(10**9))
    
    dqmatrix = xgb.dask.DaskQuantileDMatrix(client, X, y)
    print("converted to DaskQuantileDMatrix")
    
    if calc_scale_pos_weight:
        return dqmatrix, scale_pos_weight
    return dqmatrix


if __name__ == "__main__":
    client = get_cluster()
    if len(snapshot_list) > 1:
        specific_save = curr_sparta_file + "_" + str(snapshot_list[0]) + "to" + str(snapshot_list[-1]) + "_" + str(search_rad) + "r200msearch/"
    else:
        specific_save = curr_sparta_file + "_" + str(snapshot_list[0]) + "_" + str(search_rad) + "r200msearch/"

    save_location = path_to_xgboost + specific_save

    model_save_location = save_location + "models/" + model_name + "/"

    train_dataset_loc = save_location + "datasets/" + "train_dataset.pickle"
    train_labels_loc = save_location + "datasets/" + "train_labels.pickle"
    test_dataset_loc = save_location + "datasets/" + "test_dataset.pickle"
    test_labels_loc = save_location + "datasets/" + "test_labels.pickle"
        
    dtrain,scale_pos_weight = create_training_matrix(train_dataset_loc, train_labels_loc, frac_use_data=1, calc_scale_pos_weight=True)
    dtest = create_training_matrix(test_dataset_loc, test_labels_loc, frac_use_data=1, calc_scale_pos_weight=False)
    print("scale_pos_weight:", scale_pos_weight)
        
    if os.path.isfile("/home/zvladimi/MLOIS/xgboost_datasets_plots/sparta_cbol_l0063_n0256_190to178_6.0r200msearch/models/big_model.json"):
        bst = xgb.Booster()
        bst.load_model("/home/zvladimi/MLOIS/xgboost_datasets_plots/sparta_cbol_l0063_n0256_190to178_6.0r200msearch/models/big_model.json")
        print("Loaded Booster")
    else:
        print("Start train")
        output = dxgb.train(
            client,
            {
            "verbosity": 1,
            "tree_method": "hist",
            # Golden line for GPU training
            "device": "cuda",
            'scale_pos_weight': scale_pos_weight,
            'max_depth':4,
            },
            dtrain,
            num_boost_round=1000,
            evals=[(dtrain, "train"), (dtest,"test")],
            early_stopping_rounds=20,            
            )
        bst = output["booster"]
        history = output["history"]
        create_directory(save_location + "models/")
        bst.save_model(save_location + "models/big_model.json")
        #print("Evaluation history:", history)
        plt.figure(figsize=(10,7))
        plt.plot(history["train"]["rmse"], label="Training loss")
        plt.plot(history["test"]["rmse"], label="Validation loss")
        plt.axvline(21, color="gray", label="Optimal tree number")
        plt.xlabel("Number of trees")
        plt.ylabel("Loss")
        plt.legend()
        plt.savefig("/home/zvladimi/MLOIS/Random_figures/training_loss_graph.png")
    #for name, size in sorted(((name, sys.getsizeof(value)) for name, value in list(
     #               locals().items())), key= lambda x: -x[1])[:25]:
      #  print("{:>30}: {:>8}".format(name, sizeof_fmt(size)))      
    
    # you can pass output directly into `predict` too.
    
    del dtrain
    del dtest

    with open(train_dataset_loc, "rb") as file:
        X = pickle.load(file)
    with open(train_labels_loc, "rb") as file:
        y = pickle.load(file)
    X = da.from_array(X,chunks=(chunk_size,X.shape[1]))
    
    train_prediction = dxgb.inplace_predict(client, bst, X)
    train_prediction = np.round(train_prediction)

    print("Train Report")
    print(classification_report(y, train_prediction))

    del X
    del y

    with open(test_dataset_loc, "rb") as file:
        X = pickle.load(file)
    with open(test_labels_loc, "rb") as file:
        y = pickle.load(file)
    X = da.from_array(X,chunks=(chunk_size,X.shape[1]))
    
    test_prediction = dxgb.inplace_predict(client, bst, X)
    test_prediction = np.round(test_prediction)
    
    print("Test Report")
    print(classification_report(y, test_prediction))

        
