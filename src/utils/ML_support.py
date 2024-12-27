from dask import array as da
import dask.dataframe as dd
from dask import delayed
from dask.distributed import Client
import xgboost as xgb
from xgboost import dask as dxgb

import numpy as np
import os
import pickle
import json
import h5py
import re
import matplotlib.pyplot as plt
import pandas as pd
from colossus.lss import peaks
from colossus import cosmology
import warnings

from skopt import gp_minimize
from skopt.space import Real
from sklearn.metrics import accuracy_score
from functools import partial

from .data_and_loading_functions import load_SPARTA_data, find_closest_z, conv_halo_id_spid, timed, split_data_by_halo, parse_ranges, create_nu_string
from .visualization_functions import plot_per_err
from .update_vis_fxns import plot_full_ptl_dist, plot_miss_class_dist, compare_prfs_nu, compare_prfs, inf_orb_frac
from .calculation_functions import create_mass_prf, create_stack_mass_prf, filter_prf, calculate_density
from sparta_tools import sparta 
from colossus.cosmology import cosmology

##################################################################################################################
# LOAD CONFIG PARAMETERS
import configparser
config = configparser.ConfigParser()
config.read(os.getcwd() + "/config.ini")
rand_seed = config.getint("MISC","random_seed")
use_gpu = config.getboolean("MISC","use_gpu")
curr_sparta_file = config["MISC"]["curr_sparta_file"]
sim_cosmol = config["MISC"]["sim_cosmol"]

snap_path = config["PATHS"]["snap_path"]
SPARTA_output_path = config["PATHS"]["SPARTA_output_path"]
pickled_path = config["PATHS"]["pickled_path"]
ML_dset_path = config["PATHS"]["ML_dset_path"]

if sim_cosmol == "planck13-nbody":
    sim_pat = r"cpla_l(\d+)_n(\d+)"
    cosmol = cosmology.setCosmology('planck13-nbody',{'flat': True, 'H0': 67.0, 'Om0': 0.32, 'Ob0': 0.0491, 'sigma8': 0.834, 'ns': 0.9624, 'relspecies': False})
else:
    cosmol = cosmology.setCosmology(sim_cosmol) 
    sim_pat = r"cbol_l(\d+)_n(\d+)"
match = re.search(sim_pat, curr_sparta_file)
if match:
    sparta_name = match.group(0)
SPARTA_hdf5_path = SPARTA_output_path + sparta_name + "/" + curr_sparta_file + ".hdf5"

p_red_shift = config.getfloat("SEARCH","p_red_shift")

file_lim = config.getint("XGBOOST","file_lim")

reduce_rad = config.getfloat("XGBOOST","reduce_rad")
reduce_perc = config.getfloat("XGBOOST", "reduce_perc")

weight_rad = config.getfloat("XGBOOST","weight_rad")
min_weight = config.getfloat("XGBOOST","min_weight")
weight_exp = config.getfloat("XGBOOST","weight_exp")

hpo_loss = config.get("XGBOOST","hpo_loss")
nu_splits = config["XGBOOST"]["nu_splits"]
plt_nu_splits = config["XGBOOST"]["plt_nu_splits"]
plt_nu_splits = parse_ranges(nu_splits)

linthrsh = config.getfloat("XGBOOST","linthrsh")
lin_nbin = config.getint("XGBOOST","lin_nbin")
log_nbin = config.getint("XGBOOST","log_nbin")
lin_rvticks = json.loads(config.get("XGBOOST","lin_rvticks"))
log_rvticks = json.loads(config.get("XGBOOST","log_rvticks"))
lin_tvticks = json.loads(config.get("XGBOOST","lin_tvticks"))
log_tvticks = json.loads(config.get("XGBOOST","log_tvticks"))
lin_rticks = json.loads(config.get("XGBOOST","lin_rticks"))
log_rticks = json.loads(config.get("XGBOOST","log_rticks"))

if use_gpu:
    from dask_cuda import LocalCUDACluster
    import cudf
    import dask_cudf as dc

# Instantiate a dask cluster with GPUs
def get_CUDA_cluster():
    cluster = LocalCUDACluster(
                               device_memory_limit='10GB',
                               jit_unspill=True)
    client = Client(cluster)
    return client

# Make predictions using the model. Requires the inputs to be a dask dataframe. Can either return the predictions still as a dask dataframe or as a numpy array
def make_preds(client, bst, X, dask = False, threshold = 0.5):
    if dask:
        preds = dxgb.predict(client,bst,X)
        preds = preds.map_partitions(lambda df: (df >= threshold).astype(int))
        return preds
    else:
        preds = dxgb.inplace_predict(client, bst, X).compute()
        preds = (preds >= threshold).astype(np.int8)
    
    return preds

# This function prints out all the model information such as the training simulations, training parameters, and results
# The results are split by simulation that the model was tested on and reports the misclassification rate on each population
def print_model_prop(model_dict, indent=''):
    # If using from command line and passing path to the pickled dictionary instead of dict load the dict from the file path
    if isinstance(model_dict, str):
        with open(model_dict, "rb") as file:
            model_dict = pickle.load(file)
        
    for key, value in model_dict.items():
        # use recursion for dictionaries within the dictionary
        if isinstance(value, dict):
            print(f"{indent}{key}:")
            print_model_prop(value, indent + '  ')
        # if the value is instead a list join them all together with commas
        elif isinstance(value, list):
            print(f"{indent}{key}: {', '.join(map(str, value))}")
        else:
            print(f"{indent}{key}: {value}")

