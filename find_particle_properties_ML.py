import numpy as np
from pygadgetreader import readsnap, readheader
from scipy.spatial import cKDTree
from colossus.cosmology import cosmology
import matplotlib.pyplot as plt
from colossus.halo import mass_so
from colossus.lss import peaks
from matplotlib.pyplot import cm
import time
import h5py
from data_and_loading_functions import load_or_pickle_SPARTA_data, load_or_pickle_ptl_data, save_to_hdf5
from calculation_functions import *
from visualization_functions import compare_density_prf, rad_vel_vs_radius_plot
from sparta import sparta

def initial_search(halo_positions, search_radius, halo_r200m):
    num_halos = halo_positions.shape[0]
    particles_per_halo = np.zeros(num_halos, dtype = np.int32)
    all_halo_mass = np.zeros(num_halos, dtype = np.float32)
    
    for i in range(num_halos):
        #find how many particles we are finding
        indices = primary_particle_tree.query_ball_point(halo_positions[i,:], r = search_radius * halo_r200m[i])

        # how many new particles being added and correspondingly how massive the halo is
        num_new_particles = len(indices)
        all_halo_mass[i] = num_new_particles * mass
        particles_per_halo[i] = num_new_particles

    print("Total num particles: ", np.sum(particles_per_halo))
    print("Total num halos: ", num_halos)
    
    return particles_per_halo, all_halo_mass

