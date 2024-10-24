import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.ticker import LogLocator, NullFormatter
from utils.data_and_loading_functions import split_orb_inf, timed
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Circle
import shap
plt.rcParams['mathtext.fontset'] = 'dejavuserif'
plt.rcParams['font.family'] = 'serif'

# used to find the location of a number within bins 
def get_bin_loc(bin_edges,search_num):
    # if the search number is at or beyond the bins set it to be the maximum location
    if search_num >= bin_edges[-1]:
        search_loc = bin_edges.size - 1
    else:
        upper_index = np.searchsorted(bin_edges, search_num, side='right')
        lower_index = upper_index - 1

        lower_edge = bin_edges[lower_index]
        upper_edge = bin_edges[upper_index]

        # Interpolate the fractional position of 0 between the two edges
        fraction = (search_num - lower_edge) / (upper_edge - lower_edge)
        search_loc = lower_index + fraction
    
    return search_loc

def gen_ticks(bin_edges,spacing=6):
    ticks = []
    tick_loc = []

    # Add every spacing bin edge
    ticks.extend(bin_edges[::spacing])

    # Ensure the first and last bin edges are included
    ticks.extend([bin_edges[0], bin_edges[-1]])

    tick_loc = np.arange(bin_edges.size)[::spacing].tolist()
    tick_loc.extend([0,bin_edges.size-1])

    zero_loc = get_bin_loc(bin_edges,0)

    # only add the tick if it is noticeably far away from 0
    if zero_loc > 0.05:
        tick_loc.append(zero_loc)
        ticks.append(0)

    # Remove ticks that will get rounded down to 0
    ticks = np.round(ticks,2).tolist()
    rmv_ticks = np.where(ticks == 0)[0]
    if rmv_ticks.size > 0:
        ticks = ticks.pop(rmv_ticks)
        tick_loc = tick_loc.pop(rmv_ticks)

    # Remove duplicates and sort the list
    ticks = sorted(set(ticks))
    tick_loc = sorted(set(tick_loc))
    
    return tick_loc, ticks

# TODO add a configuration dictionary that can be passed instead
def imshow_plot(ax, img, x_label="", y_label="", text="", title="", hide_xticks=False, hide_yticks=False, xticks = None,yticks = None,tick_color="black",xlinthrsh = None, ylinthrsh = None, xlim=None,ylim=None, axisfontsize=28, number = None, return_img=False, kwargs=None):
    if kwargs is None:
        kwargs = {}
    
    ret_img=ax.imshow(img["hist"].T, interpolation="nearest", **kwargs)
    ax.tick_params(axis="both",which="major",length=6,width=2)
    ax.tick_params(axis="both",which="minor",length=4,width=1.5)
    xticks_loc = []
    yticks_loc = []
    
    if xticks is not None:
        for tick in xticks:
            xticks_loc.append(get_bin_loc(img["x_edge"],tick))
        if not hide_xticks:
            ax.set_xticks(xticks_loc,xticks)
            ax.tick_params(axis="x",direction="in")
    if yticks is not None:
        for tick in yticks:
            yticks_loc.append(get_bin_loc(img["y_edge"],tick))
    
        if not hide_yticks:
            ax.set_yticks(yticks_loc,yticks)
            ax.tick_params(axis="y",direction="in")
            
    if xlim is not None:
        min_xloc = get_bin_loc(img["x_edge"],xlim[0])
        max_xloc = get_bin_loc(img["x_edge"],xlim[1])
        ax.set_xlim(min_xloc,max_xloc)
        
    if ylim is not None:
        min_yloc = get_bin_loc(img["y_edge"],ylim[0])
        max_yloc = get_bin_loc(img["y_edge"],ylim[1])
        ax.set_ylim(min_yloc,max_yloc)
        
    if ylinthrsh is not None:
        ylinthrsh_loc = get_bin_loc(img["y_edge"],ylinthrsh)
        ax.axhline(y=ylinthrsh_loc, color='grey', linestyle='--', alpha=1)
        if np.any(np.array(yticks, dtype=np.float32) < 0):
            neg_ylinthrsh_loc = get_bin_loc(img["y_edge"],-ylinthrsh)
            y_zero_loc = get_bin_loc(img["y_edge"],0)
            ax.axhline(y=neg_ylinthrsh_loc, color='grey', linestyle='--', alpha=1)
            ax.axhline(y=y_zero_loc, color='#e6e6fa', linestyle='-.', alpha=1)
    
    if xlinthrsh is not None:
        xlinthrsh_loc = get_bin_loc(img["x_edge"],xlinthrsh)
        ax.axvline(x=xlinthrsh_loc, color='grey', linestyle='--', alpha=1)
        if np.any(np.array(yticks, dtype=np.float32) < 0):
            neg_xlinthrsh_loc = get_bin_loc(img["x_edge"],-xlinthrsh)
            x_zero_loc = get_bin_loc(img["x_edge"],0)
            ax.axvline(x=neg_xlinthrsh_loc, color='grey', linestyle='--', alpha=1)
            ax.axvline(x=x_zero_loc, color='#e6e6fa', linestyle='-.', alpha=1)

    if text != "":
        ax.text(0.01,0.03, text, ha="left", va="bottom", transform=ax.transAxes, fontsize=axisfontsize, bbox={"facecolor":'white',"alpha":0.9,})
    if number is not None:
        ax.text(0.02,0.93,number,ha="left",va="bottom",transform=ax.transAxes,fontsize=axisfontsize,bbox={"facecolor":'white',"alpha":0.9,})
    if title != "":
        ax.set_title(title,fontsize=28)
    if x_label != "":
        ax.set_xlabel(x_label,fontsize=axisfontsize)
    if y_label != "":
        ax.set_ylabel(y_label,fontsize=axisfontsize)
    if hide_xticks:
        ax.tick_params(axis='x', which='both',bottom=False,labelbottom=False)
    else:
        ax.tick_params(axis='x', which='major', labelsize=20,colors=tick_color,labelcolor="black")
        ax.tick_params(axis='x', which='minor', labelsize=18,colors=tick_color,labelcolor="black")
         
    if hide_yticks:
        ax.tick_params(axis='y', which='both',left=False,labelleft=False)
    else:
        ax.tick_params(axis='y', which='major', labelsize=20,colors=tick_color,labelcolor="black")
        ax.tick_params(axis='y', which='minor', labelsize=18,colors=tick_color,labelcolor="black")
           
    if return_img:
        return ret_img