# From the input simulation name extract the simulation name (ex: cbol_l0063_n0256) and the SPARTA hdf5 output name (ex: cbol_l0063_n0256_4r200m_1-5v200m)
def split_calc_name(sim):
    sim_pat = r"cbol_l(\d+)_n(\d+)"
    match = re.search(sim_pat, sim)
    if not match:
        sim_pat = r"cpla_l(\d+)_n(\d+)"
        match = re.search(sim_pat,sim)
        
    if match:
        sim_name = match.group(0)
           
    sim_search_pat = sim_pat + r"_(\d+)r200m_(\d+)v200m"
    name_match = re.search(sim_search_pat, sim)
    
    # also check if there is a decimal for v200m
    if not name_match:
        sim_search_pat = sim_pat + r"_(\d+)r200m_(\d+)-(\d+)v200m"
        name_match = re.search(sim_search_pat, sim)
    
    if name_match:
        search_name = name_match.group(0)
        
    if not name_match and not match:
        print("Couldn't read sim name correctly:",sim)
        print(match)
    
    return sim_name, search_name

# Convert a simulation's name to where the primary snapshot location is in the pickled data (ex: cbol_l0063_n0256_4r200m_1-5v200m_190to166 -> 190_cbol_l0063_n0256_4r200m_1-5v200m)
def get_pickle_path_for_sim(input_str):
    # Define the regex pattern to match the string parts
    pattern = r"_([\d]+)to([\d]+)"
    
    # Search for the pattern in the input string
    match = re.search(pattern, input_str)
    
    if not match:
        raise ValueError("Input string:",input_str, "does not match the expected format.")

    # Extract the parts of the string
    prefix = input_str[:match.start()]
    first_number = match.group(1)
    
    # Construct the new string
    new_string = f"{first_number}_{prefix}"
    
    return new_string

# Use a function to assign weights for XGBoost training for each particle based on their radii
def weight_by_rad(radii,orb_inf,use_weight_rad=weight_rad,use_min_weight=min_weight,use_weight_exp=weight_exp,weight_inf=False,weight_orb=True):
    weights = np.ones(radii.shape[0])

    if weight_inf and weight_orb:
        mask = (radii > use_weight_rad)
    elif weight_orb:
        mask = (radii > use_weight_rad) & (orb_inf == 1)
    elif weight_inf:
        mask = (radii > use_weight_rad) & (orb_inf == 0)
    else:
        print("No weights calculated. Make sure to set weight_inf and/or weight_orb = True")
        return pd.DataFrame(weights)
    weights[mask] = (np.exp((np.log(use_min_weight)/(np.max(radii)-use_weight_rad)) * (radii[mask]-use_weight_rad)))**use_weight_exp

    return pd.DataFrame(weights)

# For each radial bin beyond an inputted radius randomly reduce the number of particles present to a certain percentage of the number of particles within that inptuted radius
def scale_by_rad(data,bin_edges,use_red_rad=reduce_rad,use_red_perc=reduce_perc):
    radii = data["p_Scaled_radii"].values
    max_ptl = int(np.floor(np.where(radii<use_red_rad)[0].shape[0] * use_red_perc))
    filter_data = []
    
    for i in range(len(bin_edges) - 1):
        bin_mask = (radii >= bin_edges[i]) & (radii < bin_edges[i+1])
        bin_data = data[bin_mask]
        if len(bin_data) > int(max_ptl) and bin_edges[i] > 1:
            bin_data = bin_data.sample(n=max_ptl,replace=False)
        filter_data.append(bin_data)
    
    filter_data = pd.concat(filter_data) 
    
    return filter_data

# Returns an inputted dataframe with only the halos that fit within the inputted ranges of nus (peak height)
#TODO return updated halo_n and halo_first?
def filter_df_with_nus(df,nus,halo_first,halo_n):    
    # First masks which halos are within the inputted nu ranges
    mask = pd.Series([False] * nus.shape[0])
    for start, end in nu_splits:
        mask[np.where((nus >= start) & (nus <= end))[0]] = True
    
    # Then get the indices of all the particles that belong to these halos and combine them into another mask which returns only the wanted particles    
    halo_n = halo_n[mask]
    halo_first = halo_first[mask]
    halo_last = halo_first + halo_n
 
    use_idxs = np.concatenate([np.arange(start, end) for start, end in zip(halo_first, halo_last)])

    return df.iloc[use_idxs]

# Goes through a folder where a dataset's hdf5 files are stored and reforms them into one pandas dataframe (in order)
def reform_dataset_dfs(folder_path):
    hdf5_files = []
    for f in os.listdir(folder_path):
        if f.endswith('.h5'):
            hdf5_files.append(f)
    hdf5_files.sort()

    dfs = []
    for file in hdf5_files:
        file_path = os.path.join(folder_path, file)
        df = pd.read_hdf(file_path) 
        dfs.append(df) 
    return pd.concat(dfs, ignore_index=True)

# Sorts a dataset's .h5 files such that they are in ascending numerical order and if desired can return a limited number of them based off the file_lim parameter in the config file
def sort_and_lim_files(folder_path,limit_files=False):
    hdf5_files = []
    for f in os.listdir(folder_path):
        if f.endswith('.h5'):
            hdf5_files.append(f)
    hdf5_files.sort()
    if file_lim > 0 and file_lim < len(hdf5_files) and limit_files:
        hdf5_files = hdf5_files[:file_lim]
    return hdf5_files
    