def search_halos(halo_idxs, halo_positions, halo_r200m, search_radius, total_particles, dens_prf_all, dens_prf_1halo, start_nu, end_nu, curr_halo_id, sparta_file_path, snapshot_list):
    primary_snap = snapshot_list[0]
    global halo_start_idx
    num_halos = halo_positions.shape[0]
    halo_indices = np.zeros((num_halos,2), dtype = np.int32)
    all_part_vel = np.zeros((total_particles,3), dtype = np.float32)

    calculated_r200m = np.zeros(halo_r200m.size)
    calculated_radial_velocities = np.zeros((total_particles), dtype = np.float32)
    calculated_radial_velocities_comp = np.zeros((total_particles,3), dtype = np.float32)
    calculated_tangential_velocities_comp = np.zeros((total_particles,3), dtype = np.float32)
    calculated_tangential_velocities_magn  = np.zeros((total_particles), dtype = np.float32)
    all_radii = np.zeros((total_particles), dtype = np.float32)
    all_scaled_radii = np.zeros(total_particles, dtype = np.float32)
    r200m_per_part = np.zeros(total_particles, dtype = np.float32)
    all_orbit_assn = np.zeros((total_particles,2), dtype = np.int64)

    start = 0
    t_start = time.time()
    for i in range(num_halos):
        # find the indices of the particles within the expected r200 radius multiplied by times_r200 
        indices = primary_particle_tree.query_ball_point(halo_positions[i,primary_snap,:], r = search_radius * halo_r200m[i,primary_snap])
        
        #Only take the particle positions that where found with the tree
        current_particles_pos = prim_particles_pos[indices,:]
        current_particles_vel = prim_particles_vel[indices,:]
        current_particles_pid = prim_particles_pid[indices]
        # current_orbit_assn_sparta: halo_idx, PID, orb/inf
        current_orbit_assn_sparta = np.zeros((current_particles_pid.size, 3))
        current_halos_pos = halo_positions[i,primary_snap,:]        

        current_orbit_assn_sparta[:,0] = current_particles_pid
        current_orbit_assn_sparta[:,1] = halo_idxs[i]

        # how many new particles being added
        num_new_particles = len(indices)
        halo_indices[i,0] = halo_start_idx
        halo_indices[i,1] = num_new_particles
        halo_start_idx = halo_start_idx + num_new_particles

        #for how many new particles create an array of how much mass there should be within that particle radius
        use_mass = np.arange(1, num_new_particles + 1, 1) * mass       
        
        all_part_vel[start:start+num_new_particles] = current_particles_vel
            
        #calculate the radii of each particle based on the distance formula
        unsorted_particle_radii, unsorted_coord_dist = calculate_distance(current_halos_pos[0], current_halos_pos[1], current_halos_pos[2], current_particles_pos[:,0],
                                    current_particles_pos[:,1], current_particles_pos[:,2], num_new_particles, box_size)         
              
              
        sparta_output = sparta.load(filename = sparta_file_path, halo_ids = curr_halo_id[i], log_level = 0)['tcr_ptl']['res_oct'] # last_pericenter_snap, n_is_lower_limit, n_pericenter, tracer_id
        sparta_last_pericenter_snap = sparta_output['last_pericenter_snap']
        sparta_tracer_ids = sparta_output['tracer_id']
        sparta_n_is_lower_limit = sparta_output['n_is_lower_limit']
        sparta_n_pericenter = sparta_output['n_pericenter']
        
        orbit_assn_sparta = np.zeros((sparta_tracer_ids.size, 2), dtype = np.int64)
        orbit_assn_sparta[:,0] = sparta_tracer_ids

        # only want pericenters that have occurred at or before this snapshot
        sparta_n_pericenter[np.where(sparta_last_pericenter_snap > primary_snap)[0]] = 0

        # if there is more than one pericenter count as orbiting (1) and if it isn't it is infalling (0)
        orbit_assn_sparta[np.where(sparta_n_pericenter > 0)[0],1] = 1

        # However particle can also be orbiting if n_is_lower_limit is 1
        orbit_assn_sparta[np.where(sparta_n_is_lower_limit == 1)[0],1] = 1

        poss_pids = np.intersect1d(current_particles_pid, orbit_assn_sparta[:,0], return_indices = True) # only check pids that are within the tracers for this halo (otherwise infall)
        poss_pid_match = np.intersect1d(current_particles_pid[poss_pids[1]], orbit_assn_sparta[:,0], return_indices = True) # get the corresponding indices for the pids and their infall/orbit assn
        # create a mask to then set any particle that is not identified as orbiting to be infalling
        current_orbit_assn_sparta[poss_pids[1],2] = orbit_assn_sparta[poss_pid_match[2],1]
        mask = np.ones(current_particles_pid.size, dtype = bool) 
        mask[poss_pids[1]] = False
        current_orbit_assn_sparta[mask,2] = 0 # set every pid that didn't have a match to infalling  

        #sort the radii, positions, velocities, coord separations to allow for creation of plots and to correctly assign how much mass there is
        arrsortrad = unsorted_particle_radii.argsort()
        particle_radii = unsorted_particle_radii[arrsortrad]
        current_particles_pos = current_particles_pos[arrsortrad]
        current_particles_vel = current_particles_vel[arrsortrad]
        #current_orbit_assn = current_orbit_assn[arrsortrad]
        current_orbit_assn_sparta = current_orbit_assn_sparta[arrsortrad]
        coord_dist = unsorted_coord_dist[arrsortrad]
        
        #calculate the density at each particle
        calculated_densities = np.zeros(num_new_particles)
        calculated_densities = calculate_density(use_mass, particle_radii)
        
        #determine indices of particles where the expected r200 value is 
        indices_r200_met = check_where_r200(calculated_densities, rho_m)
        
        #if only one index is less than 200 * rho_c then that is the r200 radius
        if indices_r200_met[0].size == 1:
            calculated_r200m[i] = particle_radii[indices_r200_met[0][0]]
        #if there are none then the radius is 0
        elif indices_r200_met[0].size == 0:
            calculated_r200m[i] = 0
        #if multiple indices choose the first two and average them
        else:
            calculated_r200m[i] = (particle_radii[indices_r200_met[0][0]] + particle_radii[indices_r200_met[0][1]])/2
        
        
        # calculate peculiar, radial, and tangential velocity
        peculiar_velocity = calc_pec_vel(current_particles_vel, halos_vel[i])
        calculated_radial_velocities[start:start+num_new_particles], calculated_radial_velocities_comp[start:start+num_new_particles], curr_v200m, physical_vel, rhat = calc_rad_vel(peculiar_velocity, particle_radii, coord_dist, halo_r200m[i], red_shift, little_h, hubble_constant)
        calculated_tangential_velocities_comp[start:start+num_new_particles] = calc_tang_vel(calculated_radial_velocities[start:start+num_new_particles], physical_vel, rhat)/curr_v200m
        calculated_tangential_velocities_magn[start:start+num_new_particles] = np.linalg.norm(calculated_tangential_velocities_comp[start:start+num_new_particles], axis = 1)

        # scale radial velocities and their components by V200m
        # scale radii by R200m
        # assign all values to portion of entire array for this halo mass bin
        calculated_radial_velocities[start:start+num_new_particles] = calculated_radial_velocities[start:start+num_new_particles]/curr_v200m
        calculated_radial_velocities_comp[start:start+num_new_particles] = calculated_radial_velocities_comp[start:start+num_new_particles]/curr_v200m
        all_radii[start:start+num_new_particles] = particle_radii
        all_scaled_radii[start:start+num_new_particles] = particle_radii/halo_r200m[i]
        r200m_per_part[start:start+num_new_particles] = halo_r200m[i]
        all_orbit_assn[start:start+num_new_particles] = current_orbit_assn_sparta
            
        if i == 50 or i == 100 or i == 113:
            compare_density_prf(particle_radii/halo_r200m[i], dens_prf_all[i], dens_prf_1halo[i], mass, current_orbit_assn_sparta[:,2], i, start_nu, end_nu)

        start += num_new_particles

        if i % 250 == 0 and i != 0:
            t_lap = time.time()
            tot_time = t_lap - t_start
            t_remain = (num_halos - i)/250 * tot_time
            print("Halos:", (i-250), "to", i, "time taken:", np.round(tot_time,2), "seconds" , "time remaining:", np.round(t_remain/60,2), "minutes,",  np.round((t_remain),2), "seconds")
            t_start = t_lap
            
    return all_orbit_assn, calculated_radial_velocities, all_radii, all_scaled_radii, r200m_per_part, calculated_radial_velocities_comp, calculated_tangential_velocities_comp, calculated_tangential_velocities_magn, halo_indices
    