# Uses np.histogram2d to create a histogram and the edges of the histogram in one dictionary
# Can also do a linear binning then a logarithmic binning (similar to symlog) but allows for 
# special case of only positive log and not negative log
def histogram(x,y,use_bins,hist_range,min_ptl,set_ptl,split_xscale_dict=None,split_yscale_dict=None):
    if split_yscale_dict is not None:
        linthrsh = split_yscale_dict["linthrsh"]
        lin_nbin = split_yscale_dict["lin_nbin"]
        log_nbin = split_yscale_dict["log_nbin"]
        
        y_range = hist_range[1]
        # if the y axis goes to the negatives we split the number of log bins in two for pos and neg so there are the same amount of bins as if it was just positive
        if y_range[0] < 0:
            lin_bins = np.linspace(-linthrsh,linthrsh,lin_nbin,endpoint=False)
            neg_log_bins = -np.logspace(np.log10(-y_range[0]),np.log10(linthrsh),int(log_nbin/2),endpoint=False)
            pos_log_bins = np.logspace(np.log10(linthrsh),np.log10(y_range[1]),int(log_nbin/2))
            y_bins = np.concatenate([neg_log_bins,lin_bins,pos_log_bins])
            
        else:
            lin_bins = np.linspace(y_range[0],linthrsh,lin_nbin,endpoint=False)
            pos_log_bins = np.logspace(np.log10(linthrsh),np.log10(y_range[1]),log_nbin)
            y_bins = np.concatenate([lin_bins,pos_log_bins])

        if split_xscale_dict == None:
            use_bins[0] = y_bins.size 
        use_bins[1] = y_bins
        
    if split_xscale_dict is not None:
        linthrsh = split_xscale_dict["linthrsh"]
        lin_nbin = split_xscale_dict["lin_nbin"]
        log_nbin = split_xscale_dict["log_nbin"]
        
        x_range = hist_range[0]
        # if the y axis goes to the negatives
        if x_range[0] < 0:
            lin_bins = np.linspace(-linthrsh,linthrsh,lin_nbin,endpoint=False)
            neg_log_bins = -np.logspace(np.log10(-x_range[0]),np.log10(linthrsh),int(log_nbin/2),endpoint=False)
            pos_log_bins = np.logspace(np.log10(linthrsh),np.log10(x_range[1]),int(log_nbin/2))
            x_bins = np.concatenate([neg_log_bins,lin_bins,pos_log_bins])    
        else:
            lin_bins = np.linspace(x_range[0],linthrsh,lin_nbin,endpoint=False)
            pos_log_bins = np.logspace(np.log10(linthrsh),np.log10(x_range[1]),log_nbin)
            x_bins = np.concatenate([lin_bins,pos_log_bins])

        use_bins[0] = x_bins
        if split_yscale_dict == None:
            use_bins[1] = x_bins.size 

    hist = np.histogram2d(x, y, bins=use_bins, range=hist_range)
    
    fin_hist = {
        "hist":hist[0],
        "x_edge":hist[1],
        "y_edge":hist[2]
    }
    
    fin_hist["hist"][fin_hist["hist"] < min_ptl] = set_ptl
    
    return fin_hist

def scale_hists(inc_hist, act_hist, act_min, inc_min):
    scaled_hist = {
        "x_edge":act_hist["x_edge"],
        "y_edge":act_hist["y_edge"]
    }
    scaled_hist["hist"] = np.divide(inc_hist["hist"],act_hist["hist"],out=np.zeros_like(inc_hist["hist"]), where=act_hist["hist"]!=0)
    
    scaled_hist["hist"] = np.where((inc_hist["hist"] < 1) & (act_hist["hist"] >= act_min), inc_min, scaled_hist["hist"])
    # Where there are miss classified particles but they won't show up on the image, set them to the min
    scaled_hist["hist"] = np.where((inc_hist["hist"] >= 1) & (scaled_hist["hist"] < inc_min) & (act_hist["hist"] >= act_min), inc_min, scaled_hist["hist"])
    
    return scaled_hist

# scale the number of particles so that there are no lines. Plot N / N_tot / dx / dy
def normalize_hists(hist,tot_nptl,min_ptl):
    scaled_hist = {
        "x_edge":hist["x_edge"],
        "y_edge":hist["y_edge"]
    }
    
    dx = np.diff(hist["x_edge"])
    dy = np.diff(hist["y_edge"])

    scaled_hist["hist"] = hist["hist"] / tot_nptl / dx[:,None] / dy[None,:]
    # scale all bins where lower than the min to the min

    scaled_hist["hist"] = np.where((scaled_hist["hist"] < min_ptl) & (scaled_hist["hist"] > 0), min_ptl, scaled_hist["hist"])

    return scaled_hist