# Returns a simulation's mass used and the redshift of the primary snapshot
def sim_mass_p_z(sim,config_params):
    sparta_name, sparta_search_name = split_calc_name(sim)
            
    with h5py.File(SPARTA_output_path + sparta_name + "/" +  sparta_search_name + ".hdf5","r") as f:
        dic_sim = {}
        grp_sim = f['simulation']
        for f in grp_sim.attrs:
            dic_sim[f] = grp_sim.attrs[f]
    
    p_red_shift = config_params["p_red_shift"]
    
    all_red_shifts = dic_sim['snap_z']
    p_sparta_snap = np.abs(all_red_shifts - p_red_shift).argmin()
    use_z = all_red_shifts[p_sparta_snap]
    p_snap_loc = get_pickle_path_for_sim(sim)
    with open(pickled_path + p_snap_loc + "/ptl_mass.pickle", "rb") as pickle_file:
        ptl_mass = pickle.load(pickle_file)
    
    return ptl_mass, use_z

# Split a dataframe so that each one is below an inputted maximum memory size
def split_dataframe(df, max_size, weights=None, use_weights = False):
    total_size = df.memory_usage(index=True).sum()
    num_splits = int(np.ceil(total_size / max_size))
    chunk_size = int(np.ceil(len(df) / num_splits))
    print("splitting Dataframe into:",num_splits,"dataframes")
    
    split_dfs = []
    split_weights = []
    for i in range(0, len(df), chunk_size):
        split_dfs.append(df.iloc[i:i + chunk_size])
        if use_weights:
            split_weights.append(weights[i:i+chunk_size])
    
    if use_weights:
        return split_dfs, split_weights
    else:
        return split_dfs

# Function to process a file in a dataset's folder: combines them all, performs any desired filtering, calculates weights if desired, and calculates scaled position weight
# Also splits the dataframe into smaller dataframes based of inputted maximum memory size
def process_file(folder_path, file_index, ptl_mass, use_z, bin_edges, max_mem, filter_nu, scale_rad, use_weights):
    @delayed
    def delayed_task():
        ptl_path = f"{folder_path}/ptl_info/ptl_{file_index}.h5"
        halo_path = f"{folder_path}/halo_info/halo_{file_index}.h5"

        ptl_df = pd.read_hdf(ptl_path)
        halo_df = pd.read_hdf(halo_path)

        # reset indices for halo_first halo_n indexing
        halo_df["Halo_first"] = halo_df["Halo_first"] - halo_df["Halo_first"][0]
        
        # Calculate peak heights for each halo
        nus = np.array(peaks.peakHeight((halo_df["Halo_n"][:] * ptl_mass), use_z))
        
        # Filter by nu and/or by radius
        if filter_nu:
            ptl_df = filter_df_with_nus(ptl_df, nus, halo_df["Halo_first"], halo_df["Halo_n"])
        if scale_rad:
            ptl_df = scale_by_rad(ptl_df,bin_edges)
            
        weights = (
            weight_by_rad(ptl_df["p_Scaled_radii"].values, ptl_df["Orbit_infall"].values, 
                          weight_inf=False, weight_orb=True) if use_weights else None
        )

        # Calculate scale position weight
        scal_pos_weight = calc_scal_pos_weight(ptl_df)

        # If the dataframe is too large split it up
        if ptl_df.memory_usage(index=True).sum() > max_mem:
            ptl_dfs = split_dataframe(ptl_df, max_mem)
            if use_weights:
                ptl_dfs, weights = split_dataframe(ptl_df,max_mem,weights,use_weights=True)
        else:
            ptl_dfs = [ptl_df]
            if use_weights:
                weights = [weights]
        
        return ptl_dfs,scal_pos_weight,weights
    return delayed_task()

# Combines the results of the processing of each file in the folder into one dataframe for the data and list for the scale position weights and an array of weights if desired
def combine_results(results, client, use_weights):
    # Unpack the results
    ddfs,scal_pos_weights,dask_weights = [], [], []
    
    for res in results:
        ddfs.extend(res[0])
        scal_pos_weights.append(res[1]) # We append since scale position weight is just a number
        if use_weights:
            dask_weights.extend(res[2])
            
    all_ddfs = dd.concat([dd.from_delayed(client.scatter(df)) for df in ddfs])
    if use_weights:
        all_weights = dd.concat([dd.from_delayed(client.scatter(w)) for w in dask_weights])
        return all_ddfs, scal_pos_weights, all_weights

    return all_ddfs, scal_pos_weights

# Combines all the files in a dataset's folder into one dask dataframe and a list for the scale position weights and an array of weights if desired 
def reform_datasets(client,ptl_mass,use_z,max_mem,bin_edges,folder_path,scale_rad=False,use_weights=False,filter_nu=None,limit_files=False):
    ptl_files = sort_and_lim_files(folder_path + "/ptl_info/",limit_files=limit_files)
    
    # Create delayed tasks for each file
    delayed_results = [
        process_file(
            folder_path, file_index, ptl_mass, use_z, bin_edges,
            max_mem, scale_rad, use_weights, filter_nu
        )
        for file_index in range(len(ptl_files))
    ]

    # Compute the results in parallel
    results = client.compute(delayed_results, sync=True)

    return combine_results(results, client, use_weights)
    
