import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from utils.data_and_loading_functions import split_orb_inf

def phase_plot(ax, x, y, min_ptl, max_ptl, range, num_bins, cmap, x_label="", y_label="", norm = "log", xrange=None, yrange=None, split_yscale_dict = None, hide_xticks=False, hide_yticks=False,text="", axisfontsize=20, title=""):
    bins = [num_bins,num_bins]
    if split_yscale_dict != None:
        linthrsh = split_yscale_dict["linthrsh"]
        lin_nbin = split_yscale_dict["lin_nbin"]
        log_nbin = split_yscale_dict["log_nbin"]
        
        x_range = range[0]
        y_range = range[1]
        use_yrange = y_range
        # if the y axis goes to the negatives
        if y_range[0] < 0:
            # keep the plot symmetric around 0
            if y_range[0] > y_range[1]:
                use_yrange[1] = -y_range[0]
            elif y_range[1] > y_range[0]:
                use_yrange[0] = -y_range[1]
            
            lin_bins = np.linspace(-linthrsh,linthrsh,lin_nbin,endpoint=False)
            neg_log_bins = -np.logspace(np.log10(-use_yrange[0]),np.log10(linthrsh),log_nbin,endpoint=False)
            pos_log_bins = np.logspace(np.log10(linthrsh),np.log10(use_yrange[1]),log_nbin)
            y_bins = np.concatenate([neg_log_bins,lin_bins,pos_log_bins])            
            
            bins = [num_bins,y_bins]
            
            ax.hist2d(x[np.where((y >= -linthrsh) & (y <= linthrsh))], y[np.where((y >= -linthrsh) & (y <= linthrsh))], bins=bins, density=False, weights=None, cmin=min_ptl, cmap=cmap, norm=norm, vmin=min_ptl, vmax=max_ptl)
            ax.set_yscale('linear')
            ax.set_ylim(-linthrsh,linthrsh)
            ax.set_xlim(x_range[0],x_range[1])
            ax.spines[["bottom","top"]].set_visible(False)
            ax.get_xaxis().set_visible(False)
            
            divider = make_axes_locatable(ax)
            axposlog = divider.append_axes("top", size="100%", pad=0, sharex=ax)
            axposlog.hist2d(x[np.where(y >= linthrsh)[0]], y[np.where(y >= linthrsh)[0]], bins=bins, density=False, weights=None, cmin=min_ptl, cmap=cmap, norm=norm, vmin=min_ptl, vmax=max_ptl)
            axposlog.set_yscale('symlog',linthresh=linthrsh)
            axposlog.set_ylim((linthrsh,use_yrange[1]))
            axposlog.set_xlim(x_range[0],x_range[1])
            axposlog.spines[["bottom"]].set_visible(False)
            axposlog.get_xaxis().set_visible(False)
            
            axneglog = divider.append_axes("bottom", size="100%", pad=0, sharex=ax)            
            axneglog.hist2d(x[np.where(y < -linthrsh)[0]], y[np.where(y < -linthrsh)[0]], bins=bins, density=False, weights=None, cmin=min_ptl, cmap=cmap, norm=norm, vmin=min_ptl, vmax=max_ptl)
            axneglog.set_yscale('symlog',linthresh=linthrsh)
            axneglog.set_ylim((use_yrange[0],-linthrsh))
            axneglog.set_xlim(x_range[0],x_range[1])
            axneglog.spines[["top"]].set_visible(False)
            
        else:
            lin_bins = np.linspace(use_yrange[0],linthrsh,lin_nbin,endpoint=False)
            pos_log_bins = np.logspace(np.log10(linthrsh),np.log10(use_yrange[1]),log_nbin)
            y_bins = np.concatenate([lin_bins,pos_log_bins])
            
            bins = [num_bins,y_bins]
            
            ax.hist2d(x[np.where((y <= linthrsh))], y[np.where(y <= linthrsh)], bins=bins, density=False, weights=None, cmin=min_ptl, cmap=cmap, norm=norm, vmin=min_ptl, vmax=max_ptl)
            ax.set_yscale('linear')
            ax.set_ylim(0,linthrsh)
            ax.set_xlim(x_range[0],x_range[1])
            ax.spines[["top"]].set_visible(False)
            
            divider = make_axes_locatable(ax)
            axposlog = divider.append_axes("top", size="100%", pad=0, sharex=ax)
            axposlog.hist2d(x[np.where(y >= linthrsh)[0]], y[np.where(y >= linthrsh)[0]], bins=bins, density=False, weights=None, cmin=min_ptl, cmap=cmap, norm=norm, vmin=min_ptl, vmax=max_ptl)
            axposlog.set_yscale('symlog',linthresh=linthrsh)
            axposlog.set_ylim((linthrsh,use_yrange[1]))
            axposlog.set_xlim(x_range[0],x_range[1])
            axposlog.spines[["bottom"]].set_visible(False)
            axposlog.get_xaxis().set_visible(False)
    else:
        ax.hist2d(x, y, bins=bins, range=range, density=False, weights=None, cmin=min_ptl, cmap=cmap, norm=norm, vmin=min_ptl, vmax=max_ptl)
    
    if text != "":
        if split_yscale_dict != None and y_range[0] < 0:
            axneglog.text(.01,.03, text, ha="left", va="bottom", transform=axneglog.transAxes, fontsize=18, bbox={"facecolor":'white',"alpha":.9,})
        else:
            ax.text(.01,.03, text, ha="left", va="bottom", transform=ax.transAxes, fontsize=18, bbox={"facecolor":'white',"alpha":.9,})
    if title != "":
        if split_yscale_dict != None:
            axposlog.set_title(title,fontsize=24)
        else:
            ax.set_title(title,fontsize=24)
    if x_label != "":
        if split_yscale_dict != None and y_range[0] < 0:
            axneglog.set_xlabel(x_label,fontsize=axisfontsize)
        else:
            ax.set_xlabel(x_label,fontsize=axisfontsize)
    if y_label != "":
        ax.set_ylabel(y_label,fontsize=axisfontsize)
    if hide_xticks:
        if split_yscale_dict != None and y_range[0] < 0:
            ax.tick_params(axis='x', which='both',bottom=False,labelbottom=False)
            axposlog.tick_params(axis='x', which='both',bottom=False,labelbottom=False)
            axneglog.tick_params(axis='x', which='both',bottom=False,labelbottom=False)
        elif split_yscale_dict != None and y_range[0] >= 0:
            ax.tick_params(axis='x', which='both',bottom=False,labelbottom=False)
            axposlog.tick_params(axis='x', which='both',bottom=False,labelbottom=False)
        else:
            ax.tick_params(axis='x', which='both',bottom=False,labelbottom=False) 
    else:
        if split_yscale_dict != None and y_range[0] < 0:
            ax.tick_params(axis='x', which='major', labelsize=16)
            ax.tick_params(axis='x', which='minor', labelsize=14)
            axposlog.tick_params(axis='x', which='major', labelsize=16)
            axposlog.tick_params(axis='x', which='minor', labelsize=14)
            axneglog.tick_params(axis='x', which='major', labelsize=16)
            axneglog.tick_params(axis='x', which='minor', labelsize=14) 
        elif split_yscale_dict != None and y_range[0] >= 0:
            ax.tick_params(axis='x', which='major', labelsize=16)
            ax.tick_params(axis='x', which='minor', labelsize=14)
            axposlog.tick_params(axis='x', which='major', labelsize=16)
            axposlog.tick_params(axis='x', which='minor', labelsize=14)
        else:
            ax.tick_params(axis='x', which='major', labelsize=16)
            ax.tick_params(axis='x', which='minor', labelsize=14)

    if hide_yticks:
        if split_yscale_dict != None and y_range[0] < 0:
            ax.tick_params(axis='y', which='both',left=False,labelleft=False) 
            axposlog.tick_params(axis='y', which='both',left=False,labelleft=False) 
            axneglog.tick_params(axis='y', which='both',left=False,labelleft=False) 
        elif split_yscale_dict != None and y_range[0] >= 0:
            ax.tick_params(axis='y', which='both',left=False,labelleft=False) 
            axposlog.tick_params(axis='y', which='both',left=False,labelleft=False) 
        else:
            ax.tick_params(axis='y', which='both',left=False,labelleft=False) 
    else:
        if split_yscale_dict != None and y_range[0] < 0:
            ax.tick_params(axis='y', which='major', labelsize=16)
            ax.tick_params(axis='y', which='minor', labelsize=14)
            axposlog.tick_params(axis='y', which='major', labelsize=16)
            axposlog.tick_params(axis='y', which='minor', labelsize=14)
            axneglog.tick_params(axis='y', which='major', labelsize=16)
            axneglog.tick_params(axis='y', which='minor', labelsize=14) 
        elif split_yscale_dict != None and y_range[0] >= 0:
            ax.tick_params(axis='y', which='major', labelsize=16)
            ax.tick_params(axis='y', which='minor', labelsize=14)
            axposlog.tick_params(axis='y', which='major', labelsize=16)
            axposlog.tick_params(axis='y', which='minor', labelsize=14)
        else:
            ax.tick_params(axis='y', which='major', labelsize=16)
            ax.tick_params(axis='y', which='minor', labelsize=14)