def split_into_bins(num_bins, radial_vel, scaled_radii, particle_radii, halo_r200_per_part):
    start_bin_val = 0.001
    finish_bin_val = np.max(scaled_radii)
    
    bins = np.logspace(np.log10(start_bin_val), np.log10(finish_bin_val), num_bins)
    
    bin_start = 0
    average_val_part = np.zeros((num_bins,2), dtype = np.float32)
    average_val_hubble = np.zeros((num_bins,2), dtype = np.float32)
    
    # For each bin
    for i in range(num_bins - 1):
        bin_end = bins[i]
        
        # Find which particle belong in that bin
        indices_in_bin = np.where((scaled_radii >= bin_start) & (scaled_radii < bin_end))[0]
 
        if indices_in_bin.size != 0:
            # Get all the scaled radii within this bin and average it
            use_scaled_particle_radii = scaled_radii[indices_in_bin]
            average_val_part[i, 0] = np.average(use_scaled_particle_radii)
            
            # Get all the radial velocities within this bin and average it
            use_vel_rad = radial_vel[indices_in_bin]
            average_val_part[i, 1] = np.average(use_vel_rad)
            
            # get all the radii within this bin
            hubble_radius = particle_radii[indices_in_bin]

            # Find the median value and then the median value for the corresponding R200m values
            median_hubble_radius = np.median(hubble_radius)
            median_hubble_r200 = np.median(halo_r200_per_part[indices_in_bin])
            median_scaled_hubble = median_hubble_radius/median_hubble_r200
            
            # Calculate the v200m value for the corresponding R200m value found
            average_val_hubble[i,0] = median_scaled_hubble
            corresponding_hubble_m200m = mass_so.R_to_M(median_hubble_r200, red_shift, "200c") * little_h # convert to M⊙
            average_val_hubble[i,1] = (median_hubble_radius * hubble_constant)/calc_v200m(corresponding_hubble_m200m, median_hubble_r200)
            
        bin_start = bin_end
    
    return average_val_part, average_val_hubble    
    
