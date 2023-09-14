import pickle
import h5py 
import os
import numpy as np
from pygadgetreader import readsnap, readheader

def create_directory(path):
    if os.path.exists(path) != True:
        os.makedirs(path)

def check_pickle_exist_gadget(ptl_property, snapshot, snapshot_path, pickle_path):
    # save to folder containing pickled data to be accessed easily later
    file_path = pickle_path + str(snapshot) + "/" + ptl_property + "_" + snapshot + ".pickle" 
    create_directory(pickle_path + str(snapshot) + "/")
    
    # check if the file has already been pickled if so just load it
    if os.path.isfile(file_path):
        with open(file_path, "rb") as pickle_file:
            particle_info = pickle.load(pickle_file)
    # otherwise load the specific information from the particle data and save it as a pickle file
    else:
        particle_info = readsnap(snapshot_path, ptl_property, 'dm')
        with open(file_path, "wb") as pickle_file:
            pickle.dump(particle_info, pickle_file)
    return particle_info

def check_pickle_exist_hdf5_prop(snapshot, first_group, second_group, third_group, hdf5_path, sparta_name, pickle_path):
    # save to folder containing pickled data to be accessed easily later
    file_path = pickle_path + str(snapshot) + "/" + first_group + "_" + second_group + "_" + third_group + "_" + sparta_name + ".pickle" 
    create_directory(pickle_path + str(snapshot) + "/")
    
    # check if the file has already been pickled if so just load it
    if os.path.isfile(file_path):
        with open(file_path, "rb") as pickle_file:
            halo_info = pickle.load(pickle_file)
    # otherwise load the specific information from the SPARTA hdf5 file and save it as a pickle file
    else:
        with h5py.File(hdf5_path, 'r') as file:
            if third_group != "":
                halo_info = file[first_group][second_group][third_group][:]
            else:
                halo_info = file[first_group][second_group][:]
        with open(file_path, "wb") as pickle_file:
            pickle.dump(halo_info, pickle_file)
    return halo_info

def load_or_pickle_ptl_data(snapshot, snapshot_path, scale_factor, little_h, pickle_path):
    ptl_pid = check_pickle_exist_gadget("pid", snapshot, snapshot_path, pickle_path)
    ptl_vel = check_pickle_exist_gadget("vel", snapshot, snapshot_path, pickle_path)
    ptl_pos = check_pickle_exist_gadget("pos", snapshot, snapshot_path, pickle_path)
    ptl_mass = check_pickle_exist_gadget("mass", snapshot, snapshot_path, pickle_path)

    ptl_pos = ptl_pos * 10**3 * scale_factor * little_h # convert to kpc and physical
    ptl_mass = ptl_mass[0] * 10**10 # units M_sun/h

    return ptl_pid, ptl_vel, ptl_pos, ptl_mass

def load_or_pickle_SPARTA_data(sparta_name, hdf5_path, scale_factor, little_h, snap, pickle_path):
    halos_pos = check_pickle_exist_hdf5_prop(snap, "halos", "position", "", hdf5_path, sparta_name, pickle_path)
    halos_vel = check_pickle_exist_hdf5_prop(snap, "halos", "velocity", "", hdf5_path, sparta_name, pickle_path)
    halo_last_snap = check_pickle_exist_hdf5_prop(snap, "halos", "last_snap", "", hdf5_path, sparta_name, pickle_path)
    halos_r200m = check_pickle_exist_hdf5_prop(snap, "halos", "R200m", "", hdf5_path, sparta_name, pickle_path)
    halo_id = check_pickle_exist_hdf5_prop(snap, "halos", "id", "", hdf5_path, sparta_name, pickle_path)
    halo_status = check_pickle_exist_hdf5_prop(snap, "halos", "status", "", hdf5_path, sparta_name, pickle_path)
    
    density_prf_all = check_pickle_exist_hdf5_prop(snap, "anl_prf", "M_all", "", hdf5_path, sparta_name, pickle_path)
    density_prf_1halo = check_pickle_exist_hdf5_prop(snap, "anl_prf", "M_1halo", "", hdf5_path, sparta_name, pickle_path)
    
    halos_pos = halos_pos[:,snap,:]
    halos_vel = halos_vel[:,snap,:]
    halos_r200m = halos_r200m[:,snap]
    halo_id = halo_id[:,snap]
    halo_status = halo_status[:,snap]
    density_prf_all = density_prf_all[:,snap,:]
    density_prf_1halo = density_prf_1halo[:,snap,:]
    
    halos_pos = halos_pos * 10**3 * scale_factor * little_h # convert to kpc and physical
    halos_r200m = halos_r200m * little_h # convert to kpc

    return halos_pos, halos_vel, halos_r200m, halo_id, density_prf_all, density_prf_1halo, halo_status, halo_last_snap