def gen_ticks(bin_edges,spacing=5):
    ticks = []

    # Include 0 if it is within the range of bin edges
    if bin_edges.min() <= 0 <= bin_edges.max():
        ticks.append(0)

    # Add every 2nd bin edge
    ticks.extend(bin_edges[::spacing])

    # Ensure the first and last bin edges are included
    ticks.extend([bin_edges[0], bin_edges[-1]])

    # Remove duplicates and sort the list
    ticks = sorted(set(ticks))

    return np.round(ticks,2)

def imshow_plot(ax, img, extent, x_label="", y_label="", text="", title="", hide_xticks=False, hide_yticks=False, axisfontsize=20, return_img=False, kwargs={}):
    ret_img=ax.imshow(img["hist"].T, interpolation="none", extent = extent, **kwargs)
    xticks = gen_ticks(img["x_edge"],spacing=6)
    yticks = gen_ticks(img["y_edge"])
    
    ax.set_xticks(xticks)
    ax.set_yticks(yticks)
    ax.set_xticklabels(ax.get_xticks(), rotation=90)    
    
    if text != "":
        ax.text(.01,.03, text, ha="left", va="bottom", transform=ax.transAxes, fontsize=18, bbox={"facecolor":'white',"alpha":0.9,})
        
    if title != "":
        ax.set_title(title,fontsize=24)
    if x_label != "":
        ax.set_xlabel(x_label,fontsize=axisfontsize)
    if y_label != "":
        ax.set_ylabel(y_label,fontsize=axisfontsize)
    if hide_xticks:
        ax.tick_params(axis='x', which='both',bottom=False,labelbottom=False)
    else:
        ax.tick_params(axis='x', which='major', labelsize=16)
        ax.tick_params(axis='x', which='minor', labelsize=14)
         
    if hide_yticks:
        ax.tick_params(axis='y', which='both',left=False,labelleft=False)
    else:
        ax.tick_params(axis='y', which='major', labelsize=16)
        ax.tick_params(axis='y', which='minor', labelsize=14)
           
    if return_img:
        return ret_img