def split_halo_by_mass(num_bins, halos_status, halos_last_snap, num_ptl_params, num_halo_params, start_nu, num_iter, nu_step, times_r200m, halo_r200m, sparta_file_path, sparta_file_name, snapshot_list, new_file, snap_done):
    primary_snap = snapshot_list[0] 
    # with h5py.File((save_location + "all_halo_properties" + sparta_file_name + ".hdf5"), 'a') as all_halo_properties:
    #     if new_file:
    #         for key in all_halo_properties.keys():
    #             del all_halo_properties[key]
    #         new_file_halo = True
    #     else:
    #         new_file_halo = False

    # with h5py.File((save_location + "all_particle_properties" + sparta_file_name + ".hdf5"), 'a') as all_particle_properties:
    #     # Determine if we are creating a completely new file (file doesn't have any keys) or if we are accessing a different number of particles
    #     if new_file:
    #         for key in all_particle_properties.keys():
    #             del all_particle_properties[key]
    #         new_file_ptl = True
    #     else:
    #         new_file_ptl = False

    color = iter(cm.rainbow(np.linspace(0, 1, num_iter)))
    
    print("\nstart initial search")    
    # get the halo_masses and number of particles
    num_particles_per_halo, halo_masses = initial_search(halos_pos, times_r200m, halo_r200m)
    print("finish initial search")
    total_num_particles = np.sum(num_particles_per_halo)
    # convert masses to peaks
    scaled_halo_mass = halo_masses/little_h # units M⊙/h
    peak_heights = peaks.peakHeight(scaled_halo_mass, red_shift)

    file_counter = 0

    # For how many mass bin splits
    for j in range(num_iter):
        t_start = time.time()
        c = next(color)
        end_nu = start_nu + nu_step
        print("\nStart split:", start_nu, "to", end_nu)
        
        # Get the indices of the halos that are within the desired peaks as well as ones that are 
        halos_within_range = np.where((peak_heights >= start_nu) & (peak_heights < end_nu) & (halos_last_snap >= primary_snap) & (halos_status[primary_snap] == 10))[0]
        print("Num halos: ", halos_within_range.shape[0])
        
        # only get the parameters we want for this specific halo bin
        if halos_within_range.shape[0] > 0:
            use_halo_pos = halos_pos[halos_within_range]
            use_halo_r200m = halo_r200m[halos_within_range]
            use_density_prf_all = density_prf_all[halos_within_range]
            use_density_prf_1halo = density_prf_1halo[halos_within_range]
            use_num_particles = num_particles_per_halo[halos_within_range]
            use_halo_id = halos_id[halos_within_range]

            total_num_use_particles = np.sum(use_num_particles)
            
            print("Num particles: ", total_num_use_particles)
            

            # calculate all the information
            orbital_assign, radial_velocities, radii, scaled_radii, r200m_per_part, radial_velocities_comp, tangential_velocities_comp, tangential_velocities_magn, halo_idxs = search_halos(halos_within_range, use_halo_pos, use_halo_r200m, times_r200m, total_num_use_particles, use_density_prf_all, use_density_prf_1halo, start_nu, end_nu, use_halo_id, sparta_file_path, snapshot_list)             
            with h5py.File((save_location + "all_particle_properties" + sparta_file_name + ".hdf5"), 'a') as all_particle_properties:

                save_to_hdf5(new_file, all_particle_properties, "PIDS_" + str(primary_snap), dataset = orbital_assign[:,0], chunk = True, max_shape = (total_num_particles,), curr_idx = file_counter, max_num_keys = num_ptl_params, num_snap = snap_done)
                save_to_hdf5(new_file, all_particle_properties, "Orbit_Infall_" + str(primary_snap), dataset = orbital_assign[:,1], chunk = True, max_shape = (total_num_particles,), curr_idx = file_counter, max_num_keys = num_ptl_params, num_snap = snap_done)
                save_to_hdf5(new_file, all_particle_properties, "Scaled_radii_" + str(primary_snap), dataset = scaled_radii, chunk = True, max_shape = (total_num_particles,), curr_idx = file_counter, max_num_keys = num_ptl_params, num_snap = snap_done)
                save_to_hdf5(new_file, all_particle_properties, "Radial_vel_magn_" + str(primary_snap), dataset = radial_velocities, chunk = True, max_shape = (total_num_particles,), curr_idx = file_counter, max_num_keys = num_ptl_params, num_snap = snap_done)
                save_to_hdf5(new_file, all_particle_properties, "Tangential_vel_magn_" + str(primary_snap), dataset = tangential_velocities_magn, chunk = True, max_shape = (total_num_particles,), curr_idx = file_counter, max_num_keys = num_ptl_params, num_snap = snap_done)
            
            with h5py.File((save_location + "all_halo_properties" + sparta_file_name + ".hdf5"), 'a') as all_halo_properties:

                save_to_hdf5(new_file, all_halo_properties, "Halo_start_ind_" + str(primary_snap), dataset = halo_idxs[:,0], chunk = True, max_shape = (total_num_halos,), curr_idx = file_counter, max_num_keys = num_halo_params, num_snap = snap_done)
                save_to_hdf5(new_file, all_halo_properties, "Halo_num_ptl_" + str(primary_snap), dataset = halo_idxs[:,1], chunk = True, max_shape = (total_num_halos,), curr_idx = file_counter, max_num_keys = num_halo_params, num_snap = snap_done)
                save_to_hdf5(new_file, all_halo_properties, "Halo_id_" + str(primary_snap), dataset = use_halo_id, chunk = True, max_shape = (total_num_halos,), curr_idx = file_counter, max_num_keys = num_halo_params, num_snap = snap_done)
            
            file_counter = file_counter + scaled_radii.shape[0]
               
            # plot the scaled radial vel vs scaled radius
            # graph_rad_vel, graph_val_hubble = split_into_bins(num_bins, radial_velocities, scaled_radii, radii, r200m_per_part)
            # graph_rad_vel = graph_rad_vel[~np.all(graph_rad_vel == 0, axis=1)]
            # graph_val_hubble = graph_val_hubble[~np.all(graph_val_hubble == 0, axis=1)]

            #rad_vel_vs_radius_plot(graph_rad_vel, graph_val_hubble, start_nu, end_nu, c, ax)
        t_end = time.time()
        print("finished bin:", start_nu, "to", end_nu, "in", np.round((t_end- t_start)/60,2), "minutes,", np.round((t_end- t_start),2), "seconds")
        start_nu = end_nu
        
