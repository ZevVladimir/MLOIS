import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize

import os
import pickle
from sparta_tools import sparta

from src.utils.ML_fxns import setup_client, get_combined_name, get_feature_labels, extract_snaps
from src.utils.util_fxns import create_directory, load_pickle, load_config, save_pickle, load_pickle, timed, load_sparta_mass_prf, load_SPARTA_data
from src.utils.ke_cut_fxns import load_ke_data, opt_ke_predictor
from src.utils.vis_fxns import plt_SPARTA_KE_dist
from src.utils.calc_fxns import calc_rho, calc_mass_acc_rate
from src.utils.prfl_fxns import create_stack_mass_prf, filter_prf, compare_split_prfs
from src.utils.util_fxns import set_cosmology, conv_halo_id_spid,reform_dset_dfs, parse_ranges, split_sparta_hdf5_name

config_params = load_config(os.getcwd() + "/config.ini")

ML_dset_path = config_params["PATHS"]["ml_dset_path"]
path_to_models = config_params["PATHS"]["path_to_models"]
SPARTA_output_path = config_params["SPARTA_DATA"]["sparta_output_path"]

pickle_data = config_params["MISC"]["pickle_data"]

eval_datasets = config_params["EVAL_MODEL"]["eval_datasets"]
plt_nu_splits = parse_ranges(config_params["EVAL_MODEL"]["plt_nu_splits"])
plt_macc_splits = parse_ranges(config_params["EVAL_MODEL"]["plt_macc_splits"])
linthrsh = config_params["EVAL_MODEL"]["linthrsh"]
lin_nbin = config_params["EVAL_MODEL"]["lin_nbin"]
log_nbin = config_params["EVAL_MODEL"]["log_nbin"]
lin_rvticks = config_params["EVAL_MODEL"]["lin_rvticks"]
log_rvticks = config_params["EVAL_MODEL"]["log_rvticks"]
lin_tvticks = config_params["EVAL_MODEL"]["lin_tvticks"]
log_tvticks = config_params["EVAL_MODEL"]["log_tvticks"]
lin_rticks = config_params["EVAL_MODEL"]["lin_rticks"]
log_rticks = config_params["EVAL_MODEL"]["log_rticks"]

features = config_params["TRAIN_MODEL"]["features"]

fast_ke_calib_sims = config_params["KE_CUT"]["fast_ke_calib_sims"]
opt_ke_calib_sims = config_params["KE_CUT"]["opt_ke_calib_sims"]
perc = config_params["KE_CUT"]["perc"]
width = config_params["KE_CUT"]["width"]
grad_lims = config_params["KE_CUT"]["grad_lims"]
r_cut_calib = config_params["KE_CUT"]["r_cut_calib"]
r_cut_pred = config_params["KE_CUT"]["r_cut_pred"]
ke_test_sims = config_params["KE_CUT"]["ke_test_sims"]
    
def overlap_loss(params, lnv2_bin, sparta_labels_bin):
    decision_boundary = params[0]
    line_classif = (lnv2_bin <= decision_boundary).astype(int)  

    # Count misclassified particles
    misclass_orb = np.sum((line_classif == 0) & (sparta_labels_bin == 1))
    misclass_inf = np.sum((line_classif == 1) & (sparta_labels_bin == 0))

    # Loss is the absolute difference between the two misclassification counts
    return abs(misclass_orb - misclass_inf)

def opt_func(bins, r, lnv2, sparta_labels, def_b, plot_loc = "", title = ""):
    # Assign bin indices based on radius
    bin_indices = np.digitize(r, bins) - 1  
    
    magma_cmap = plt.get_cmap("magma")
    magma_cmap.set_under(color='black')
    magma_cmap.set_bad(color='black') 

    intercepts = []
    for i in range(bins.shape[0]-1):
        mask = bin_indices == i
        if np.sum(mask) == 0:
            intercepts.append(def_b)
            continue  # Skip empty bins
        
        lnv2_bin = lnv2[mask]
        sparta_labels_bin = sparta_labels[mask]

        # Optimize

        # initial_guess = [np.min(lnv2_bin)]
        # result_min = minimize(overlap_loss, initial_guess, args=(lnv2_bin, sparta_labels_bin), method="Nelder-Mead")
        
        initial_guess = [np.max(lnv2_bin)]
        result_max = minimize(overlap_loss, initial_guess, args=(lnv2_bin, sparta_labels_bin), method="Nelder-Mead")
        
        initial_guess = [np.mean(lnv2_bin)]
        result_mean = minimize(overlap_loss, initial_guess, args=(lnv2_bin, sparta_labels_bin), method="Nelder-Mead")
        
        if result_mean.fun < result_max.fun:
            result = result_mean
        else:
            result = result_max
        
        calc_b = result.x[0]
            
        create_directory(plot_loc + title + "bins/")
            
        intercepts.append(calc_b)
        
    return {"b":intercepts}
    