# Uses np.histogram2d to create a histogram and the edges of the histogram in one dictionary
# Can also do a linear binning then a logarithmic binning (similar to symlog) but allows for 
# special case of only positive log and not negative log
def histogram(x,y,use_bins,hist_range,min_ptl,set_ptl,split_yscale_dict=None):
    if split_yscale_dict != None:
        linthrsh = split_yscale_dict["linthrsh"]
        lin_nbin = split_yscale_dict["lin_nbin"]
        log_nbin = split_yscale_dict["log_nbin"]
        
        y_range = hist_range[1]
        # if the y axis goes to the negatives
        if y_range[0] < 0:
            lin_bins = np.linspace(-linthrsh,linthrsh,lin_nbin,endpoint=False)
            neg_log_bins = -np.logspace(np.log10(-y_range[0]),np.log10(linthrsh),log_nbin,endpoint=False)
            pos_log_bins = np.logspace(np.log10(linthrsh),np.log10(y_range[1]),log_nbin)
            y_bins = np.concatenate([neg_log_bins,lin_bins,pos_log_bins])
            
        else:
            lin_bins = np.linspace(y_range[0],linthrsh,lin_nbin,endpoint=False)
            pos_log_bins = np.logspace(np.log10(linthrsh),np.log10(y_range[1]),log_nbin)
            y_bins = np.concatenate([lin_bins,pos_log_bins])

        use_bins[1] = y_bins
    
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