num_bins = 50        
start_nu = 0
nu_step = 0.5
num_iter = 7
num_save_ptl_params = 5
num_save_halo_params = 3
times_r200 = 6
dynamical_time = 2.448854618582507 # calculated by (2 * R200m)/V200m not sure how to do this each time... but hard coded for now from running this code with set snapshots
global halo_start_idx 
curr_sparta_file = "sparta_cbol_l0063_n0256"

# snapshot list should go from high to low (the first value will be what is searched around and generally you want that to be the more recent snap)
snapshot_list = [190, 189]

primary_snapshot = snapshot_list[0]
hdf5_file_path = "/home/zvladimi/MLOIS/SPARTA_data/" + curr_sparta_file + ".hdf5"
save_location =  "/home/zvladimi/MLOIS/calculated_info/" + "calc_from_" + curr_sparta_file + "_" + str(snapshot_list[0]) + "to" + str(snapshot_list[-1]) + "/"

t1 = time.time()
print("start particle assign")


t3 = time.time()

halo_start_idx = 0
cosmol = cosmology.setCosmology("bolshoi")
little_h = cosmol.h 

for i, snap in enumerate(snapshot_list):
    snapshot_path = "/home/zvladimi/MLOIS/particle_data/snapshot_" + str(snap) + "/snapshot_0" + str(snap)
    # get constants from pygadgetreader
    red_shift = readheader(snapshot_path, 'redshift')
    scale_factor = 1/(1+red_shift)
    rho_m = cosmol.rho_m(red_shift)
    hubble_constant = cosmol.Hz(red_shift) * 0.001 # convert to units km/s/kpc

    box_size = readheader(snapshot_path, 'boxsize') #units Mpc/h comoving
    box_size = box_size * 10**3 * scale_factor * little_h #convert to Kpc physical

    if i == 0:
        prim_particles_pid, prim_particles_vel, prim_particles_pos, mass = load_or_pickle_ptl_data(save_location, str(primary_snapshot), snapshot_path, scale_factor, little_h)
        halos_pos, halos_vel, halo_last_snap, halos_r200m, halos_id, halo_status, num_pericenter, tracer_id, n_is_lower_limit, last_pericenter_snap, density_prf_all, density_prf_1halo, halos_last_snap, halos_status, total_num_halos = load_or_pickle_SPARTA_data(save_location, curr_sparta_file, hdf5_file_path, scale_factor, little_h, primary_snapshot)

        t4 = time.time()
        print("\n finish loading data: ", (t4- t3), " seconds")
        #construct a search tree with all of the particle positions
        primary_particle_tree = cKDTree(data = prim_particles_pos, leafsize = 3, balanced_tree = False, boxsize = box_size)
    else:
        comp_particles_pid, comp_particles_vel, comp_particles_pos, mass = load_or_pickle_ptl_data(save_location, str(snap), snapshot_path, scale_factor, little_h)
        comp_halos_pos, comp_halos_vel, comp_halo_last_snap, comp_halos_r200m, comp_halos_id, comp_halo_status, comp_num_pericenter, comp_tracer_id, comp_n_is_lower_limit, comp_last_pericenter_snap, comp_density_prf_all, comp_density_prf_1halo, comp_halos_last_snap, comp_halos_status, comp_total_num_halos = load_or_pickle_SPARTA_data(save_location, curr_sparta_file, hdf5_file_path, scale_factor, little_h, snap)
        comp_particle_tree = cKDTree(data = comp_particles_pos, leafsize = 3, balanced_tree = False, boxsize = box_size)

    split_halo_by_mass(num_bins, halos_status, halos_last_snap, num_save_ptl_params, num_save_halo_params, start_nu, num_iter, nu_step, times_r200, halos_r200m, hdf5_file_path, curr_sparta_file, snapshot_list, True, len(snapshot_list))    
t5 = time.time()
print("finish calculations: ", np.round((t5- t3)/60,2), "minutes,", (t5- t3), " seconds" + "\n")

t2 = time.time()
print("Total time: ", np.round((t2- t1)/60,2), "minutes,", (t2- t1), " seconds")
#plt.savefig("/home/zvladimi/MLOIS/Random_figures/avg_rad_vel_vs_pos.png")