# Calculates the scaled position weight for a dataset. Which is used to weight the model towards the population with less particles (should be the orbiting population)
def calc_scal_pos_weight(df):
    count_negatives = (df['Orbit_infall'] == 0).sum()
    count_positives = (df['Orbit_infall'] == 1).sum()

    scale_pos_weight = count_negatives / count_positives
    return scale_pos_weight

# Loads all the data for the inputted list of simulations into one dataframe. Finds the scale position weight for the dataset and any adjusted weighting for it if desired
def load_data(client, sims, dset_name, bin_edges = None, limit_files = False, scale_rad=False, use_weights=False, filter_nu=False):
    dask_dfs = []
    all_scal_pos_weight = []
    all_weights = []
    
    for sim in sims:
        with open(ML_dset_path + sim + "/config.pickle","rb") as f:
            config_params = pickle.load(f)
        # Get mass and redshift for this simulation
        ptl_mass, use_z = sim_mass_p_z(sim,config_params)
        max_mem = int(np.floor(config_params["HDF5 Mem Size"] / 2))
        
        if dset_name == "Full":
            datasets = ["Train", "Test"]
        else:
            datasets = [dset_name]

        for dataset in datasets:
            with timed(f"Reformed {dataset} Dataset: {sim}"): 
                dataset_path = f"{ML_dset_path}{sim}/{dataset}"
                if use_weights:
                    ptl_ddf,sim_scal_pos_weight, weights = reform_datasets(client,ptl_mass,use_z,max_mem,bin_edges,dataset_path,scale_rad=scale_rad,use_weights=use_weights,filter_nu=filter_nu,limit_files=limit_files)  
                    all_weights.append(weights)
                else:
                    ptl_ddf,sim_scal_pos_weight = reform_datasets(client,ptl_mass,use_z,max_mem,bin_edges,dataset_path,scale_rad=scale_rad,use_weights=use_weights,filter_nu=filter_nu,limit_files=limit_files)  
                all_scal_pos_weight.append(sim_scal_pos_weight)
                dask_dfs.append(ptl_ddf)
                    
    all_scal_pos_weight = np.average(np.concatenate([np.array(sublist).flatten() for sublist in all_scal_pos_weight]))
    act_scale_pos_weight = np.average(all_scal_pos_weight)

    all_dask_dfs = dd.concat(dask_dfs)
    
    if use_weights:
        return all_dask_dfs,act_scale_pos_weight, dd.concat(all_weights)
    else:
        return all_dask_dfs,act_scale_pos_weight

def load_sprta_mass_prf(sim_splits,all_idxs,use_sims,ret_r200m=False):                
    mass_prf_all_list = []
    mass_prf_1halo_list = []
    all_r200m_list = []
    all_masses = []
    
    for i,sim in enumerate(use_sims):
        # Get the halo indices corresponding to this simulation
        if i < len(use_sims) - 1:
            use_idxs = all_idxs[sim_splits[i]:sim_splits[i+1]]
        else:
            use_idxs = all_idxs[sim_splits[i]:]
        
        
        sparta_name, sparta_search_name = split_calc_name(sim)
        # find the snapshots for this simulation
        snap_pat = r"(\d+)to(\d+)"
        match = re.search(snap_pat, sim)
        if match:
            curr_snap_list = [match.group(1), match.group(2)] 
        
        with open(ML_dset_path + sim + "/config.pickle", "rb") as file:
            config_dict = pickle.load(file)
            
            curr_z = config_dict["p_snap_info"]["red_shift"][()]
            curr_snap_dir_format = config_dict["snap_dir_format"]
            curr_snap_format = config_dict["snap_format"]
            new_p_snap, curr_z = find_closest_z(curr_z,snap_path + sparta_name + "/",curr_snap_dir_format,curr_snap_format)
            p_scale_factor = 1/(1+curr_z)
            
        with h5py.File(SPARTA_output_path + sparta_name + "/" + sparta_search_name + ".hdf5","r") as f:
            dic_sim = {}
            grp_sim = f['simulation']

            for attr in grp_sim.attrs:
                dic_sim[attr] = grp_sim.attrs[attr]
        
        all_red_shifts = dic_sim['snap_z']
        p_sparta_snap = np.abs(all_red_shifts - curr_z).argmin()
        
        halos_pos, halos_r200m, halos_id, halos_status, halos_last_snap, parent_id, ptl_mass = load_SPARTA_data(SPARTA_hdf5_path,sparta_search_name, p_scale_factor, curr_snap_list[0], p_sparta_snap)

        use_halo_ids = halos_id[use_idxs]
        
        sparta_output = sparta.load(filename=SPARTA_output_path + sparta_name + "/" + sparta_search_name + ".hdf5", halo_ids=use_halo_ids, log_level=0)
        new_idxs = conv_halo_id_spid(use_halo_ids, sparta_output, p_sparta_snap) # If the order changed by sparta re-sort the indices
        
        mass_prf_all_list.append(sparta_output['anl_prf']['M_all'][new_idxs,p_sparta_snap,:])
        mass_prf_1halo_list.append(sparta_output['anl_prf']['M_1halo'][new_idxs,p_sparta_snap,:])

        all_r200m_list.append(sparta_output['halos']['R200m'][:,p_sparta_snap])

        all_masses.append(ptl_mass)

    mass_prf_all = np.vstack(mass_prf_all_list)
    mass_prf_1halo = np.vstack(mass_prf_1halo_list)
    all_r200m = np.concatenate(all_r200m_list)
    
    bins = sparta_output["config"]['anl_prf']["r_bins_lin"]
    bins = np.insert(bins, 0, 0)

    if ret_r200m:
        return mass_prf_all,mass_prf_1halo,all_masses,bins,all_r200m
    else:
        return mass_prf_all,mass_prf_1halo,all_masses,bins