if __name__ == "__main__":
    client = setup_client()
    model_type = "kinetic_energy_cut"
    
    comb_fast_model_sims = get_combined_name(fast_ke_calib_sims) 
    comb_opt_model_sims = get_combined_name(opt_ke_calib_sims)   
     
    fast_model_fldr_loc = path_to_models + comb_fast_model_sims + "/" + model_type + "/"
    opt_model_fldr_loc = path_to_models + comb_opt_model_sims + "/" + model_type + "/"  
    create_directory(opt_model_fldr_loc)
    
    #TODO loop the test sims
    dset_params = load_pickle(ML_dset_path + ke_test_sims[0][0] + "/dset_params.pickle")
    sim_cosmol = dset_params["cosmology"]
    all_tdyn_steps = dset_params["t_dyn_steps"]
    
    feature_columns = get_feature_labels(features,all_tdyn_steps)
    snap_list = extract_snaps(opt_ke_calib_sims[0])
    cosmol = set_cosmology(sim_cosmol)
    
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
    
    #TODO make this check not necessary just if you want to have this plotted as well
    param_path = fast_model_fldr_loc + "ke_fastparams_dict.pickle"
    if os.path.exists(param_path):
        ke_param_dict = load_pickle(param_path)
        m_pos = ke_param_dict["m_pos"]
        b_pos = ke_param_dict["b_pos"]
        m_neg = ke_param_dict["m_neg"]
        b_neg = ke_param_dict["b_neg"]
    else:
        raise FileNotFoundError(
            f"Parameter file not found at {param_path}. Please run the fast phase-space cut code to generate it."
        )
    
    #TODO make this a loop
    curr_test_sims = ke_test_sims[0]
    test_comb_name = get_combined_name(curr_test_sims) 
    dset_name = eval_datasets[0]
    plot_loc = opt_model_fldr_loc + dset_name + "_" + test_comb_name + "/plots/"
    create_directory(plot_loc)
    
    if os.path.isfile(opt_model_fldr_loc + "ke_optparams_dict.pickle"):
        print("Loading parameters from saved file")
        opt_param_dict = load_pickle(opt_model_fldr_loc + "ke_optparams_dict.pickle")
        
        with timed("Loading Testing Data"):
            r, vr, lnv2, sparta_labels, samp_data, my_data, halo_df = load_ke_data(client,curr_test_sims=curr_test_sims,sim_cosmol=sim_cosmol,snap_list=snap_list)
            r_test = my_data["p_Scaled_radii"].compute().to_numpy()
            vr_test = my_data["p_Radial_vel"].compute().to_numpy()
            vphys_test = my_data["p_phys_vel"].compute().to_numpy()
            sparta_labels_test = my_data["Orbit_infall"].compute().to_numpy()
            lnv2_test = np.log(vphys_test**2)
            
            halo_first = halo_df["Halo_first"].values
            halo_n = halo_df["Halo_n"].values
            all_idxs = halo_df["Halo_indices"].values
            # Know where each simulation's data starts in the stacked dataset based on when the indexing starts from 0 again
            sim_splits = np.where(halo_first == 0)[0]
        
            sparta_orb = np.where(sparta_labels_test == 1)[0]
            sparta_inf = np.where(sparta_labels_test == 0)[0]
    else:        
        with timed("Optimizing phase-space cut"):
            with timed("Loading Fitting Data"):
                r, vr, lnv2, sparta_labels, samp_data, my_data, halo_df = load_ke_data(client,curr_test_sims=opt_ke_calib_sims,sim_cosmol=sim_cosmol,snap_list=snap_list)
                
                # We use the full dataset since for our custom fitting it does not only specific halos (?)
                r_fit = my_data["p_Scaled_radii"].compute().to_numpy()
                vr_fit = my_data["p_Radial_vel"].compute().to_numpy()
                vphys_fit = my_data["p_phys_vel"].compute().to_numpy()
                sparta_labels_fit = my_data["Orbit_infall"].compute().to_numpy()
                lnv2_fit = np.log(vphys_fit**2)
                
                halo_first = halo_df["Halo_first"].values
                halo_n = halo_df["Halo_n"].values
                all_idxs = halo_df["Halo_indices"].values
                # Know where each simulation's data starts in the stacked dataset based on when the indexing starts from 0 again
                sim_splits = np.where(halo_first == 0)[0]
            
                sparta_orb = np.where(sparta_labels_fit == 1)[0]
                sparta_inf = np.where(sparta_labels_fit == 0)[0]

                mask_vr_neg = (vr_fit < 0)
                mask_vr_pos = ~mask_vr_neg
                mask_r = r_fit < r_cut_calib
                
                
            sparta_name, sparta_search_name = split_sparta_hdf5_name(curr_test_sims[0])
            curr_sparta_HDF5_path = SPARTA_output_path + sparta_name + "/" + sparta_search_name + ".hdf5"      
            
            sparta_output = sparta.load(filename=curr_sparta_HDF5_path, log_level=0)
        
            bins = sparta_output["config"]['anl_prf']["r_bins_lin"]
            bins = np.insert(bins, 0, 0)
            
            vr_pos = opt_func(bins, r_fit[mask_vr_pos], lnv2_fit[mask_vr_pos], sparta_labels_fit[mask_vr_pos], ke_param_dict["b_pos"], plot_loc = plot_loc, title = "pos")
            vr_neg = opt_func(bins, r_fit[mask_vr_neg], lnv2_fit[mask_vr_neg], sparta_labels_fit[mask_vr_neg], ke_param_dict["b_neg"], plot_loc = plot_loc, title = "neg")
        
            opt_param_dict = {
                "orb_vr_pos": vr_pos,
                "orb_vr_neg": vr_neg,
                "inf_vr_neg": vr_neg,
                "inf_vr_pos": vr_pos,
            }
        
            save_pickle(opt_param_dict,opt_model_fldr_loc+"ke_optparams_dict.pickle")
            
            # if the testing simulations are the same as the model simulations we don't need to reload the data
            if sorted(curr_test_sims) == sorted(opt_ke_calib_sims):
                print("Using fitting simulations for testing")
                r_test = r_fit
                vr_test = vr_fit
                vphys_test = vphys_fit
                sparta_labels_test = sparta_labels_fit
                lnv2_test = lnv2_fit
            else:
                with timed("Loading Testing Data"):
                    r, vr, lnv2, sparta_labels, samp_data, my_data, halo_df = load_ke_data(client,curr_test_sims=curr_test_sims)
                    r_test = my_data["p_Scaled_radii"].compute().to_numpy()
                    vr_test = my_data["p_Radial_vel"].compute().to_numpy()
                    vphys_test = my_data["p_phys_vel"].compute().to_numpy()
                    sparta_labels_test = my_data["Orbit_infall"].compute().to_numpy()
                    lnv2_test = np.log(vphys_test**2)
                    
            halo_first = halo_df["Halo_first"].values
            halo_n = halo_df["Halo_n"].values
            all_idxs = halo_df["Halo_indices"].values
            # Know where each simulation's data starts in the stacked dataset based on when the indexing starts from 0 again
            sim_splits = np.where(halo_first == 0)[0]
        
            sparta_orb = np.where(sparta_labels_test == 1)[0]
            sparta_inf = np.where(sparta_labels_test == 0)[0]     
    
    mask_vr_neg = (vr_test < 0)
    mask_vr_pos = ~mask_vr_neg
    mask_r = r_test < r_cut_calib
        
    fltr_combs = {
        "orb_vr_neg": np.intersect1d(sparta_orb, np.where(mask_vr_neg)[0]),
        "orb_vr_pos": np.intersect1d(sparta_orb, np.where(mask_vr_pos)[0]),
        "inf_vr_neg": np.intersect1d(sparta_inf, np.where(mask_vr_neg)[0]),
        "inf_vr_pos": np.intersect1d(sparta_inf, np.where(mask_vr_pos)[0]),
    } 
    
    act_mass_prf_all, act_mass_prf_orb, all_masses, bins = load_sparta_mass_prf(sim_splits,all_idxs,curr_test_sims)
    act_mass_prf_inf = act_mass_prf_all - act_mass_prf_orb 
    
    plt_SPARTA_KE_dist(ke_param_dict, fltr_combs, bins, r_test, lnv2_test, perc = perc, width = width, r_cut = r_cut_calib, plot_loc = plot_loc, title = "bin_fit_", plot_lin_too=True, cust_line_dict = opt_param_dict)

