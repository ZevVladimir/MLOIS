import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
# mpl.use('TkAgg')
# manager = plt.get_current_fig_manager()
# manager.resize(*manager.window.maxsize())

class plot_determiner:
    def __init__(self, plot_types, plot_size, X, Y, xlim = None, ylim = None, x_label = None, y_label = None, line_labels = None, fig_title = None, subplot_title = None, colorbar = False, constrained = False, save_location = None, args = [], kwargs = {}):
        self.plot_types = plot_types
        self.plot_size = plot_size
        self.X = X
        self.Y = Y
        self.xlim = xlim
        self.ylim = ylim
        self.x_label = x_label
        self.y_label = y_label
        self.line_labels = line_labels
        self.fig_title = fig_title
        self.subplot_title = subplot_title
        self.colorbar = colorbar
        self.constrained = constrained
        self.save_location = save_location
        self.args = args
        self.kwargs = kwargs
        self.fig = None
    
    def plot(self):
        if self.constrained:
            fig = plt.figure(constrained_layout=True)
        else:
            fig = plt.figure()

        fig.suptitle(self.fig_title)
        subfigs = fig.subfigures(nrows=self.plot_size[0], ncols=1)

        curr_plot_num = 0
        curr_line_num = 0

        for row,subfig in enumerate(subfigs):
            subfig.suptitle(self.subplot_title[row])

            axs = subfig.subplots(nrows=1, ncols=self.plot_size[1])
            for col,ax in enumerate(axs):
                for line in range(self.X.shape[1]):
                    if self.plot_size[0] > 1:
                        if self.line_labels != None: 
                            graph = ax.__getattribute__(self.plot_types[curr_plot_num])(self.X[:,line,curr_plot_num], self.Y[:,line,curr_plot_num], label = self.line_labels[curr_line_num], *self.args[curr_plot_num], **self.kwargs) 
                        else:
                            graph = ax.__getattribute__(self.plot_types[curr_plot_num])(self.X[:,line,curr_plot_num], self.Y[:,line,curr_plot_num], *self.args[curr_plot_num], **self.kwargs)
                        
                        if self.xlim != None:
                            ax.set_xlim(self.xlim)
                        if self.ylim != None:
                            ax.set_ylim(self.ylim)
                        if self.x_label != None:
                            ax.set_xlabel(self.x_label[curr_plot_num])
                        if self.y_label != None:
                            ax.set_ylabel(self.y_label[curr_plot_num])
                        
                    else:
                        if self.line_labels != None: 
                            graph = ax.__getattribute__(self.plot_types[curr_plot_num])(self.X[:,line,curr_plot_num], self.Y[:,line,curr_plot_num], label = self.line_labels[curr_line_num], *self.args[curr_plot_num], **self.kwargs) 
                        else:
                            graph = ax.__getattribute__(self.plot_types[curr_plot_num])(self.X[:,line,curr_plot_num], self.Y[:,line,curr_plot_num], *self.args[curr_plot_num], **self.kwargs)

                        if self.xlim != None:
                            ax.set_xlim(self.xlim)
                        if self.ylim != None:
                            ax.set_ylim(self.ylim)
                        if self.x_label != None:
                            ax.set_xlabel(self.x_label[curr_plot_num])
                        if self.y_label != None:
                            ax.set_ylabel(self.y_label[curr_plot_num])
                    curr_line_num += 1
                curr_plot_num += 1

            if self.colorbar:
                axcb = fig.colorbar(mpl.cm.ScalarMappable(norm=mpl.colors.LogNorm(vmin=self.kwargs["vmin"], vmax=self.kwargs["vmax"]),cmap=self.kwargs["cmap"]), ax=axs.ravel().tolist(), pad=0.04, aspect = 30)
        
        if self.line_labels != None:
            plt.legend()
        self.fig = fig

        return fig
    
    def save(self, new_fig = None):
        if new_fig != None:
            self.fig = new_fig
            self.fig.savefig(self.save_location)
        elif self.fig != None:
            self.fig.savefig(self.save_location)
        else:
            print("No figure to save, try calling .plot()")
    
    def show(self, new_fig = None):
        if new_fig != None:
            self.fig = new_fig
            fig.show()
            plt.close()
        elif self.fig != None:
            fig = self.fig
            fig.show()
            plt.close()
        else:
            print("No figure to show, try calling .plot()")