def eval_model(model_info, client, model, use_sims, dst_type, X, y, halo_ddf, combined_name, plot_save_loc, dens_prf = False,missclass=False,full_dist=False,io_frac=False,per_err=False,split_nu=False): 
    with timed("Predictions"):
        print(f"Starting predictions for {y.size.compute():.3e} particles")
        preds = make_preds(client, model, X)
    X = X.compute()
    y = y.compute()
    
    X_scatter = client.scatter(X)
    X = dd.from_delayed(X_scatter)
    y_scatter = client.scatter(y)
    y = dd.from_delayed(y_scatter)

    num_bins = 30

    if dens_prf:
        halo_first = halo_ddf["Halo_first"].values
        halo_n = halo_ddf["Halo_n"].values
        all_idxs = halo_ddf["Halo_indices"].values

        all_z = []
        all_rhom = []
        # Know where each simulation's data starts in the stacked dataset based on when the indexing starts from 0 again
        sim_splits = np.where(halo_first == 0)[0]

        # if there are multiple simulations, to correctly index the dataset we need to update the starting values for the 
        # stacked simulations such that they correspond to the larger dataset and not one specific simulation
        if len(use_sims) > 1:
            for i,sim in enumerate(use_sims):
                # The first sim remains the same
                if i == 0:
                    continue
                # Else if it isn't the final sim 
                elif i < len(use_sims) - 1:
                    halo_first[sim_splits[i]:sim_splits[i+1]] += (halo_first[sim_splits[i]-1] + halo_n[sim_splits[i]-1])
                # Else if the final sim
                else:
                    halo_first[sim_splits[i]:] += (halo_first[sim_splits[i]-1] + halo_n[sim_splits[i]-1])
        
        # Get the redshifts for each simulation's primary snapshot
        for i,sim in enumerate(use_sims):
            with open(ML_dset_path + sim + "/config.pickle", "rb") as file:
                config_dict = pickle.load(file)
                curr_z = config_dict["p_snap_info"]["red_shift"][()]
                all_z.append(curr_z)
                all_rhom.append(cosmol.rho_m(curr_z))
                h = config_dict["p_snap_info"]["h"][()]
        
        tot_num_halos = halo_n.shape[0]
        min_disp_halos = int(np.ceil(0.3 * tot_num_halos))
        
        act_mass_prf_all, act_mass_prf_orb,all_masses,bins = load_sprta_mass_prf(sim_splits,all_idxs,use_sims)
        act_mass_prf_inf = act_mass_prf_all - act_mass_prf_orb
        
        calc_mass_prf_all, calc_mass_prf_orb, calc_mass_prf_inf, calc_nus, calc_r200m = create_stack_mass_prf(sim_splits,radii=X["p_Scaled_radii"].values.compute(), halo_first=halo_first, halo_n=halo_n, mass=all_masses, orbit_assn=preds.values, prf_bins=bins, use_mp=True, all_z=all_z)

        # Halos that get returned with a nan R200m mean that they didn't meet the required number of ptls within R200m and so we need to filter them from our calculated profiles and SPARTA profiles 
        small_halo_fltr = np.isnan(calc_r200m)
        act_mass_prf_all[small_halo_fltr,:] = np.nan
        act_mass_prf_orb[small_halo_fltr,:] = np.nan
        act_mass_prf_inf[small_halo_fltr,:] = np.nan

        # Calculate the density by divide the mass of each bin by the volume of that bin's radius
        calc_dens_prf_all = calculate_density(calc_mass_prf_all*h,bins[1:],calc_r200m*h,sim_splits,all_rhom)
        calc_dens_prf_orb = calculate_density(calc_mass_prf_orb*h,bins[1:],calc_r200m*h,sim_splits,all_rhom)
        calc_dens_prf_inf = calculate_density(calc_mass_prf_inf*h,bins[1:],calc_r200m*h,sim_splits,all_rhom)
        
        act_dens_prf_all = calculate_density(act_mass_prf_all*h,bins[1:],calc_r200m*h,sim_splits,all_rhom)
        act_dens_prf_orb = calculate_density(act_mass_prf_orb*h,bins[1:],calc_r200m*h,sim_splits,all_rhom)
        act_dens_prf_inf = calculate_density(act_mass_prf_inf*h,bins[1:],calc_r200m*h,sim_splits,all_rhom)

        if split_nu:
            all_prf_lst = []
            orb_prf_lst = []
            inf_prf_lst = []
            cpy_plt_nu_splits = plt_nu_splits.copy()
            for i,nu_split in enumerate(cpy_plt_nu_splits):
                # Take the second element of the where to filter by the halos (?)
                fltr = np.where((calc_nus > nu_split[0]) & (calc_nus < nu_split[1]))[0]
                if fltr.shape[0] > 25:
                    all_prf_lst.append(filter_prf(calc_dens_prf_all,act_dens_prf_all,min_disp_halos,fltr))
                    orb_prf_lst.append(filter_prf(calc_dens_prf_orb,act_dens_prf_orb,min_disp_halos,fltr))
                    inf_prf_lst.append(filter_prf(calc_dens_prf_inf,act_dens_prf_inf,min_disp_halos,fltr))
                else:
                    plt_nu_splits.remove(nu_split)

            compare_prfs_nu(plt_nu_splits,len(cpy_plt_nu_splits),all_prf_lst,orb_prf_lst,inf_prf_lst,bins[1:],lin_rticks,plot_save_loc,title="dens_")
        else:
            all_prf_lst = filter_prf(calc_dens_prf_all,act_dens_prf_all,min_disp_halos)
            orb_prf_lst = filter_prf(calc_dens_prf_orb,act_dens_prf_orb,min_disp_halos)
            inf_prf_lst = filter_prf(calc_dens_prf_inf,act_dens_prf_inf,min_disp_halos)
            
            # Ignore warnigns about taking mean/median of empty slices and division by 0 that are expected with how the profiles are handled
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                compare_prfs(all_prf_lst,orb_prf_lst,inf_prf_lst,bins[1:],lin_rticks,plot_save_loc,title="dens_",use_med=True)
                compare_prfs(all_prf_lst,orb_prf_lst,inf_prf_lst,bins[1:],lin_rticks,plot_save_loc,title="dens_",use_med=False)
        
        
    if missclass or full_dist or io_frac:       
        p_corr_labels=y.compute().values.flatten()
        p_ml_labels=preds.values
        p_r=X["p_Scaled_radii"].values.compute()
        p_rv=X["p_Radial_vel"].values.compute()
        p_tv=X["p_Tangential_vel"].values.compute()
        c_r=X["c_Scaled_radii"].values.compute()
        c_rv=X["c_Radial_vel"].values.compute()
        
        split_scale_dict = {
            "linthrsh":linthrsh, 
            "lin_nbin":lin_nbin,
            "log_nbin":log_nbin,
            "lin_rvticks":lin_rvticks,
            "log_rvticks":log_rvticks,
            "lin_tvticks":lin_tvticks,
            "log_tvticks":log_tvticks,
            "lin_rticks":lin_rticks,
            "log_rticks":log_rticks,
        }
    
    if full_dist:
        plot_full_ptl_dist(p_corr_labels=p_corr_labels,p_r=p_r,p_rv=p_rv,p_tv=p_tv,c_r=c_r,c_rv=c_rv,split_scale_dict=split_scale_dict,num_bins=num_bins,save_loc=plot_save_loc)
    if missclass:
        curr_sim_name = ""
        for sim in use_sims:
            curr_sim_name += sim
            curr_sim_name += "_"
        curr_sim_name += dst_type
        plot_miss_class_dist(p_corr_labels=p_corr_labels,p_ml_labels=p_ml_labels,p_r=p_r,p_rv=p_rv,p_tv=p_tv,c_r=c_r,c_rv=c_rv,split_scale_dict=split_scale_dict,num_bins=num_bins,save_loc=plot_save_loc,model_info=model_info,dataset_name=curr_sim_name)
    if io_frac:
        inf_orb_frac(p_corr_labels=p_corr_labels,p_r=p_r,p_rv=p_rv,p_tv=p_tv,c_r=c_r,c_rv=c_rv,split_scale_dict=split_scale_dict,num_bins=num_bins,save_loc=plot_save_loc)
    if per_err:
        with h5py.File(SPARTA_hdf5_path,"r") as f:
            dic_sim = {}
            grp_sim = f['config']['anl_prf']
            for f in grp_sim.attrs:
                dic_sim[f] = grp_sim.attrs[f]
            bins = dic_sim["r_bins_lin"]
        plot_per_err(bins,X["p_Scaled_radii"].values.compute(),y.compute().values.flatten(),preds.values,plot_save_loc, "$r/r_{200m}$","rad")
        # plot_per_err(bins,X["p_Radial_vel"].values.compute(),y.compute().values.flatten(),preds.values,plot_save_loc, "$v_r/v_{200m}$","rad_vel")
        # plot_per_err(bins,X["p_Tangential_vel"].values.compute(),y.compute().values.flatten(),preds.values,plot_save_loc, "$v_t/v_{200m}$","tang_vel")