def plot_full_ptl_dist(p_corr_labels, p_r, p_rv, p_tv, c_r, c_rv, split_scale_dict, num_bins, save_loc):
    with timed("Finished Full Ptl Dist Plot"):
        print("Starting Full Ptl Dist Plot")
        
        linthrsh = split_scale_dict["linthrsh"]
        log_nbin = split_scale_dict["log_nbin"]
        
        p_r_range = [np.min(p_r),np.max(p_r)]
        p_rv_range = [np.min(p_rv),np.max(p_rv)]
        p_tv_range = [np.min(p_tv),np.max(p_tv)]
        
        act_min_ptl = 10
        set_ptl = 0
        scale_min_ptl = 1e-4
        
        inf_p_r, orb_p_r = split_orb_inf(p_r,p_corr_labels)
        inf_p_rv, orb_p_rv = split_orb_inf(p_rv,p_corr_labels)
        inf_p_tv, orb_p_tv = split_orb_inf(p_tv,p_corr_labels)
        inf_c_r, orb_c_r = split_orb_inf(c_r,p_corr_labels)
        inf_c_rv, orb_c_rv = split_orb_inf(c_rv,p_corr_labels)
        
        # Use the binning from all particles for the orbiting and infalling plots and the secondary snap to keep it consistent
        all_p_r_p_rv = histogram(p_r,p_rv,use_bins=[num_bins,num_bins],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_scale_dict)
        all_p_r_p_tv = histogram(p_r,p_tv,use_bins=[num_bins,num_bins],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_scale_dict)
        all_p_rv_p_tv = histogram(p_rv,p_tv,use_bins=[num_bins,num_bins],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_xscale_dict=split_scale_dict,split_yscale_dict=split_scale_dict)
        all_c_r_c_rv = histogram(c_r,c_rv,use_bins=[all_p_r_p_rv["x_edge"],all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_scale_dict)
        
        inf_p_r_p_rv = histogram(inf_p_r,inf_p_rv,use_bins=[all_p_r_p_rv["x_edge"],all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_scale_dict)
        inf_p_r_p_tv = histogram(inf_p_r,inf_p_tv,use_bins=[all_p_r_p_tv["x_edge"],all_p_r_p_tv["y_edge"]],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_scale_dict)
        inf_p_rv_p_tv = histogram(inf_p_rv,inf_p_tv,use_bins=[all_p_rv_p_tv["x_edge"],all_p_rv_p_tv["y_edge"]],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_xscale_dict=split_scale_dict,split_yscale_dict=split_scale_dict)
        inf_c_r_c_rv = histogram(inf_c_r,inf_c_rv,use_bins=[all_c_r_c_rv["x_edge"],all_c_r_c_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_scale_dict)
        
        orb_p_r_p_rv = histogram(orb_p_r,orb_p_rv,use_bins=[all_p_r_p_rv["x_edge"],all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_scale_dict)
        orb_p_r_p_tv = histogram(orb_p_r,orb_p_tv,use_bins=[all_p_r_p_tv["x_edge"],all_p_r_p_tv["y_edge"]],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_scale_dict)
        orb_p_rv_p_tv = histogram(orb_p_rv,orb_p_tv,use_bins=[all_p_rv_p_tv["x_edge"],all_p_rv_p_tv["y_edge"]],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_xscale_dict=split_scale_dict,split_yscale_dict=split_scale_dict)
        orb_c_r_c_rv = histogram(orb_c_r,orb_c_rv,use_bins=[all_p_r_p_rv["x_edge"],all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_scale_dict)
        
        tot_nptl = p_r.shape[0]
        
        # normalize the number of particles so that there are no lines.
        all_p_r_p_rv = normalize_hists(all_p_r_p_rv,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)
        all_p_r_p_tv = normalize_hists(all_p_r_p_tv,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)
        all_p_rv_p_tv = normalize_hists(all_p_rv_p_tv,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)
        all_c_r_c_rv = normalize_hists(all_c_r_c_rv,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)

        inf_p_r_p_rv = normalize_hists(inf_p_r_p_rv,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)
        inf_p_r_p_tv = normalize_hists(inf_p_r_p_tv,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)
        inf_p_rv_p_tv = normalize_hists(inf_p_rv_p_tv,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)
        inf_c_r_c_rv = normalize_hists(inf_c_r_c_rv,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)

        orb_p_r_p_rv = normalize_hists(orb_p_r_p_rv,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)
        orb_p_r_p_tv = normalize_hists(orb_p_r_p_tv,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)
        orb_p_rv_p_tv = normalize_hists(orb_p_rv_p_tv,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)
        orb_c_r_c_rv = normalize_hists(orb_c_r_c_rv,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)
        
        # Can just do the all particle arrays since inf/orb will have equal or less
        max_ptl = np.max(np.array([np.max(all_p_r_p_rv["hist"]),np.max(all_p_r_p_tv["hist"]),np.max(all_p_rv_p_tv["hist"]),np.max(all_c_r_c_rv["hist"])]))
        
        cividis_cmap = plt.get_cmap("cividis")
        cividis_cmap.set_under(color='black')
        cividis_cmap.set_bad(color='black') 
        
        plot_kwargs = {
                "vmin":scale_min_ptl,
                "vmax":max_ptl,
                "norm":"log",
                "origin":"lower",
                "aspect":"auto",
                "cmap":cividis_cmap,
        }
        
        r_ticks = split_scale_dict["lin_rticks"] + split_scale_dict["log_rticks"]
        
        rv_ticks = split_scale_dict["lin_rvticks"] + split_scale_dict["log_rvticks"]
        rv_ticks = rv_ticks + [-x for x in rv_ticks if x != 0]
        rv_ticks.sort()

        tv_ticks = split_scale_dict["lin_tvticks"] + split_scale_dict["log_tvticks"]       
        
        widths = [4,4,4,4,.5]
        heights = [0.15,4,4,4] # have extra row up top so there is space for the title
        
        fig = plt.figure(constrained_layout=True, figsize=(35,25))
        gs = fig.add_gridspec(len(heights),len(widths),width_ratios = widths, height_ratios = heights, hspace=0, wspace=0)
        
        imshow_plot(fig.add_subplot(gs[1,0]),all_p_r_p_rv,y_label="$v_r/v_{200m}$",text="All Particles",title="Current Snapshot",hide_xticks=True,xticks=r_ticks,yticks=rv_ticks,ylinthrsh=linthrsh,number="D1",kwargs=plot_kwargs)
        imshow_plot(fig.add_subplot(gs[1,1]),all_p_r_p_tv,y_label="$v_t/v_{200m}$",hide_xticks=True,xticks=r_ticks,yticks=tv_ticks,ylinthrsh=linthrsh,number="D2",kwargs=plot_kwargs)
        imshow_plot(fig.add_subplot(gs[1,2]),all_p_rv_p_tv,hide_xticks=True,hide_yticks=True,xticks=rv_ticks,yticks=tv_ticks,xlinthrsh=linthrsh,ylinthrsh=linthrsh,number="D3",kwargs=plot_kwargs)
        imshow_plot(fig.add_subplot(gs[1,3]),all_c_r_c_rv,y_label="$v_r/v_{200m}$",title="Past Snapshot",hide_xticks=True,xticks=r_ticks,yticks=rv_ticks,ylinthrsh=linthrsh,number="D4",kwargs=plot_kwargs)
        
        imshow_plot(fig.add_subplot(gs[2,0]),inf_p_r_p_rv,y_label="$v_r/v_{200m}$",text="Infalling Particles",hide_xticks=True,xticks=r_ticks,yticks=rv_ticks,ylinthrsh=linthrsh,number="D5",kwargs=plot_kwargs)
        imshow_plot(fig.add_subplot(gs[2,1]),inf_p_r_p_tv,y_label="$v_t/v_{200m}$",hide_xticks=True,xticks=r_ticks,yticks=tv_ticks,ylinthrsh=linthrsh,number="D6",kwargs=plot_kwargs)
        imshow_plot(fig.add_subplot(gs[2,2]),inf_p_rv_p_tv,hide_xticks=True,hide_yticks=True,xticks=rv_ticks,yticks=tv_ticks,xlinthrsh=linthrsh,ylinthrsh=linthrsh,number="D7",kwargs=plot_kwargs)
        imshow_plot(fig.add_subplot(gs[2,3]),inf_c_r_c_rv,y_label="$v_r/v_{200m}$",hide_xticks=True,xticks=r_ticks,yticks=rv_ticks,ylinthrsh=linthrsh,number="D8",kwargs=plot_kwargs)
                    
        imshow_plot(fig.add_subplot(gs[3,0]),orb_p_r_p_rv,x_label="$r/R_{200m}$",y_label="$v_r/v_{200m}$",text="Orbiting Particles",xticks=r_ticks,yticks=rv_ticks,ylinthrsh=linthrsh,number="D9",kwargs=plot_kwargs)
        imshow_plot(fig.add_subplot(gs[3,1]),orb_p_r_p_tv,x_label="$r/R_{200m}$",y_label="$v_t/v_{200m}$",xticks=r_ticks,yticks=tv_ticks,ylinthrsh=linthrsh,number="D10",kwargs=plot_kwargs)
        imshow_plot(fig.add_subplot(gs[3,2]),orb_p_rv_p_tv,x_label="$v_r/v_{200m}$",hide_yticks=True,xticks=rv_ticks,yticks=tv_ticks,xlinthrsh=linthrsh,ylinthrsh=linthrsh,number="D11",kwargs=plot_kwargs)
        imshow_plot(fig.add_subplot(gs[3,3]),orb_c_r_c_rv,x_label="$r/R_{200m}$",y_label="$v_r/v_{200m}$",xticks=r_ticks,yticks=rv_ticks,ylinthrsh=linthrsh,number="D12",kwargs=plot_kwargs)

        color_bar = plt.colorbar(mpl.cm.ScalarMappable(norm=mpl.colors.LogNorm(vmin=scale_min_ptl, vmax=max_ptl),cmap=cividis_cmap), cax=plt.subplot(gs[1:,-1]))
        color_bar.set_label(r"$dN / N dx dy$",fontsize=26)
        color_bar.ax.tick_params(which="major",direction="in",labelsize=22,length=10,width=3)
        color_bar.ax.tick_params(which="minor",direction="in",labelsize=22,length=5,width=1.5)
        
        fig.savefig(save_loc + "ptl_distr.png")
        plt.close()

def plot_miss_class_dist(p_corr_labels, p_ml_labels, p_r, p_rv, p_tv, c_r, c_rv, split_scale_dict, num_bins, save_loc, model_info,dataset_name):
    with timed("Finished Miss Class Dist Plot"):
        print("Starting Miss Class Dist Plot")

        linthrsh = split_scale_dict["linthrsh"]
        log_nbin = split_scale_dict["log_nbin"]

        p_r_range = [np.min(p_r),np.max(p_r)]
        p_rv_range = [np.min(p_rv),np.max(p_rv)]
        p_tv_range = [np.min(p_tv),np.max(p_tv)]
        
        inc_min_ptl = 1e-4
        act_min_ptl = 10
        act_set_ptl = 0

        # inc_inf: particles that are actually infalling but labeled as orbiting
        # inc_orb: particles that are actually orbiting but labeled as infalling
        inc_inf = np.where((p_ml_labels == 1) & (p_corr_labels == 0))[0]
        inc_orb = np.where((p_ml_labels == 0) & (p_corr_labels == 1))[0]
        num_inf = np.where(p_corr_labels == 0)[0].shape[0]
        num_orb = np.where(p_corr_labels == 1)[0].shape[0]
        tot_num_inc = inc_orb.shape[0] + inc_inf.shape[0]
        tot_num_ptl = num_orb + num_inf

        missclass_dict = {
            "Total Num of Particles": tot_num_ptl,
            "Num Incorrect Infalling Particles": str(inc_inf.shape[0])+", "+str(np.round(((inc_inf.shape[0]/num_inf)*100),2))+"% of infalling ptls",
            "Num Incorrect Orbiting Particles": str(inc_orb.shape[0])+", "+str(np.round(((inc_orb.shape[0]/num_orb)*100),2))+"% of orbiting ptls",
            "Num Incorrect All Particles": str(tot_num_inc)+", "+str(np.round(((tot_num_inc/tot_num_ptl)*100),2))+"% of all ptls",
        }
        
        if "Results" not in model_info:
            model_info["Results"] = {}
        
        if dataset_name not in model_info["Results"]:
            model_info["Results"][dataset_name]={}
        model_info["Results"][dataset_name]["Primary Snap"] = missclass_dict
        
        inc_inf_p_r = p_r[inc_inf]
        inc_orb_p_r = p_r[inc_orb]
        inc_inf_p_rv = p_rv[inc_inf]
        inc_orb_p_rv = p_rv[inc_orb]
        inc_inf_p_tv = p_tv[inc_inf]
        inc_orb_p_tv = p_tv[inc_orb]
        inc_inf_c_r = c_r[inc_inf]
        inc_orb_c_r = c_r[inc_orb]
        inc_inf_c_rv = c_rv[inc_inf]
        inc_orb_c_rv = c_rv[inc_orb]

        act_inf_p_r, act_orb_p_r = split_orb_inf(p_r, p_corr_labels)
        act_inf_p_rv, act_orb_p_rv = split_orb_inf(p_rv, p_corr_labels)
        act_inf_p_tv, act_orb_p_tv = split_orb_inf(p_tv, p_corr_labels)
        act_inf_c_r, act_orb_c_r = split_orb_inf(c_r, p_corr_labels)
        act_inf_c_rv, act_orb_c_rv = split_orb_inf(c_rv, p_corr_labels)
        
        # Create histograms for all particles and then for the incorrect particles
        # Use the binning from all particles for the orbiting and infalling plots and the secondary snap to keep it consistent
        act_all_p_r_p_rv = histogram(p_r,p_rv,use_bins=[num_bins,num_bins],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)
        act_all_p_r_p_tv = histogram(p_r,p_tv,use_bins=[num_bins,num_bins],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)
        act_all_p_rv_p_tv = histogram(p_rv,p_tv,use_bins=[num_bins,num_bins],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_xscale_dict=split_scale_dict,split_yscale_dict=split_scale_dict)
        act_all_c_r_c_rv = histogram(c_r,c_rv,use_bins=[act_all_p_r_p_rv["x_edge"],act_all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)
        
        act_inf_p_r_p_rv = histogram(act_inf_p_r,act_inf_p_rv,use_bins=[act_all_p_r_p_rv["x_edge"],act_all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)
        act_inf_p_r_p_tv = histogram(act_inf_p_r,act_inf_p_tv,use_bins=[act_all_p_r_p_tv["x_edge"],act_all_p_r_p_tv["y_edge"]],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)
        act_inf_p_rv_p_tv = histogram(act_inf_p_rv,act_inf_p_tv,use_bins=[act_all_p_rv_p_tv["x_edge"],act_all_p_rv_p_tv["y_edge"]],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_xscale_dict=split_scale_dict,split_yscale_dict=split_scale_dict)
        act_inf_c_r_c_rv = histogram(act_inf_c_r,act_inf_c_rv,use_bins=[act_all_c_r_c_rv["x_edge"],act_all_c_r_c_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)
        
        act_orb_p_r_p_rv = histogram(act_orb_p_r,act_orb_p_rv,use_bins=[act_all_p_r_p_rv["x_edge"],act_all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)
        act_orb_p_r_p_tv = histogram(act_orb_p_r,act_orb_p_tv,use_bins=[act_all_p_r_p_tv["x_edge"],act_all_p_r_p_tv["y_edge"]],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)
        act_orb_p_rv_p_tv = histogram(act_orb_p_rv,act_orb_p_tv,use_bins=[act_all_p_rv_p_tv["x_edge"],act_all_p_rv_p_tv["y_edge"]],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_xscale_dict=split_scale_dict,split_yscale_dict=split_scale_dict)
        act_orb_c_r_c_rv = histogram(act_orb_c_r,act_orb_c_rv,use_bins=[act_all_p_r_p_rv["x_edge"],act_all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)
            
        inc_inf_p_r_p_rv = histogram(inc_inf_p_r,inc_inf_p_rv,use_bins=[act_all_p_r_p_rv["x_edge"],act_all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)
        inc_inf_p_r_p_tv = histogram(inc_inf_p_r,inc_inf_p_tv,use_bins=[act_all_p_r_p_tv["x_edge"],act_all_p_r_p_tv["y_edge"]],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)
        inc_inf_p_rv_p_tv = histogram(inc_inf_p_rv,inc_inf_p_tv,use_bins=[act_all_p_rv_p_tv["x_edge"],act_all_p_rv_p_tv["y_edge"]],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_xscale_dict=split_scale_dict,split_yscale_dict=split_scale_dict)
        inc_inf_c_r_c_rv = histogram(inc_inf_c_r,inc_inf_c_rv,use_bins=[act_all_c_r_c_rv["x_edge"],act_all_c_r_c_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)
        
        inc_orb_p_r_p_rv = histogram(inc_orb_p_r,inc_orb_p_rv,use_bins=[act_all_p_r_p_rv["x_edge"],act_all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)
        inc_orb_p_r_p_tv = histogram(inc_orb_p_r,inc_orb_p_tv,use_bins=[act_all_p_r_p_tv["x_edge"],act_all_p_r_p_tv["y_edge"]],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)
        inc_orb_p_rv_p_tv = histogram(inc_orb_p_rv,inc_orb_p_tv,use_bins=[act_all_p_rv_p_tv["x_edge"],act_all_p_rv_p_tv["y_edge"]],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_xscale_dict=split_scale_dict,split_yscale_dict=split_scale_dict)
        inc_orb_c_r_c_rv = histogram(inc_orb_c_r,inc_orb_c_rv,use_bins=[act_all_p_r_p_rv["x_edge"],act_all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_scale_dict)

        
        inc_all_p_r_p_rv = {
            "hist":inc_inf_p_r_p_rv["hist"] + inc_orb_p_r_p_rv["hist"],
            "x_edge":act_all_p_r_p_rv["x_edge"],
            "y_edge":act_all_p_r_p_rv["y_edge"]
        }
        inc_all_p_r_p_tv = {
            "hist":inc_inf_p_r_p_tv["hist"] + inc_orb_p_r_p_tv["hist"],
            "x_edge":act_all_p_r_p_tv["x_edge"],
            "y_edge":act_all_p_r_p_tv["y_edge"]
        }
        inc_all_p_rv_p_tv = {
            "hist":inc_inf_p_rv_p_tv["hist"] + inc_orb_p_rv_p_tv["hist"],
            "x_edge":act_all_p_rv_p_tv["x_edge"],
            "y_edge":act_all_p_rv_p_tv["y_edge"]
        }
        inc_all_c_r_c_rv = {
            "hist":inc_inf_c_r_c_rv["hist"] + inc_orb_c_r_c_rv["hist"],
            "x_edge":act_all_c_r_c_rv["x_edge"],
            "y_edge":act_all_c_r_c_rv["y_edge"]
        }

        scale_inc_all_p_r_p_rv = scale_hists(inc_all_p_r_p_rv,act_all_p_r_p_rv,act_min=act_min_ptl,inc_min=inc_min_ptl)
        scale_inc_all_p_r_p_tv = scale_hists(inc_all_p_r_p_tv,act_all_p_r_p_tv,act_min=act_min_ptl,inc_min=inc_min_ptl)
        scale_inc_all_p_rv_p_tv = scale_hists(inc_all_p_rv_p_tv,act_all_p_rv_p_tv,act_min=act_min_ptl,inc_min=inc_min_ptl)
        scale_inc_all_c_r_c_rv = scale_hists(inc_all_c_r_c_rv,act_all_c_r_c_rv,act_min=act_min_ptl,inc_min=inc_min_ptl)
        
        scale_inc_inf_p_r_p_rv = scale_hists(inc_inf_p_r_p_rv,act_inf_p_r_p_rv,act_min=act_min_ptl,inc_min=inc_min_ptl)
        scale_inc_inf_p_r_p_tv = scale_hists(inc_inf_p_r_p_tv,act_inf_p_r_p_tv,act_min=act_min_ptl,inc_min=inc_min_ptl)
        scale_inc_inf_p_rv_p_tv = scale_hists(inc_inf_p_rv_p_tv,act_inf_p_rv_p_tv,act_min=act_min_ptl,inc_min=inc_min_ptl)
        scale_inc_inf_c_r_c_rv = scale_hists(inc_inf_c_r_c_rv,act_inf_c_r_c_rv,act_min=act_min_ptl,inc_min=inc_min_ptl)
        
        scale_inc_orb_p_r_p_rv = scale_hists(inc_orb_p_r_p_rv,act_orb_p_r_p_rv,act_min=act_min_ptl,inc_min=inc_min_ptl)
        scale_inc_orb_p_r_p_tv = scale_hists(inc_orb_p_r_p_tv,act_orb_p_r_p_tv,act_min=act_min_ptl,inc_min=inc_min_ptl)
        scale_inc_orb_p_rv_p_tv = scale_hists(inc_orb_p_rv_p_tv,act_orb_p_rv_p_tv,act_min=act_min_ptl,inc_min=inc_min_ptl)
        scale_inc_orb_c_r_c_rv = scale_hists(inc_orb_c_r_c_rv,act_orb_c_r_c_rv,act_min=act_min_ptl,inc_min=inc_min_ptl)
        
        magma_cmap = plt.get_cmap("magma")
        magma_cmap = LinearSegmentedColormap.from_list('magma_truncated', magma_cmap(np.linspace(0.15, 1, 256)))
        magma_cmap.set_under(color='black')
        magma_cmap.set_bad(color='black')
        
        
        scale_miss_class_args = {
                "vmin":inc_min_ptl,
                "vmax":1,
                "norm":"log",
                "origin":"lower",
                "aspect":"auto",
                "cmap":magma_cmap,
        }
        
        r_ticks = split_scale_dict["lin_rticks"] + split_scale_dict["log_rticks"]
        
        rv_ticks = split_scale_dict["lin_rvticks"] + split_scale_dict["log_rvticks"]
        rv_ticks = rv_ticks + [-x for x in rv_ticks if x != 0]
        rv_ticks.sort()

        tv_ticks = split_scale_dict["lin_tvticks"] + split_scale_dict["log_tvticks"]     
        
        widths = [4,4,4,4,.5]
        heights = [0.12,4,4,4]
        
        fig = plt.figure(constrained_layout=True,figsize=(35,25))
        gs = fig.add_gridspec(len(heights),len(widths),width_ratios = widths, height_ratios = heights, hspace=0, wspace=0)

        imshow_plot(fig.add_subplot(gs[1,0]),scale_inc_all_p_r_p_rv,y_label="$v_r/v_{200m}$",hide_xticks=True,text="All Misclassified",xticks=r_ticks,yticks=rv_ticks,ylinthrsh=linthrsh,number="S1",kwargs=scale_miss_class_args, title="Current Snapshot")
        imshow_plot(fig.add_subplot(gs[1,1]),scale_inc_all_p_r_p_tv,y_label="$v_t/v_{200m}$",hide_xticks=True,xticks=r_ticks,yticks=tv_ticks,ylinthrsh=linthrsh,number="S2",kwargs=scale_miss_class_args)
        imshow_plot(fig.add_subplot(gs[1,2]),scale_inc_all_p_rv_p_tv,hide_xticks=True,hide_yticks=True,xticks=rv_ticks,yticks=tv_ticks,xlinthrsh=linthrsh,ylinthrsh=linthrsh,number="S3",kwargs=scale_miss_class_args)
        imshow_plot(fig.add_subplot(gs[1,3]),scale_inc_all_c_r_c_rv,y_label="$v_r/v_{200m}$",hide_xticks=True,xticks=r_ticks,yticks=rv_ticks,ylinthrsh=linthrsh,number="S4",kwargs=scale_miss_class_args, title="Past Snapshot")

        imshow_plot(fig.add_subplot(gs[2,0]),scale_inc_inf_p_r_p_rv,hide_xticks=True,y_label="$v_r/v_{200m}$",text="Label: Orbit\nReal: Infall",xticks=r_ticks,yticks=rv_ticks,ylinthrsh=linthrsh,number="S5",kwargs=scale_miss_class_args)
        imshow_plot(fig.add_subplot(gs[2,1]),scale_inc_inf_p_r_p_tv,y_label="$v_t/v_{200m}$",hide_xticks=True,xticks=r_ticks,yticks=tv_ticks,ylinthrsh=linthrsh,number="S6",kwargs=scale_miss_class_args)
        imshow_plot(fig.add_subplot(gs[2,2]),scale_inc_inf_p_rv_p_tv,hide_xticks=True,hide_yticks=True,xticks=rv_ticks,yticks=tv_ticks,xlinthrsh=linthrsh,ylinthrsh=linthrsh,number="S7",kwargs=scale_miss_class_args)
        imshow_plot(fig.add_subplot(gs[2,3]),scale_inc_inf_c_r_c_rv,y_label="$v_r/v_{200m}$",hide_xticks=True,xticks=r_ticks,yticks=rv_ticks,ylinthrsh=linthrsh,number="S8",kwargs=scale_miss_class_args)
        
        imshow_plot(fig.add_subplot(gs[3,0]),scale_inc_orb_p_r_p_rv,x_label="$r/R_{200m}$",y_label="$v_r/v_{200m}$",text="Label: Infall\nReal: Orbit",xticks=r_ticks,yticks=rv_ticks,ylinthrsh=linthrsh,number="S9",kwargs=scale_miss_class_args)
        imshow_plot(fig.add_subplot(gs[3,1]),scale_inc_orb_p_r_p_tv,x_label="$r/R_{200m}$",y_label="$v_t/v_{200m}$",xticks=r_ticks,yticks=tv_ticks,ylinthrsh=linthrsh,number="S10",kwargs=scale_miss_class_args)
        imshow_plot(fig.add_subplot(gs[3,2]),scale_inc_orb_p_rv_p_tv,x_label="$v_r/v_{200m}$",hide_yticks=True,xticks=rv_ticks,yticks=tv_ticks,xlinthrsh=linthrsh,ylinthrsh=linthrsh,number="S11",kwargs=scale_miss_class_args)
        imshow_plot(fig.add_subplot(gs[3,3]),scale_inc_orb_c_r_c_rv,x_label="$r/R_{200m}$",y_label="$v_r/v_{200m}$",xticks=r_ticks,yticks=rv_ticks,ylinthrsh=linthrsh,number="S12",kwargs=scale_miss_class_args)
        
        color_bar = plt.colorbar(mpl.cm.ScalarMappable(norm=mpl.colors.LogNorm(vmin=inc_min_ptl, vmax=1),cmap=magma_cmap), cax=plt.subplot(gs[1:,-1]))
        color_bar.set_label(r"$N_{\mathrm{bin, inc}} / N_{\mathrm{bin, tot}}$",fontsize=26)
        color_bar.ax.tick_params(which="major",direction="in",labelsize=22,length=10,width=3)
        color_bar.ax.tick_params(which="minor",direction="in",labelsize=22,length=5,width=1.5)
        
        fig.savefig(save_loc + "scaled_miss_class.png")
        plt.close()

def plot_perr_err():
    return

def plot_log_vel(phys_vel,radii,labels,save_loc,add_line=[None,None],show_v200m=False,v200m=1.5):
    if v200m == -1:
        title = "no_cut"
    else:
        title = str(v200m) + "v200m"
    log_phys_vel = np.log10(phys_vel)
    
    orb_loc = np.where(labels == 1)[0]
    inf_loc = np.where(labels == 0)[0]
    
    r_range = [0,np.max(radii)]
    pv_range = [np.min(log_phys_vel),np.max(log_phys_vel)]
    
    num_bins = 500
    min_ptl = 10
    set_ptl = 0
    scale_min_ptl = 1e-4
    
    all = histogram(radii,log_phys_vel,use_bins=[num_bins,num_bins],hist_range=[r_range,pv_range],min_ptl=min_ptl,set_ptl=set_ptl)
    inf = histogram(radii[inf_loc],log_phys_vel[inf_loc],use_bins=[num_bins,num_bins],hist_range=[r_range,pv_range],min_ptl=min_ptl,set_ptl=set_ptl)
    orb = histogram(radii[orb_loc],log_phys_vel[orb_loc],use_bins=[num_bins,num_bins],hist_range=[r_range,pv_range],min_ptl=min_ptl,set_ptl=set_ptl)
    
    tot_nptl = radii.shape[0]
    
    all = normalize_hists(all,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)
    inf = normalize_hists(inf,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)
    orb = normalize_hists(orb,tot_nptl=tot_nptl,min_ptl=scale_min_ptl)
    
    # Can just do the all particle arrays since inf/orb will have equal or less
    max_ptl = np.max(np.array([np.max(all["hist"]),np.max(inf["hist"]),np.max(orb["hist"])]))
    
    magma_cmap = plt.get_cmap("magma")
    magma_cmap = LinearSegmentedColormap.from_list('magma_truncated', magma_cmap(np.linspace(0.15, 1, 256)))
    magma_cmap.set_under(color='black')
    magma_cmap.set_bad(color='black')
    
    lin_plot_kwargs = {
            "vmin":scale_min_ptl,
            "vmax":max_ptl,
            "norm":"linear",
            "origin":"lower",
            "aspect":"auto",
            "cmap":magma_cmap,
    }
    
    rticks = [0,0.5,1,2,3]
    pv_ticks = [-2,-1,0,1,2]
    
    widths = [4,4,4,.5]
    heights = [4]
    
    fig = plt.figure(constrained_layout=True, figsize=(25,10))
    if show_v200m:
        fig.suptitle(title,fontsize=32)
    gs = fig.add_gridspec(len(heights),len(widths),width_ratios = widths, height_ratios = heights, hspace=0, wspace=0)
    
    ax1 = fig.add_subplot(gs[0,0])
    ax2 = fig.add_subplot(gs[0,1])
    ax3 = fig.add_subplot(gs[0,2])
    
    imshow_plot(ax1,all,x_label="$r/R_{200}$",xticks=rticks,yticks=pv_ticks,y_label="$log_{10}(v_{phys}/v_{200m})$",ylim=[-3,2],title="All Particles",tick_color="white",axisfontsize=22,kwargs=lin_plot_kwargs)
    imshow_plot(ax2,inf,x_label="$r/R_{200}$",xticks=rticks,hide_yticks=True,ylim=[-3,2],title="Infalling Particles",tick_color="white",axisfontsize=22,kwargs=lin_plot_kwargs)
    imshow_plot(ax3,orb,x_label="$r/R_{200}$",xticks=rticks,hide_yticks=True,ylim=[-3,2],title="Orbiting Particles",tick_color="white",axisfontsize=22,kwargs=lin_plot_kwargs)

    if v200m > 0 and show_v200m:
        ax1.hlines(np.log10(v200m),xmin=r_range[0],xmax=r_range[1],colors="black")
        ax2.hlines(np.log10(v200m),xmin=r_range[0],xmax=r_range[1],colors="black")
        ax3.hlines(np.log10(v200m),xmin=r_range[0],xmax=r_range[1],colors="black")
    
    
    line_xloc = []
    line_yloc = []
    if add_line[0] is not None:
        line_xloc.append(get_bin_loc(all["x_edge"],radii.iloc[0]))
        line_xloc.append(get_bin_loc(all["x_edge"],radii.iloc[-1]))
        line_yloc.append(get_bin_loc(all["y_edge"],add_line[0] * radii.iloc[0] + add_line[1]))
        line_yloc.append(get_bin_loc(all["y_edge"],add_line[0] * radii.iloc[-1] + add_line[1]))
        ax1.plot(line_xloc, line_yloc,color="white",label=f"m={add_line[0]}\nb={add_line[1]}")    
        ax2.plot(line_xloc, line_yloc,color="white")    
        ax3.plot(line_xloc, line_yloc,color="white")    
        
        ax1.legend(fontsize=16)
        

    lin_color_bar = plt.colorbar(mpl.cm.ScalarMappable(norm=mpl.colors.Normalize(vmin=scale_min_ptl, vmax=max_ptl),cmap=magma_cmap), cax=plt.subplot(gs[0,-1]))
    lin_color_bar.set_label(r"$dN / N dx dy$",fontsize=22)
    lin_color_bar.ax.tick_params(which="major",direction="in",labelsize=18,length=10,width=3)
    lin_color_bar.ax.tick_params(which="minor",direction="in",labelsize=18,length=5,width=1.5)
    
    fig.savefig(save_loc + "log_phys_vel_" + title + ".png")
    

    line_y = add_line[0] * radii + add_line[1]
    line_preds = np.zeros(radii.size) 
    line_preds[log_phys_vel <= line_y] = 1

    labels_np = labels["Orbit_infall"].values
    
    num_inc_inf = np.where((line_preds == 1) & (labels_np == 0))[0].shape[0]
    num_inc_orb = np.where((line_preds == 0) & (labels_np == 1))[0].shape[0]
    num_inf = np.where(labels_np == 0)[0].shape[0]
    num_orb = np.where(labels_np == 1)[0].shape[0]
    tot_num_inc = num_inc_orb + num_inc_inf
    tot_num_ptl = num_orb + num_inf


    print("Total Num of Particles", tot_num_ptl)
    print("Num Incorrect Infalling Particles", str(num_inc_inf)+", "+str(np.round(((num_inc_inf/num_inf)*100),2))+"% of infalling ptls")
    print("Num Incorrect Orbiting Particles", str(num_inc_orb)+", "+str(np.round(((num_inc_orb/num_orb)*100),2))+"% of orbiting ptls")
    print("Num Incorrect All Particles", str(tot_num_inc)+", "+str(np.round(((tot_num_inc/tot_num_ptl)*100),2))+"% of all ptls")
        
def plot_halo_slice(ptl_pos,labels,halo_pos,halo_r200m,search_rad,save_loc,title=""):
    cividis_cmap = plt.get_cmap("cividis")
    cividis_cmap.set_under(color='black')
    cividis_cmap.set_bad(color='black') 
    
    ptl_pos[:,0] = ptl_pos[:,0] - halo_pos[0]
    ptl_pos[:,1] = ptl_pos[:,1] - halo_pos[1]
    
    xlim = np.max(np.abs(ptl_pos[:,0]))
    ylim = np.max(np.abs(ptl_pos[:,1]))
    nbins = 250
    
    hist = np.histogram2d(ptl_pos[:,0],ptl_pos[:,1],bins=nbins,range=[[-xlim,xlim],[-ylim,ylim]])
    max_ptl = np.max(hist[0])
    
    search_circle_0 = Circle((0,0),radius=search_rad*halo_r200m,edgecolor="yellow",facecolor='none',linestyle="--",fill=False,label="Search radius: 4R200m")
    search_circle_1 = Circle((0,0),radius=search_rad*halo_r200m,edgecolor="yellow",facecolor='none',linestyle="--",fill=False,label="Search radius: 4R200m")
    search_circle_2 = Circle((0,0),radius=search_rad*halo_r200m,edgecolor="yellow",facecolor='none',linestyle="--",fill=False,label="Search radius: 4R200m")
    
    r200m_circle_0 = Circle((0,0),radius=halo_r200m,edgecolor="white",facecolor='none',linestyle="--",fill=False,label="R200m")
    r200m_circle_1 = Circle((0,0),radius=halo_r200m,edgecolor="white",facecolor='none',linestyle="--",fill=False,label="R200m")
    r200m_circle_2 = Circle((0,0),radius=halo_r200m,edgecolor="white",facecolor='none',linestyle="--",fill=False,label="R200m")
    
    axisfontsize = 18
    titlefontsize = 22
    legendfontsize = 14
    tickfontsize = 14
    
    fig, ax = plt.subplots(1,3,figsize=(30,10),constrained_layout=True)
    ax[0].hist2d(ptl_pos[:,0],ptl_pos[:,1],bins=nbins,vmax=max_ptl,range=[[-xlim,xlim],[-ylim,ylim]],cmap=cividis_cmap)
    ax[0].add_patch(search_circle_0)
    ax[0].add_patch(r200m_circle_0)
    ax[0].set_xlabel(r"$x [h^{-1}kpc]$",fontsize=axisfontsize)
    ax[0].set_ylabel(r"$y [h^{-1}kpc]$",fontsize=axisfontsize)
    ax[0].set_title("All Particles",fontsize=titlefontsize)
    ax[0].tick_params(axis='x', which='major', labelsize=tickfontsize)
    ax[0].tick_params(axis='y', which='major', labelsize=tickfontsize)
    ax[0].legend(fontsize=legendfontsize)
    
    ax[1].hist2d(ptl_pos[np.where(labels==1)[0],0],ptl_pos[np.where(labels==1)[0],1],bins=nbins,vmax=max_ptl,range=[[-xlim,xlim],[-ylim,ylim]],cmap=cividis_cmap)
    ax[1].add_patch(search_circle_1)
    ax[1].add_patch(r200m_circle_1)
    ax[1].set_xlabel(r"$x [h^{-1}kpc]$",fontsize=axisfontsize)
    ax[1].set_title("Orbiting Particles",fontsize=titlefontsize)
    ax[1].tick_params(axis='x', which='major', labelsize=tickfontsize)
    ax[1].tick_params(axis='y', which='both',left=False,labelleft=False)
    ax[1].legend(fontsize=legendfontsize)
    
    ax[2].hist2d(ptl_pos[np.where(labels==0)[0],0],ptl_pos[np.where(labels==0)[0],1],bins=nbins,vmax=max_ptl,range=[[-xlim,xlim],[-ylim,ylim]],cmap=cividis_cmap)
    ax[2].add_patch(search_circle_2)
    ax[2].add_patch(r200m_circle_2)
    ax[2].set_xlabel(r"$x [h^{-1}kpc]$",fontsize=axisfontsize)
    ax[2].set_title("Infalling Particles",fontsize=titlefontsize)
    ax[2].tick_params(axis='x', which='major', labelsize=tickfontsize)
    ax[2].tick_params(axis='y', which='both',left=False,labelleft=False)
    ax[2].legend(fontsize=legendfontsize)
    
    fig.savefig(save_loc+title+"halo_dist.png")
    