#######################################################################################################################################    
    all_z = []
    all_rhom = []
    with timed("Density Profile Comparison"):
        # if there are multiple simulations, to correctly index the dataset we need to update the starting values for the 
        # stacked simulations such that they correspond to the larger dataset and not one specific simulation
        if len(curr_test_sims) > 1:
            for i,sim in enumerate(curr_test_sims):
                # The first sim remains the same
                if i == 0:
                    continue
                # Else if it isn't the final sim 
                elif i < len(curr_test_sims) - 1:
                    halo_first[sim_splits[i]:sim_splits[i+1]] += (halo_first[sim_splits[i]-1] + halo_n[sim_splits[i]-1])
                # Else if the final sim
                else:
                    halo_first[sim_splits[i]:] += (halo_first[sim_splits[i]-1] + halo_n[sim_splits[i]-1])
        # Get the redshifts for each simulation's primary snapshot
        for i,sim in enumerate(curr_test_sims):
            with open(ML_dset_path + sim + "/dset_params.pickle", "rb") as file:
                dset_params = pickle.load(file)
                curr_z = dset_params["all_snap_info"]["prime_snap_info"]["red_shift"]
                curr_rho_m = dset_params["all_snap_info"]["prime_snap_info"]["rho_m"]
                all_z.append(curr_z)
                all_rhom.append(curr_rho_m)
                h = dset_params["all_snap_info"]["prime_snap_info"]["h"][()]

        tot_num_halos = halo_n.shape[0]
        min_disp_halos = int(np.ceil(0.3 * tot_num_halos))
        
        preds_fit_ke = opt_ke_predictor(opt_param_dict, bins, r_test, vr_test, lnv2_test, r_cut_pred)
        
        calc_mass_prf_all, calc_mass_prf_orb, calc_mass_prf_inf, calc_nus, calc_r200m = create_stack_mass_prf(sim_splits,radii=r_test, halo_first=halo_first, halo_n=halo_n, mass=all_masses, orbit_assn=preds_fit_ke, prf_bins=bins, use_mp=True, all_z=all_z)

        # Halos that get returned with a nan R200m mean that they didn't meet the required number of ptls within R200m and so we need to filter them from our calculated profiles and SPARTA profiles 
        small_halo_fltr = np.isnan(calc_r200m)
        act_mass_prf_all[small_halo_fltr,:] = np.nan
        act_mass_prf_orb[small_halo_fltr,:] = np.nan
        act_mass_prf_inf[small_halo_fltr,:] = np.nan

        # Calculate the density by divide the mass of each bin by the volume of that bin's radius
        calc_dens_prf_all = calc_rho(calc_mass_prf_all*h,bins[1:],calc_r200m*h,sim_splits,all_rhom)
        calc_dens_prf_orb = calc_rho(calc_mass_prf_orb*h,bins[1:],calc_r200m*h,sim_splits,all_rhom)
        calc_dens_prf_inf = calc_rho(calc_mass_prf_inf*h,bins[1:],calc_r200m*h,sim_splits,all_rhom)

        act_dens_prf_all = calc_rho(act_mass_prf_all*h,bins[1:],calc_r200m*h,sim_splits,all_rhom)
        act_dens_prf_orb = calc_rho(act_mass_prf_orb*h,bins[1:],calc_r200m*h,sim_splits,all_rhom)
        act_dens_prf_inf = calc_rho(act_mass_prf_inf*h,bins[1:],calc_r200m*h,sim_splits,all_rhom)

        # If we want the density profiles to only consist of halos of a specific peak height (nu) bin 

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
                
        curr_halos_r200m_list = []
        past_halos_r200m_list = []                
                
        for sim in curr_test_sims:
            dset_params = load_pickle(ML_dset_path + sim + "/dset_params.pickle")
            p_snap = dset_params["all_snap_info"]["prime_snap_info"]["ptl_snap"][()]
            curr_z = dset_params["all_snap_info"]["prime_snap_info"]["red_shift"][()]
            # TODO make this generalizable to when the snapshot separation isn't just 1 dynamical time as needed for mass accretion calculation
            # we can just use the secondary snap here because we already chose to do 1 dynamical time for that snap
            past_z = dset_params["all_snap_info"]["comp_" + str(all_tdyn_steps[0]) + "_tdstp_snap_info"]["red_shift"][()] 
            p_sparta_snap = dset_params["all_snap_info"]["prime_snap_info"]["sparta_snap"][()]
            c_sparta_snap = dset_params["all_snap_info"]["comp_" + str(all_tdyn_steps[0]) + "_tdstp_snap_info"]["sparta_snap"][()]
            
            sparta_name, sparta_search_name = split_sparta_hdf5_name(sim)
            
            curr_sparta_HDF5_path = SPARTA_output_path + sparta_name + "/" + sparta_search_name + ".hdf5"
                    
            # Load the halo's positions and radii
            param_paths = [["halos","R200m"],["halos","id"]]
            sparta_params, sparta_param_names = load_SPARTA_data(curr_sparta_HDF5_path, param_paths, sparta_search_name, pickle_data=pickle_data)

            curr_halos_r200m = sparta_params[sparta_param_names[0]][:,p_sparta_snap]
            curr_halos_ids = sparta_params[sparta_param_names[1]][:,p_sparta_snap]
            
            halo_ddf = reform_dset_dfs(ML_dset_path + sim + "/" + "Test" + "/halo_info/")
            curr_idxs = halo_ddf["Halo_indices"].values
            
            use_halo_r200m = curr_halos_r200m[curr_idxs]
            use_halo_ids = curr_halos_ids[curr_idxs]
            
            sparta_output = sparta.load(filename=curr_sparta_HDF5_path, halo_ids=use_halo_ids, log_level=0)
            new_idxs = conv_halo_id_spid(use_halo_ids, sparta_output, p_sparta_snap) # If the order changed by sparta re-sort the indices
            
            curr_halos_r200m_list.append(sparta_output['halos']['R200m'][:,p_sparta_snap])
            past_halos_r200m_list.append(sparta_output['halos']['R200m'][:,c_sparta_snap])
            
        curr_halos_r200m = np.concatenate(curr_halos_r200m_list)
        past_halos_r200m = np.concatenate(past_halos_r200m_list)
            
        calc_maccs = calc_mass_acc_rate(curr_halos_r200m,past_halos_r200m,curr_z,past_z)

        cpy_plt_macc_splits = plt_macc_splits.copy()
        for i,macc_split in enumerate(cpy_plt_macc_splits):
            # Take the second element of the where to filter by the halos (?)
            fltr = np.where((calc_maccs > macc_split[0]) & (calc_maccs < macc_split[1]))[0]
            if fltr.shape[0] > 25:
                all_prf_lst.append(filter_prf(calc_dens_prf_all,act_dens_prf_all,min_disp_halos,fltr))
                orb_prf_lst.append(filter_prf(calc_dens_prf_orb,act_dens_prf_orb,min_disp_halos,fltr))
                inf_prf_lst.append(filter_prf(calc_dens_prf_inf,act_dens_prf_inf,min_disp_halos,fltr))
            else:
                plt_macc_splits.remove(macc_split)
        
        
        compare_split_prfs(plt_nu_splits,len(cpy_plt_nu_splits),all_prf_lst,orb_prf_lst,inf_prf_lst,bins[1:],lin_rticks,plot_loc,title= "fit_ke_cut_dens_",prf_name_0="Optimized Cut", prf_name_1="SPARTA")
        