def plot_tree(bst,tree_num,save_loc):
    fig, ax = plt.subplots(figsize=(400, 10))
    xgb.plot_tree(bst, num_trees=tree_num, ax=ax,rankdir='LR')
    fig.savefig(save_loc + "/tree_plot.png")
       
def dens_prf_loss(halo_ddf,use_sims,radii,labels,use_orb_prf,use_inf_prf):
    halo_first = halo_ddf["Halo_first"].values
    halo_n = halo_ddf["Halo_n"].values
    all_idxs = halo_ddf["Halo_indices"].values

    # Know where each simulation's data starts in the stacked dataset based on when the indexing starts from 0 again
    sim_splits = np.where(halo_first == 0)[0]
    # if there are multiple simulations, to correctly index the dataset we need to update the starting values for the 
    # stacked simulations such that they correspond to the larger dataset and not one specific simulation
    if len(use_sims) != 1:
        for i in range(1,len(use_sims)):
            if i < len(use_sims) - 1:
                halo_first[sim_splits[i]:sim_splits[i+1]] += (halo_first[sim_splits[i]-1] + halo_n[sim_splits[i]-1])
            else:
                halo_first[sim_splits[i]:] += (halo_first[sim_splits[i]-1] + halo_n[sim_splits[i]-1])
               
    sparta_mass_prf_all,sparta_mass_prf_orb,all_masses,bins = load_sprta_mass_prf(sim_splits,all_idxs,use_sims)
    sparta_mass_prf_inf = sparta_mass_prf_all - sparta_mass_prf_orb
    sparta_mass_prf_orb = np.sum(sparta_mass_prf_orb,axis=0)
    sparta_mass_prf_inf = np.sum(sparta_mass_prf_inf,axis=0)
    #TODO make this robust for multiple sims
    calc_mass_prf_all,calc_mass_prf_orb,calc_mass_prf_inf = create_mass_prf(radii,labels,bins,all_masses[0]) 
    
    if use_orb_prf:
        use_orb = np.where(sparta_mass_prf_orb > 0)[0]
        orb_loss = np.sum(np.abs((sparta_mass_prf_orb[use_orb] - calc_mass_prf_orb[use_orb]) / sparta_mass_prf_orb[use_orb])) / bins.size
        if orb_loss == np.nan:
            orb_loss = 50
        elif orb_loss == np.inf:
            orb_loss == 50
    
    if use_inf_prf:
        use_inf = np.where(sparta_mass_prf_inf > 0)[0]
        inf_loss = np.sum(np.abs((sparta_mass_prf_inf[use_inf] - calc_mass_prf_inf[use_inf]) / sparta_mass_prf_inf[use_inf])) / bins.size
        if inf_loss == np.nan:
            inf_loss = 50
        elif inf_loss == np.inf:
            inf_loss == 50
    
    if use_orb_prf and use_inf_prf:
        print(orb_loss,inf_loss,orb_loss+inf_loss)
        return orb_loss+inf_loss
    elif use_orb_prf:
        print(orb_loss)
        return orb_loss
    elif use_inf_prf:
        print(inf_loss)
        return inf_loss