def plot_full_ptl_dist(p_corr_labels, p_r, p_rv, p_tv, c_r, c_rv, num_bins, save_loc):
    split_yscale_dict = {
        "linthrsh":2, 
        "lin_nbin":30,
        "log_nbin":15,
    }
    
    p_r_range = [np.min(p_r),np.max(p_r)]
    p_rv_range = [np.min(p_rv),np.max(p_rv)]
    p_tv_range = [np.min(p_tv),np.max(p_tv)]
    
    act_min_ptl = 10
    set_ptl = 0
    
    inf_p_r, orb_p_r = split_orb_inf(p_r,p_corr_labels)
    inf_p_rv, orb_p_rv = split_orb_inf(p_rv,p_corr_labels)
    inf_p_tv, orb_p_tv = split_orb_inf(p_tv,p_corr_labels)
    inf_c_r, orb_c_r = split_orb_inf(c_r,p_corr_labels)
    inf_c_rv, orb_c_rv = split_orb_inf(c_rv,p_corr_labels)
    
    # Use the binning from all particles for the orbiting and infalling plots and the secondary snap to keep it consistent
    all_p_r_p_rv = histogram(p_r,p_rv,use_bins=[num_bins,num_bins],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_yscale_dict)
    all_p_r_p_tv = histogram(p_r,p_tv,use_bins=[num_bins,num_bins],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_yscale_dict)
    all_p_rv_p_tv = histogram(p_rv,p_tv,use_bins=[num_bins,num_bins],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_yscale_dict)
    all_c_r_c_rv = histogram(c_r,c_rv,use_bins=[all_p_r_p_rv["x_edge"],all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_yscale_dict)
    
    inf_p_r_p_rv = histogram(inf_p_r,inf_p_rv,use_bins=[all_p_r_p_rv["x_edge"],all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_yscale_dict)
    inf_p_r_p_tv = histogram(inf_p_r,inf_p_tv,use_bins=[all_p_r_p_tv["x_edge"],all_p_r_p_tv["y_edge"]],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_yscale_dict)
    inf_p_rv_p_tv = histogram(inf_p_rv,inf_p_tv,use_bins=[all_p_rv_p_tv["x_edge"],all_p_rv_p_tv["y_edge"]],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_yscale_dict)
    inf_c_r_c_rv = histogram(inf_c_r,inf_c_rv,use_bins=[all_c_r_c_rv["x_edge"],all_c_r_c_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_yscale_dict)
    
    orb_p_r_p_rv = histogram(orb_p_r,orb_p_rv,use_bins=[all_p_r_p_rv["x_edge"],all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_yscale_dict)
    orb_p_r_p_tv = histogram(orb_p_r,orb_p_tv,use_bins=[all_p_r_p_tv["x_edge"],all_p_r_p_tv["y_edge"]],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_yscale_dict)
    orb_p_rv_p_tv = histogram(orb_p_rv,orb_p_tv,use_bins=[all_p_rv_p_tv["x_edge"],all_p_rv_p_tv["y_edge"]],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_yscale_dict)
    orb_c_r_c_rv = histogram(orb_c_r,orb_c_rv,use_bins=[all_p_r_p_rv["x_edge"],all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=set_ptl,split_yscale_dict=split_yscale_dict)
    
    # Can just do the all particle arrays since inf/orb will have equal or less
    max_ptl = np.max(np.array([np.max(all_p_r_p_rv["hist"]),np.max(all_p_r_p_tv["hist"]),np.max(all_p_rv_p_tv["hist"])]))
    
    cividis_cmap = plt.get_cmap("cividis_r")
    cividis_cmap.set_under(color='white')  
    
    plot_kwargs = {
            "vmin":act_min_ptl,
            "vmax":max_ptl,
            "norm":"log",
            "origin":"lower",
            "aspect":"auto",
            "cmap":cividis_cmap,
    }
    
    widths = [4,4,4,4,.5]
    heights = [0.15,4,4,4] # have extra row up top so there is space for the title
    
    fig = plt.figure(constrained_layout=True, figsize=(30,25))
    gs = fig.add_gridspec(len(heights),len(widths),width_ratios = widths, height_ratios = heights, hspace=0, wspace=0)
    
    imshow_plot(fig.add_subplot(gs[1,0]),all_p_r_p_rv,extent=p_r_range+p_rv_range,y_label="$v_r/v_{200m}$",text="All Particles",title="Primary Snap",hide_xticks=True,kwargs=plot_kwargs)
    imshow_plot(fig.add_subplot(gs[1,1]),all_p_r_p_tv,extent=p_r_range+p_tv_range,y_label="$v_t/v_{200m}$",hide_xticks=True,kwargs=plot_kwargs)
    imshow_plot(fig.add_subplot(gs[1,2]),all_p_rv_p_tv,extent=p_rv_range+p_tv_range,hide_xticks=True,hide_yticks=True,kwargs=plot_kwargs)
    imshow_plot(fig.add_subplot(gs[1,3]),all_c_r_c_rv,extent=p_r_range+p_rv_range,y_label="$v_r/v_{200m}$",title="Secondary Snap",hide_xticks=True,kwargs=plot_kwargs)
    
    imshow_plot(fig.add_subplot(gs[2,0]),inf_p_r_p_rv,extent=p_r_range+p_rv_range,y_label="$v_r/v_{200m}$",text="Infalling Particles",hide_xticks=True,kwargs=plot_kwargs)
    imshow_plot(fig.add_subplot(gs[2,1]),inf_p_r_p_tv,extent=p_r_range+p_tv_range,y_label="$v_t/v_{200m}$",hide_xticks=True,kwargs=plot_kwargs)
    imshow_plot(fig.add_subplot(gs[2,2]),inf_p_rv_p_tv,extent=p_rv_range+p_tv_range,hide_xticks=True,hide_yticks=True,kwargs=plot_kwargs)
    imshow_plot(fig.add_subplot(gs[2,3]),inf_c_r_c_rv,extent=p_r_range+p_rv_range,y_label="$v_r/v_{200m}$",hide_xticks=True,kwargs=plot_kwargs)
                
    imshow_plot(fig.add_subplot(gs[3,0]),orb_p_r_p_rv,extent=p_r_range+p_rv_range,x_label="$r/R_{200m}$",y_label="$v_r/v_{200m}$",text="Orbiting Particles",kwargs=plot_kwargs)
    imshow_plot(fig.add_subplot(gs[3,1]),orb_p_r_p_tv,extent=p_r_range+p_tv_range,x_label="$r/R_{200m}$",y_label="$v_t/v_{200m}$",kwargs=plot_kwargs)
    imshow_plot(fig.add_subplot(gs[3,2]),orb_p_rv_p_tv,extent=p_rv_range+p_tv_range,x_label="$v_r/v_{200m}$",hide_yticks=True,kwargs=plot_kwargs)
    imshow_plot(fig.add_subplot(gs[3,3]),orb_c_r_c_rv,extent=p_r_range+p_rv_range,x_label="$r/R_{200m}$",y_label="$v_r/v_{200m}$",kwargs=plot_kwargs)

    color_bar = plt.colorbar(mpl.cm.ScalarMappable(norm=mpl.colors.LogNorm(vmin=1, vmax=max_ptl),cmap=cividis_cmap), cax=plt.subplot(gs[1:,-1]))
    color_bar.set_label("Number of Particles",fontsize=16)
    color_bar.ax.tick_params(labelsize=14)
    
    fig.savefig(save_loc + "ptl_distr.png")

def plot_miss_class_dist(p_corr_labels, p_ml_labels, p_r, p_rv, p_tv, c_r, c_rv, num_bins, save_loc):
    split_yscale_dict = {
        "linthrsh":2, 
        "lin_nbin":30,
        "log_nbin":15,
    }
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

    misclass_dict = {
        "Total Num of Particles": tot_num_ptl,
        "Num Incorrect Infalling Particles": str(inc_inf.shape[0])+", "+str(np.round(((inc_inf.shape[0]/num_inf)*100),2))+"% of infalling ptls",
        "Num Incorrect Orbiting Particles": str(inc_orb.shape[0])+", "+str(np.round(((inc_orb.shape[0]/num_orb)*100),2))+"% of orbiting ptls",
        "Num Incorrect All Particles": str(tot_num_inc)+", "+str(np.round(((tot_num_inc/tot_num_ptl)*100),2))+"% of all ptls",
    }
    
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
    act_all_p_r_p_rv = histogram(p_r,p_rv,use_bins=[num_bins,num_bins],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    act_all_p_r_p_tv = histogram(p_r,p_tv,use_bins=[num_bins,num_bins],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    act_all_p_rv_p_tv = histogram(p_rv,p_tv,use_bins=[num_bins,num_bins],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    act_all_c_r_c_rv = histogram(c_r,c_rv,use_bins=[act_all_p_r_p_rv["x_edge"],act_all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    
    act_inf_p_r_p_rv = histogram(act_inf_p_r,act_inf_p_rv,use_bins=[act_all_p_r_p_rv["x_edge"],act_all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    act_inf_p_r_p_tv = histogram(act_inf_p_r,act_inf_p_tv,use_bins=[act_all_p_r_p_tv["x_edge"],act_all_p_r_p_tv["y_edge"]],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    act_inf_p_rv_p_tv = histogram(act_inf_p_rv,act_inf_p_tv,use_bins=[act_all_p_rv_p_tv["x_edge"],act_all_p_rv_p_tv["y_edge"]],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    act_inf_c_r_c_rv = histogram(act_inf_c_r,act_inf_c_rv,use_bins=[act_all_c_r_c_rv["x_edge"],act_all_c_r_c_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    
    act_orb_p_r_p_rv = histogram(act_orb_p_r,act_orb_p_rv,use_bins=[act_all_p_r_p_rv["x_edge"],act_all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    act_orb_p_r_p_tv = histogram(act_orb_p_r,act_orb_p_tv,use_bins=[act_all_p_r_p_tv["x_edge"],act_all_p_r_p_tv["y_edge"]],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    act_orb_p_rv_p_tv = histogram(act_orb_p_rv,act_orb_p_tv,use_bins=[act_all_p_rv_p_tv["x_edge"],act_all_p_rv_p_tv["y_edge"]],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    act_orb_c_r_c_rv = histogram(act_orb_c_r,act_orb_c_rv,use_bins=[act_all_p_r_p_rv["x_edge"],act_all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
        
    inc_inf_p_r_p_rv = histogram(inc_inf_p_r,inc_inf_p_rv,use_bins=[act_all_p_r_p_rv["x_edge"],act_all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    inc_inf_p_r_p_tv = histogram(inc_inf_p_r,inc_inf_p_tv,use_bins=[act_all_p_r_p_tv["x_edge"],act_all_p_r_p_tv["y_edge"]],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    inc_inf_p_rv_p_tv = histogram(inc_inf_p_rv,inc_inf_p_tv,use_bins=[act_all_p_rv_p_tv["x_edge"],act_all_p_rv_p_tv["y_edge"]],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    inc_inf_c_r_c_rv = histogram(inc_inf_c_r,inc_inf_c_rv,use_bins=[act_all_c_r_c_rv["x_edge"],act_all_c_r_c_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    
    inc_orb_p_r_p_rv = histogram(inc_orb_p_r,inc_orb_p_rv,use_bins=[act_all_p_r_p_rv["x_edge"],act_all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    inc_orb_p_r_p_tv = histogram(inc_orb_p_r,inc_orb_p_tv,use_bins=[act_all_p_r_p_tv["x_edge"],act_all_p_r_p_tv["y_edge"]],hist_range=[p_r_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    inc_orb_p_rv_p_tv = histogram(inc_orb_p_rv,inc_orb_p_tv,use_bins=[act_all_p_rv_p_tv["x_edge"],act_all_p_rv_p_tv["y_edge"]],hist_range=[p_rv_range,p_tv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)
    inc_orb_c_r_c_rv = histogram(inc_orb_c_r,inc_orb_c_rv,use_bins=[act_all_p_r_p_rv["x_edge"],act_all_p_r_p_rv["y_edge"]],hist_range=[p_r_range,p_rv_range],min_ptl=act_min_ptl,set_ptl=act_set_ptl,split_yscale_dict=split_yscale_dict)

    
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
    
    magma_cmap = plt.get_cmap("magma_r")
    magma_cmap.set_under(color='white')
    
    scale_miss_class_args = {
            "vmin":inc_min_ptl,
            "vmax":1,
            "norm":"log",
            "origin":"lower",
            "aspect":"auto",
            "cmap":magma_cmap,
    }
    
    
    widths = [4,4,4,4,.5]
    heights = [0.12,4,4,4]
    
    fig = plt.figure(constrained_layout=True,figsize=(30,25))
    gs = fig.add_gridspec(len(heights),len(widths),width_ratios = widths, height_ratios = heights, hspace=0, wspace=0)

    imshow_plot(fig.add_subplot(gs[1,0]), scale_inc_all_p_r_p_rv,extent=p_r_range+p_rv_range,x_label="$r/R_{200m}$",y_label="$v_r/v_{200m}$",text="All Misclassified\nScaled",kwargs=scale_miss_class_args)
    imshow_plot(fig.add_subplot(gs[1,1]), scale_inc_all_p_r_p_tv,extent=p_r_range+p_tv_range,x_label="$r/R_{200m}$",y_label="$v_t/v_{200m}$",kwargs=scale_miss_class_args)
    imshow_plot(fig.add_subplot(gs[1,2]), scale_inc_all_p_rv_p_tv,extent=p_rv_range+p_tv_range,x_label="$v_r/v_{200m}$",hide_yticks=True,kwargs=scale_miss_class_args)
    imshow_plot(fig.add_subplot(gs[1,3]), scale_inc_all_c_r_c_rv,extent=p_r_range+p_rv_range,x_label="$r/R_{200m}$",y_label="$v_r/v_{200m}$",text="All Misclassified\nScaled",kwargs=scale_miss_class_args)

    imshow_plot(fig.add_subplot(gs[2,0]), scale_inc_inf_p_r_p_rv,extent=p_r_range+p_rv_range,hide_xticks=True,hide_yticks=False,y_label="$v_r/v_{200m}$",text="Label: Orbit\nReal: Infall",kwargs=scale_miss_class_args, title="Primary Snap")
    imshow_plot(fig.add_subplot(gs[2,1]), scale_inc_inf_p_r_p_tv,extent=p_r_range+p_tv_range,y_label="$v_t/v_{200m}$",hide_xticks=True,kwargs=scale_miss_class_args)
    imshow_plot(fig.add_subplot(gs[2,2]), scale_inc_inf_p_rv_p_tv,extent=p_rv_range+p_tv_range,hide_xticks=True,hide_yticks=True,kwargs=scale_miss_class_args)
    imshow_plot(fig.add_subplot(gs[2,3]), scale_inc_inf_c_r_c_rv,extent=p_r_range+p_rv_range,y_label="$v_r/v_{200m}$",text="Label: Orbit\nReal: Infall",hide_xticks=True,kwargs=scale_miss_class_args, title="Secondary Snap")
    
    imshow_plot(fig.add_subplot(gs[3,0]), scale_inc_orb_p_r_p_rv,extent=p_r_range+p_rv_range,hide_xticks=True,hide_yticks=False,y_label="$v_r/v_{200m}$",text="Label: Infall\nReal: Orbit",kwargs=scale_miss_class_args)
    imshow_plot(fig.add_subplot(gs[3,1]), scale_inc_orb_p_r_p_tv,extent=p_r_range+p_tv_range,y_label="$v_t/v_{200m}$",hide_xticks=True,kwargs=scale_miss_class_args)
    imshow_plot(fig.add_subplot(gs[3,2]), scale_inc_orb_p_rv_p_tv,extent=p_rv_range+p_tv_range,hide_xticks=True,hide_yticks=True,kwargs=scale_miss_class_args)
    imshow_plot(fig.add_subplot(gs[3,3]), scale_inc_orb_c_r_c_rv,extent=p_r_range+p_rv_range,y_label="$v_r/v_{200m}$",text="Label: Infall\nReal: Orbit",hide_xticks=True,kwargs=scale_miss_class_args)
    
    color_bar = plt.colorbar(mpl.cm.ScalarMappable(norm=mpl.colors.LogNorm(vmin=inc_min_ptl, vmax=1),cmap=magma_cmap), cax=plt.subplot(gs[1:,-1]))
    color_bar.set_label("Num Incorrect Particles (inf/orb) / Total Particles (inf/orb)",fontsize=16)
    color_bar.ax.tick_params(labelsize=14)
    
    fig.savefig(save_loc + "scaled_miss_class.png")

def plot_r_rv_tv_graph():
    cmap = plt.get_cmap("magma")
    per_err_cmap = plt.get_cmap("cividis")

    widths = [4,4,4,.5]
    heights = [4,4]
    
    inf_fig = plt.figure()
    inf_fig.suptitle("Infalling Particles")
    gs = inf_fig.add_gridspec(2,4,width_ratios = widths, height_ratios = heights)
    
    phase_plot(inf_fig.add_subplot(gs[0,0]), ml_inf_r, ml_inf_rv, min_ptl, max_ptl, range=[r_range,rv_range], num_bins=num_bins, cmap=cmap, x_label="$r/R_{200m}$", y_label="$v_r/v_{200m}$",axisfontsize=12)
    phase_plot(inf_fig.add_subplot(gs[0,1]), ml_inf_r, ml_inf_tv, min_ptl, max_ptl, range=[r_range,tv_range], num_bins=num_bins, cmap=cmap, x_label="$r/R_{200m}$", y_label="$v_t/v_{200m}$", title="ML Predictions",axisfontsize=12)
    phase_plot(inf_fig.add_subplot(gs[0,2]), ml_inf_rv, ml_inf_tv, min_ptl, max_ptl, range=[rv_range,tv_range], num_bins=num_bins, cmap=cmap, x_label="$v_r/v_{200m}$", y_label="$v_t/v_{200m}$",axisfontsize=12)
    phase_plot(inf_fig.add_subplot(gs[1,0]), act_inf_r, act_inf_rv, min_ptl, max_ptl, range=[r_range,rv_range], num_bins=num_bins, cmap=cmap, x_label="$r/R_{200m}$", y_label="$v_r/v_{200m}$",axisfontsize=12)
    phase_plot(inf_fig.add_subplot(gs[1,1]), act_inf_r, act_inf_tv, min_ptl, max_ptl, range=[r_range,tv_range], num_bins=num_bins, cmap=cmap, x_label="$r/R_{200m}$", y_label="$v_t/v_{200m}$", title="Actual Distribution",axisfontsize=12)
    phase_plot(inf_fig.add_subplot(gs[1,2]), act_inf_rv, act_inf_tv, min_ptl, max_ptl, range=[rv_range,tv_range], num_bins=num_bins, cmap=cmap, x_label="$v_r/v_{200m}$", y_label="$v_t/v_{200m}$",axisfontsize=12)
    
    inf_color_bar = plt.colorbar(mpl.cm.ScalarMappable(norm=mpl.colors.LogNorm(vmin=min_ptl, vmax=max_ptl),cmap=cmap), cax=plt.subplot(gs[:2,-1]))
    
    inf_fig.savefig(save_location + title + "ptls_inf.png")
    
#########################################################################################################################################################
    
    orb_fig = plt.figure()
    orb_fig.suptitle("Orbiting Particles")
    gs = orb_fig.add_gridspec(2,4,width_ratios = widths, height_ratios = heights)
    
    phase_plot(orb_fig.add_subplot(gs[0,0]), ml_orb_r, ml_orb_rv, min_ptl, max_ptl, range=[r_range,rv_range], num_bins=num_bins, cmap=cmap, x_label="$r/R_{200m}$", y_label="$v_r/v_{200m}$",axisfontsize=12)
    phase_plot(orb_fig.add_subplot(gs[0,1]), ml_orb_r, ml_orb_tv, min_ptl, max_ptl, range=[r_range,tv_range], num_bins=num_bins, cmap=cmap, x_label="$r/R_{200m}$", y_label="$v_t/v_{200m}$", title="ML Predictions",axisfontsize=12)
    phase_plot(orb_fig.add_subplot(gs[0,2]), ml_orb_rv, ml_orb_tv, min_ptl, max_ptl, range=[rv_range,tv_range], num_bins=num_bins, cmap=cmap, x_label="$v_r/v_{200m}$", y_label="$v_t/v_{200m}$",axisfontsize=12)
    phase_plot(orb_fig.add_subplot(gs[1,0]), act_orb_r, act_orb_rv, min_ptl, max_ptl, range=[r_range,rv_range], num_bins=num_bins, cmap=cmap, x_label="$r/R_{200m}$", y_label="$v_r/v_{200m}$",axisfontsize=12)
    phase_plot(orb_fig.add_subplot(gs[1,1]), act_orb_r, act_orb_tv, min_ptl, max_ptl, range=[r_range,tv_range], num_bins=num_bins, cmap=cmap, x_label="$r/R_{200m}$", y_label="$v_t/v_{200m}$", title="Actual Distribution",axisfontsize=12)
    phase_plot(orb_fig.add_subplot(gs[1,2]), act_orb_rv, act_orb_tv, min_ptl, max_ptl, range=[rv_range,tv_range], num_bins=num_bins, cmap=cmap, x_label="$v_r/v_{200m}$", y_label="$v_t/v_{200m}$",axisfontsize=12)
    
    orb_color_bar = plt.colorbar(mpl.cm.ScalarMappable(norm=mpl.colors.LogNorm(vmin=min_ptl, vmax=max_ptl),cmap=cmap), cax=plt.subplot(gs[:2,-1]), pad = 0.1)
    
    orb_fig.savefig(save_location + title + "ptls_orb.png")    
    
#########################################################################################################################################################
    
    only_r_rv_widths = [4,4,.5]
    only_r_rv_heights = [4,4]
    only_r_rv_fig = plt.figure()
    only_r_rv_fig.suptitle("Radial Velocity Versus Radius: " + title)
    gs = only_r_rv_fig.add_gridspec(2,3,width_ratios = only_r_rv_widths, height_ratios = only_r_rv_heights)
    
    phase_plot(only_r_rv_fig.add_subplot(gs[0,0]), ml_orb_r, ml_orb_rv, min_ptl, max_ptl, range=[r_range,rv_range], num_bins=num_bins, cmap=cmap, x_label="$r/R_{200m}$", y_label="$v_r/v_{200m}$", title="ML Predicted Orbiting Particles")
    phase_plot(only_r_rv_fig.add_subplot(gs[0,1]), ml_inf_r, ml_inf_rv, min_ptl, max_ptl, range=[r_range,rv_range], num_bins=num_bins, cmap=cmap, x_label="$r/R_{200m}$", y_label="$v_r/v_{200m}$", title="ML Predicted Infalling Particles")
    phase_plot(only_r_rv_fig.add_subplot(gs[1,0]), act_orb_r, act_orb_rv, min_ptl, max_ptl, range=[r_range,rv_range], num_bins=num_bins, cmap=cmap, x_label="$r/R_{200m}$", y_label="$v_r/v_{200m}$", title="Actual Orbiting Particles")
    phase_plot(only_r_rv_fig.add_subplot(gs[1,1]), act_inf_r, act_inf_rv, min_ptl, max_ptl, range=[r_range,rv_range], num_bins=num_bins, cmap=cmap, x_label="$r/R_{200m}$", y_label="$v_r/v_{200m}$", title="Actual Infalling Particles")

    
    only_r_rv_color_bar = plt.colorbar(mpl.cm.ScalarMappable(norm=mpl.colors.LogNorm(vmin=min_ptl, vmax=max_ptl),cmap=cmap), cax=plt.subplot(gs[:2,-1]))
    only_r_rv_fig.savefig(save_location + title + "only_r_rv.png")

def plot_perr_err():
    return