def standardize(values):
    for col in range(values.shape[1]):
        values[:,col] = (values[:,col] - values[:,col].mean())/values[:,col].std()
    return values

def normalize(values):
    for col in range(values.shape[1]):
        values[:,col] = (values[:,col] - values[:,col].min())/(values[:,col].max() - values[:,col].min())
    return values

def build_ml_dataset(save_path, data_location, sparta_name, dataset_name, snapshot_list):
    save_path = save_path + "datasets/"
    create_directory(save_path)
    dataset_path = save_path + dataset_name + "_dataset_" + sparta_name 
    
    for snap in snapshot_list:
        dataset_path = dataset_path + "_" + str(snap)
    dataset_path = dataset_path + ".pickle"
    # if the directory for this hdf5 file exists if not make it
    if os.path.exists(save_path) != True:
        os.makedirs(save_path)
    if os.path.exists(dataset_path) != True:
        num_cols = 0
        with h5py.File((data_location + dataset_name + "_all_particle_properties_" + sparta_name + ".hdf5"), 'r') as all_ptl_properties: 
            for key in all_ptl_properties.keys():
                if all_ptl_properties[key].ndim > 1:
                    num_cols += all_ptl_properties[key].shape[1]
                else:
                    num_cols += 1
            num_params_per_snap = (num_cols - 2) / len(snapshot_list)    
            num_rows = all_ptl_properties[key].shape[0]
            full_dataset = np.zeros((num_rows, num_cols))
            all_keys = np.empty(num_cols,dtype=object)
            curr_col = 0
            for key in all_ptl_properties.keys():
                if all_ptl_properties[key].ndim > 1:
                    for row in range(all_ptl_properties[key].ndim):
                        access_col = int((curr_col + (row * num_params_per_snap)))
                        full_dataset[:,access_col] = all_ptl_properties[key][:,row]
                        all_keys[access_col] = (key + str(snapshot_list[row]))
                    curr_col += 1
                else:
                    full_dataset[:,curr_col] = all_ptl_properties[key]
                    all_keys[curr_col] = (key + str(snapshot_list[0]))
                    curr_col += 1
    
        # once all the halos are gone through save them as pickles for later  
        with open(dataset_path, "wb") as pickle_file:
            pickle.dump(full_dataset, pickle_file)
        with open(save_path + dataset_name + "_dataset_all_keys.pickle", "wb") as pickle_file:
            pickle.dump(all_keys, pickle_file)
    # if there are already pickle files just open them
    else:
        with open(dataset_path, "rb") as pickle_file:
            full_dataset = pickle.load(pickle_file)
        with open(save_path + dataset_name + "_dataset_all_keys.pickle", "rb") as pickle_file:
            all_keys = pickle.load(pickle_file)
    return full_dataset, all_keys

def save_to_hdf5(new_file, hdf5_file, data_name, dataset, chunk, max_shape, curr_idx, max_num_keys):
    if new_file and len(list(hdf5_file.keys())) < (max_num_keys):
        hdf5_file.create_dataset(data_name, data = dataset, chunks = chunk, maxshape = max_shape)
    # with a new file adding on additional data to the datasets
    elif new_file and len(list(hdf5_file.keys())) == (max_num_keys):
        hdf5_file[data_name].resize((hdf5_file[data_name].shape[0] + dataset.shape[0]), axis = 0)
        hdf5_file[data_name][-dataset.shape[0]:] = dataset   

    # if not a new file and same num of particles will just replace the previous information
    if not new_file:
        hdf5_file[data_name][curr_idx:curr_idx + dataset.shape[0]] = dataset
        
def choose_halo_split(indices, snap, halo_props, particle_props, num_features):
    start_idxs = halo_props["Halo_start_ind_" + snap].to_numpy()
    num_ptls = halo_props["Halo_num_ptl_" + snap].to_numpy()

    dataset = np.zeros((np.sum(num_ptls[indices]), num_features))
    start = 0
    for idx in indices:
        start_ind = start_idxs[idx]
        curr_num_ptl = num_ptls[idx]
        dataset[start:start+curr_num_ptl] = particle_props[start_ind:start_ind+curr_num_ptl]

        start = start + curr_num_ptl

    return dataset

def find_closest_snap(cosmology, time_find, num_snaps, path_to_snap, snap_format):
    closest_time = 0
    closest_snap = 0
    for i in range(num_snaps):
        red_shift = readheader(path_to_snap + "snapdir_" + snap_format.format(i) + "/snapshot_" + snap_format.format(i), 'redshift')
        comp_time = cosmology.age(red_shift)
        
        if np.abs(time_find - comp_time) < np.abs(time_find - closest_time):
            closest_time = comp_time
            closest_snap = i
    return closest_snap