def weight_objective(params,client,model_params,ptl_ddf,halo_ddf,use_sims,feat_cols,tar_col):
    train_dst,val_dst,train_halos,val_halos = split_data_by_halo(0.6,halo_ddf,ptl_ddf,return_halo=True)

    X_train = train_dst[feat_cols]
    y_train = train_dst[tar_col]
    
    X_val = val_dst[feat_cols]
    y_val = val_dst[tar_col]
    
    curr_weight_rad, curr_min_weight, curr_weight_exp = params

    train_radii = X_train["p_Scaled_radii"].values.compute()

    weights = weight_by_rad(train_radii,y_train.compute().values.flatten(), curr_weight_rad, curr_min_weight, curr_weight_exp)

    dask_weights = []
    scatter_weight = client.scatter(weights)
    dask_weight = dd.from_delayed(scatter_weight) 
    dask_weights.append(dask_weight)
        
    train_weights = dd.concat(dask_weights)
    
    train_weights = train_weights.repartition(npartitions=X_train.npartitions)

        
    dtrain = xgb.dask.DaskDMatrix(client, X_train, y_train, weight=train_weights)
    
    output = dxgb.train(
                client,
                model_params,
                dtrain,
                num_boost_round=50,
                # evals=[(dtrain, "train"),(dtest, "test")],
                evals=[(dtrain, "train")],
                early_stopping_rounds=5,      
                )
    bst = output["booster"]

    y_pred = make_preds(client, bst, X_val, report_name="Report", print_report=False)
    y_val = y_val.compute().values.flatten()
    
    # multiply the accuracies by -1 because we want to maximize them but we are using minimization
    if hpo_loss == "all":
        accuracy = -1 * accuracy_score(y_val, y_pred)
    elif hpo_loss == "orb":
        only_orb = np.where(y_val == 1)[0]
        accuracy = -1 * accuracy_score(y_val[only_orb], y_pred.iloc[only_orb].values)
    elif hpo_loss == "inf":
        only_inf = np.where(y_val == 0)[0]
        accuracy = -1 * accuracy_score(y_val[only_inf], y_pred.iloc[only_inf].values)
    elif hpo_loss == "mprf_all":
        val_radii = X_val["p_Scaled_radii"].values.compute()
        accuracy = dens_prf_loss(val_halos,use_sims,val_radii,y_pred,use_orb_prf=True,use_inf_prf=True)
    elif hpo_loss == "mprf_orb":
        val_radii = X_val["p_Scaled_radii"].values.compute()
        accuracy = dens_prf_loss(val_halos,use_sims,val_radii,y_pred,use_orb_prf=True,use_inf_prf=False)
    elif hpo_loss == "mprf_inf":
        val_radii = X_val["p_Scaled_radii"].values.compute()
        accuracy = dens_prf_loss(val_halos,use_sims,val_radii,y_pred,use_orb_prf=False,use_inf_prf=True)

    return accuracy

def scal_rad_objective(params,client,model_params,ptl_ddf,halo_ddf,use_sims,feat_cols,tar_col):
    train_dst,val_dst,train_halos,val_halos = split_data_by_halo(client,0.5,halo_ddf,ptl_ddf,return_halo=True)
    
    X_val = val_dst[feat_cols]
    y_val = val_dst[tar_col]
    
    data_pd = train_dst.compute()
    num_bins=100
    bin_edges = np.logspace(np.log10(0.001),np.log10(10),num_bins)
    scld_data = scale_by_rad(data_pd,bin_edges,params[0],params[1])
    
    scatter_scld = client.scatter(scld_data)
    scld_data_ddf = dd.from_delayed(scatter_scld)

    X_train = scld_data_ddf[feat_cols]
    y_train = scld_data_ddf[tar_col]
    
    dtrain = xgb.dask.DaskDMatrix(client, X_train, y_train)
    
    output = dxgb.train(
                client,
                model_params,
                dtrain,
                num_boost_round=50,
                # evals=[(dtrain, "train"),(dtest, "test")],
                evals=[(dtrain, "train")],
                early_stopping_rounds=5,      
                )
    bst = output["booster"]

    y_pred = make_preds(client, bst, X_val, report_name="Report", print_report=False)
    y_val = y_val.compute().values.flatten()
    only_orb = np.where(y_val == 1)[0]
    only_inf = np.where(y_val == 0)[0]

    accuracy = accuracy_score(y_val, y_pred)
    # accuracy = accuracy_score(y[only_orb], y_pred.iloc[only_orb].values)
    # accuracy = accuracy_score(y[only_inf], y_pred.iloc[only_inf].values)
    
    # val_radii = X_val["p_Scaled_radii"].values.compute()
    # accuracy = -1 * dens_prf_loss(val_halos,use_sims,val_radii,y_pred)
    
    return -accuracy

def print_iteration(res):
    iteration = len(res.x_iters)
    print(f"Iteration {iteration}: Current params: {res.x_iters[-1]}, Current score: {res.func_vals[-1]}")

def optimize_weights(client,model_params,ptl_ddf,halo_ddf,use_sims,feat_cols,tar_col):
    print("Start Optimization of Weights")
    space  = [Real(0.1, 5.0, name='weight_rad'),
            Real(0.001, 0.2, name='min_weight'),
            Real(0.1,10,name='weight_exp')]

    objective_with_params = partial(weight_objective,client=client,model_params=model_params,ptl_ddf=ptl_ddf,halo_ddf=halo_ddf,use_sims=use_sims,feat_cols=feat_cols,tar_col=tar_col)
    res = gp_minimize(objective_with_params, space, n_calls=50, random_state=0, callback=[print_iteration])

    print("Best parameters: ", res.x)
    print("Best accuracy: ", -res.fun)
    
    return res.x[0],res.x[1],res.x[2]
    
def optimize_scale_rad(client,model_params,ptl_ddf,halo_ddf,use_sims,feat_cols,tar_col):    
    print("Start Optimization of Scaling Radii")
    space  = [Real(0.1, 5.0, name='reduce_rad'),
            Real(0.0001, 0.25, name='reduce_perc')]

    objective_with_params = partial(scal_rad_objective,client=client,model_params=model_params,ptl_ddf=ptl_ddf,halo_ddf=halo_ddf,use_sims=use_sims,feat_cols=feat_cols,tar_col=tar_col)
    res = gp_minimize(objective_with_params, space, n_calls=50, random_state=0, callback=[print_iteration])

    print("Best parameters: ", res.x)
    print("Best accuracy: ", -res.fun)
    
    return res.x[0],res.x[1]
    
def get_combined_name(model_sims):
    combined_name = ""
    for i,sim in enumerate(model_sims):
        split_string = sim.split('_')
        
        r_patt = r'(\d+-\d+|\d+)r'
        r_match = re.search(r_patt,split_string[3])

        
        v_patt = r'(\d+-\d+|\d+)v'
        v_match = re.search(v_patt, split_string[4])


        cond_string = split_string[0] + split_string[1] + split_string[2] 
        # can add these for more information per name
        #+ "r" + r_match.group(1) + "v" + v_match.group(1) + "s" + split_string[5]
        
        combined_name += cond_string
    
    return combined_name
    
def filter_ddf(X, y = None, preds = None, fltr_dic = None, col_names = None, max_size=500):
    with timed("Filter DF"):
        full_filter = None
        if fltr_dic is not None:
            if "X_filter" in fltr_dic:
                for feature, (operator, value) in fltr_dic["X_filter"].items():
                    if operator == '>':
                        condition = X[feature] > value
                    elif operator == '<':
                        condition = X[feature] < value
                    elif operator == '>=':
                        condition = X[feature] >= value
                    elif operator == '<=':
                        condition = X[feature] <= value
                    elif operator == '==':
                        if value == "nan":
                            condition = X[feature].isna()
                        else:
                            condition = X[feature] == value
                    elif operator == '!=':
                        condition = X[feature] != value
                        
                    if feature == next(iter(fltr_dic[next(iter(fltr_dic))])):
                        full_filter = condition
                    else:
                        full_filter &= condition
                
            if "label_filter" in fltr_dic:
                for feature, value in fltr_dic["label_filter"].items():
                    if feature == "act":
                        condition = y["Orbit_infall"] == value
                    elif feature == "pred":
                        condition = preds == value
                    if feature == next(iter(fltr_dic[next(iter(fltr_dic))])):
                        full_filter = condition
                    else:
                        full_filter &= condition

            
            X = X[full_filter]
        nrows = X.shape[0].compute()
            
        if nrows > max_size and max_size > 0:
            sample = max_size / nrows
        else:
            sample = 1.0
            
        if sample > 0 and sample < 1:
            X = X.sample(frac=sample,random_state=rand_seed)
        
        if col_names != None:
            X.columns = col_names
            
        # Return the filtered array and the indices of the original array that remain
        return X.compute(), X.index.values.compute()
    
# Can set max_size to 0 to include all the particles
def shap_with_filter(explainer, X, y, preds, fltr_dic = None, col_names = None, max_size=500):
    X_fltr,fltr = filter_ddf(X, y, preds, fltr_dic = fltr_dic, col_names = col_names, max_size=max_size)
    return explainer(X_fltr), explainer.shap_values(X_fltr), X_fltr
    
    