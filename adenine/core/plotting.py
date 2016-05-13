#!/usr/bin/python -W ignore::DeprecationWarning
# -*- coding: utf-8 -*-

__all__ = ["make_silhouette", "make_scatter", "make_voronoi", "make_tree",
           "make_dendrogram", "plot_PCmagnitude", "plot_eigs"]

import os
import logging
import cPickle as pkl
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn import metrics

from adenine.utils.extra import next_color, reset_palette, title_from_filename, values_iterator

GLOBAL_FF = 'png'

def set_file_ext(ext):
    global GLOBAL_FF
    GLOBAL_FF = ext

def make_silhouette(root, labels, model_param, data_in, model):
    # Create a subplot with 1 row and 2 columns
    fig, (ax1) = plt.subplots(1, 1)
    fig.set_size_inches(20, 15)

    # The 1st subplot is the silhouette plot
    # The silhouette coefficient can range from -1, 1 but in this example all
    # lie within [-0.1, 1]
    # ax1.set_xlim([-0.1, 1])
    # The (n_clusters+1)*10 is for inserting blank space between silhouette
    # plots of individual clusters, to demarcate them clearly.
    n_clusters = np.unique(labels).shape[0]
    ax1.set_ylim([0, len(data_in) + (n_clusters + 1) * 10])

    # The silhouette_score gives the average value for all the samples.
    # This gives a perspective into the density and separation of the formed
    # clusters

    # Compute the silhouette scores for each sample
    if hasattr(model, 'affinity'):
        sample_silhouette_values = metrics.silhouette_samples(data_in, labels,
                                                          metric=model.affinity)
    else:
        sample_silhouette_values = metrics.silhouette_samples(data_in, labels,
                                                          metric='euclidean')

    sil = np.mean(sample_silhouette_values)

    y_lower = 10
    reset_palette()
    for i, label in enumerate(np.unique(labels)):
        # Aggregate the silhouette scores for samples belonging to
        # cluster i, and sort them
        ith_cluster_silhouette_values = sample_silhouette_values[labels == label]
        ith_cluster_silhouette_values.sort()

        size_cluster_i = ith_cluster_silhouette_values.shape[0]
        y_upper = y_lower + size_cluster_i

        # color = cm.spectral(float(i) / n_clusters)
        color = next_color()
        ax1.fill_betweenx(np.arange(y_lower, y_upper),
                          0, ith_cluster_silhouette_values,
                          facecolor=color, edgecolor=color, alpha=0.7)

        # Label the silhouette plots with their cluster numbers at the middle
        ax1.text(-0.05, y_lower + 0.5 * size_cluster_i, str(label))

        # Compute the new y_lower for next plot
        y_lower = y_upper + 10  # 10 for the 0 samples

    # ax1.set_title("Silhouette plot for the various clusters.")
    ax1.set_xlabel("silhouette coefficient values")
    ax1.set_ylabel("cluster label")

    # The vertical line for average silhoutte score of all the values
    ax1.axvline(x=sil, color="red", linestyle="--")

    ax1.set_yticks([])  # Clear the yaxis labels / ticks
    # ax1.set_xticks([-0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8, 1])

    title = "Silhouette analysis. {0} clusters for {2} samples, average score {1:.4f}".format(n_clusters, sil, data_in.shape[0])
    plt.suptitle(title)#, fontsize=14, fontweight='bold')

    filename = os.path.join(root,os.path.basename(root)+"_silhouette."+GLOBAL_FF)
    fig.savefig(filename)
    logging.info('Figured saved {}'.format(filename))
    plt.close()

def make_scatter(root=(), data_in=(), model_param=(), labels=None, true_labels=False, model=()):
    """Generates and saves the scatter plot of the dimensionality reduced data set.

    This function generates the scatter plot representing the dimensionality reduced data set. The plots will be saved into the root folder in a tree-like structure.

    Parameters
    -----------
    root : string
        The root path for the output creation

    data_in : array of float, shape : (n_samples, n_dimensions)
        The low space embedding estimated by the dimensinality reduction and manifold learning algorithm.

    model_param : dictionary
        The parameters of the dimensionality reduciont and manifold learning algorithm.

    labels : array of float, shape : n_samples
        The label vector. It can contain true or estimated labels.

    true_labels : boolean
        Identify if labels contains true or estimated labels.

    model : sklearn or sklearn-like object
        An instance of the class that evaluates a step. In particular this must be a clustering model provided with the clusters_centers_ attribute (e.g. KMeans).
    """
    n_samples, n_dim = data_in.shape

    # Define plot color
    if labels is None:
        y = np.zeros((n_samples))
        _hue = ' '
    else:
        y = labels
        _hue = 'Classes' if true_labels else 'Estimated Labels'

    title = title_from_filename(root)

    # Seaborn scatter plot
    #2D plot
    X = data_in[:,:2]
    idx = np.argsort(y)

    # df = pd.DataFrame(data=np.hstack((X[idx,:2],y[idx,np.newaxis])), columns=["$x_1$","$x_2$",_hue])
    df = pd.DataFrame(data=np.hstack((X[idx,:2],y[idx][:,np.newaxis])), columns=["$x_1$","$x_2$",_hue])
    if df.dtypes[_hue] != 'O': df[_hue] = df[_hue].astype('int64')
    # Generate seaborn plot
    g = sns.FacetGrid(df, hue=_hue, palette="Set1", size=5, legend_out=False)
    g.map(plt.scatter, "$x_1$", "$x_2$", s=100, linewidth=.5, edgecolor="white")
    if _hue != ' ': g.add_legend() #!! customize legend
    # g.set_xticklabels([])
    # g.set_yticklabels([])
    g.ax.autoscale_view(True,True,True)
    plt.title(title)
    filename = os.path.join(root,os.path.basename(root)+"_scatter2D."+GLOBAL_FF)
    plt.savefig(filename)
    logging.info('Figured saved {}'.format(filename))
    plt.close()

    #3D plot
    filename = os.path.join(root,os.path.basename(root)+"_scatter3D."+GLOBAL_FF)
    X = data_in[:,:3]
    if X.shape[1] < 3:
        logging.warning('{} not generated (data have less than 3 dimensions)'
                        .format(filename))
    else:
        try:
            from mpl_toolkits.mplot3d import Axes3D
            ax = plt.figure().gca(projection='3d')
            # ax.scatter(X[:,0], X[:,1], X[:,2], y, c=y, cmap='hot', s=100, linewidth=.5, edgecolor="white")
            y = np.array(y)
            reset_palette(len(np.unique(y)))
            for _, label in enumerate(np.unique(y)):
                idx = np.where(y==label)[0]
                ax.plot(X[:,0][idx], X[:,1][idx], X[:,2][idx], 'o',
                        c=next_color(), label=str(label), mew=.5, mec="white")

            ax.set_xlabel(r'$x_1$')
            ax.set_ylabel(r'$x_2$')
            ax.set_zlabel(r'$x_3$')
            ax.autoscale_view(True,True,True)
            ax.set_title(title)
            ax.legend(loc='upper left', numpoints=1, ncol=10, fontsize=8,
                      bbox_to_anchor=(0, 0))
            # plt.legend(loc='upper left', numpoints=1, ncol=3, fontsize=8, bbox_to_anchor=(0, 0111))
            plt.savefig(filename)
            logging.info('Figured saved {}'.format(filename))
            plt.close()
        except Exception as e:
            logging.info('Error in 3D plot: ' + str(e))

    # seaborn pairplot
    n_cols = min(data_in.shape[1], 3)
    cols = ["$x_{}$".format(i+1) for i in range(n_cols)]
    X = data_in[:,:3]
    idx = np.argsort(y)
    df = pd.DataFrame(data=np.hstack((X[idx,:],y[idx,np.newaxis])), columns=cols+[_hue])
    if df.dtypes[_hue] != 'O': df[_hue] = df[_hue].astype('int64')
    g = sns.PairGrid(df, hue=_hue, palette="Set1", vars=cols)
    g = g.map_diag(plt.hist)#, palette="Set1")
    g = g.map_offdiag(plt.scatter, s=100, linewidth=.5, edgecolor="white")

    # g = sns.pairplot(df, hue=_hue, palette="Set1", vars=["$x_1$","$x_2$","$x_3$"]), size=5)
    if _hue != ' ': plt.legend(title=_hue,bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0., fontsize="large")
    plt.suptitle(title,x=0.6, y=1.01,fontsize="large")
    filename = os.path.join(root,os.path.basename(root)+"_pairgrid."+GLOBAL_FF)
    g.savefig(filename)
    logging.info('Figured saved {}'.format(filename))
    plt.close()

def make_voronoi(root=(), data_in=(), model_param=(), labels=None, true_labels=False, model=()):
    """Generate and save the Voronoi tessellation obtained from the clustering algorithm.

    This function generates the Voronoi tessellation obtained from the clustering algorithm applied on the data projected on a two-dimensional embedding. The plots will be saved into the appropriate folder of the tree-like structure created into the root folder.

    Parameters
    -----------
    root : string
        The root path for the output creation

    data_in : array of float, shape : (n_samples, n_dimensions)
        The low space embedding estimated by the dimensinality reduction and manifold learning algorithm.

    model_param : dictionary
        The parameters of the dimensionality reduciont and manifold learning algorithm.

    labels : array of int, shape : n_samples
        The result of the clustering step.

    true_labels : boolean [deprecated]
        Identify if labels contains true or estimated labels.

    model : sklearn or sklearn-like object
        An instance of the class that evaluates a step. In particular this must be a clustering model provided with the clusters_centers_ attribute (e.g. KMeans).
    """
    n_samples, n_dim = data_in.shape

    # Define plot color
    if labels is None:
        y = np.zeros((n_samples))
        _hue = ' '
    else:
        y = labels # use the labels if provided
        _hue = 'Classes'

    title = title_from_filename(root)

    # Seaborn scatter Plot
    X = data_in[:,:2]
    idx = np.argsort(y)
    X = X[idx,:]
    y = y[idx,np.newaxis]
    df = pd.DataFrame(data=np.hstack((X, y)), columns=["$x_1$","$x_2$",_hue])
    if df.dtypes[_hue] != 'O': df[_hue] = df[_hue].astype('int64')
    # Generate seaborn plot
    g = sns.FacetGrid(df, hue=_hue, palette="Set1", size=5, legend_out=False)
    g.map(plt.scatter, "$x_1$", "$x_2$", s=100, linewidth=.5, edgecolor="white")
    if _hue != ' ': g.add_legend() #!! customize legend
    g.ax.autoscale_view(True,True,True)
    plt.title(title)

    # Add centroids
    if hasattr(model, 'cluster_centers_'):
        plt.scatter(model.cluster_centers_[:,0], model.cluster_centers_[:,1], s=100, marker='h', c='w')

    # Make and add to the Plot the decision boundary.
    npoints = 1000 # the number of points in that makes the background. Reducing this will decrease the quality of the voronoi background
    x_min, x_max = X[:, 0].min(), X[:, 0].max()
    y_min, y_max = X[:, 1].min(), X[:, 1].max()
    offset = (x_max - x_min) / 5. + (y_max - y_min) / 5. # zoom out the plot a bit
    xx, yy = np.meshgrid(np.linspace(x_min-offset, x_max+offset, npoints), np.linspace(y_min-offset, y_max+offset, npoints))

    # Obtain labels for each point in mesh. Use last trained model.

    Z = model.predict(np.c_[xx.ravel(), yy.ravel()])
    # Put the result into a color plot
    Z = Z.reshape(xx.shape)

    plt.imshow(Z, interpolation='nearest',
               extent=(xx.min(), xx.max(), yy.min(), yy.max()),
               cmap=plt.get_cmap('Pastel1'), aspect='auto', origin='lower')

    plt.xlim([xx.min(), xx.max()])
    plt.ylim([yy.min(), yy.max()])

    filename = os.path.join(root,os.path.basename(root)+"."+GLOBAL_FF)
    plt.savefig(filename)
    logging.info('Figured saved {}'.format(filename))
    plt.close()

def make_tree(root=(), data_in=(), model_param=(), trueLabel=None, labels=(), model=()):
    """Generate and save the tree structure obtained from the clustering algorithm.

    This function generates the tree obtained from the clustering algorithm applied on the data. The plots will be saved into the appropriate folder of the tree-like structure created into the root folder.

    Parameters
    -----------
    root : string
        The root path for the output creation

    data_in : array of float, shape : (n_samples, n_dimensions)
        The low space embedding estimated by the dimensinality reduction and manifold learning algorithm.

    model_param : dictionary
        The parameters of the dimensionality reduciont and manifold learning algorithm.

    trueLabel : array of float, shape : n_samples
        The true label vector; np.nan if missing (useful for plotting reasons).

    labels : array of int, shape : n_samples
        The result of the clustering step.

    model : sklearn or sklearn-like object
        An instance of the class that evaluates a step. In particular this must be a clustering model provided with the clusters_centers_ attribute (e.g. KMeans).
    """
    filename = os.path.join(root, os.path.basename(root)+'_tree.pdf')
    try:
        import itertools
        import pydot

        graph = pydot.Dot(graph_type='graph')

        ii = itertools.count(data_in.shape[0])
        for k, x in enumerate(model.children_):
            root_node = next(ii)
            left_edge = pydot.Edge(root_node, x[0])
            right_edge = pydot.Edge(root_node, x[1])
            graph.add_edge(right_edge)
            graph.add_edge(left_edge)

        # graph.write_png(filename[:-2]+"ng")
        graph.write_pdf(filename)
        logging.info('Figured saved {}'.format(filename))
    except:
        logging.info('Cannot create {}'.format(filename))

def make_dendrogram(root=(), data_in=(), model_param=(), trueLabel=None, labels=(), model=()):
    """Generate and save the dendrogram obtained from the clustering algorithm.

    This function generates the dendrogram obtained from the clustering algorithm applied on the data. The plots will be saved into the appropriate folder of the tree-like structure created into the root folder.

    Parameters
    -----------
    root : string
        The root path for the output creation

    data_in : array of float, shape : (n_samples, n_dimensions)
        The low space embedding estimated by the dimensinality reduction and manifold learning algorithm.

    model_param : dictionary
        The parameters of the dimensionality reduciont and manifold learning algorithm.

    trueLabel : array of float, shape : n_samples
        The true label vector; np.nan if missing (useful for plotting reasons).

    labels : array of int, shape : n_samples
        The result of the clustering step.

    model : sklearn or sklearn-like object
        An instance of the class that evaluates a step. In particular this must be a clustering model provided with the clusters_centers_ attribute (e.g. KMeans).
    """
    # tmp = np.hstack((np.arange(0,data_in.shape[0],1)[:,np.newaxis], data_in[:,0][:,np.newaxis], data_in[:,1][:,np.newaxis]))
    tmp = data_in
    col = ["$x_{"+str(i)+"}$" for i in np.arange(0, data_in.shape[1], 1)]
    df = pd.DataFrame(data=tmp, columns=col)

    if model.affinity == 'precomputed': # TODO sistemare, fede
        # tmp is the distance matrix
        make_dendrograms = False
        if make_dendrograms:
            sns.set(font="monospace")
            for method in ['single','complete','average','weighted','centroid','median','ward']:
                from scipy.cluster.hierarchy import linkage
                # print("Compute linkage matrix with metric={} ...".format(method))
                Z = linkage(tmp, method=method, metric='euclidean')
                g = sns.clustermap(df.corr(), method=method, row_linkage=Z, col_linkage=Z)
                filename = os.path.join(root, '_'.join((os.path.basename(root), method, '_dendrogram.png')))
                g.savefig(filename)
                logging.info('Figured saved {}'.format(filename))
                plt.close()
        avg_sil = True
        if avg_sil:
            try:
                from ignet.plotting.silhouette_hierarchical import plot_avg_silhouette
                filename = plot_avg_silhouette(tmp)
                logging.info('Figured saved {}'.format(filename))
            except:
                logging.warn("Cannot import name {}".format('ignet.plotting'))
        return

    # workaround to a different name used for manhatta / cityblock distance
    if model.affinity == 'manhattan': model.affinity = 'cityblock'

    g = sns.clustermap(df, method=model.linkage, metric=model.affinity, cmap='coolwarm')
    plt.setp(g.ax_heatmap.yaxis.get_majorticklabels(), rotation=0, fontsize=5)
    filename = os.path.join(root, os.path.basename(root)+'_dendrogram.'+GLOBAL_FF)
    g.savefig(filename)
    logging.info('Figured saved {}'.format(filename))
    plt.close()

def plot_PCmagnitude(root=(), points=(), title='', ylabel=''):
    """Generate and save the plot representing the trend of principal components magnitude.

    Parameters
    -----------

    rootFolder : string
        The root path for the output creation

    points : array of float, shape : n_components
        This could be the explained variance ratio or the eigenvalues of the centered matrix, according to the PCA algorithm of choice, respectively: PCA or KernelPCA.

    title : string
        Plot title
    """
    plt.plot(np.arange(1, len(points)+1), points, '-o')
    plt.title(title)
    plt.grid('on')
    plt.ylabel(ylabel)
    plt.xlim([1,min(20,len(points)+1)]) # Show maximum 20 components
    plt.ylim([0,1])
    filename = os.path.join(root,os.path.basename(root)+"_magnitude."+GLOBAL_FF)
    plt.savefig(filename)
    plt.close()

def plot_eigs(root='', affinity=(), n_clusters=0, title='', ylabel='', normalised=True):
    """Generate and save the plot representing the eigenvalues of the Laplacian
    associated to data affinity matrix.

    Parameters
    -----------

    rootFolder : string
        The root path for the output creation

    affinity : array of float, shape : (n_samples, n_samples)
        The affinity matrix.

    n_clusters : float
        The number of clusters.

    ylabel : string
        The label of the vertical axis.

    title : string
        Plot title
    """
    W = affinity - np.diag(np.diag(affinity))
    D = np.diag([np.sum(x) for x in W])
    L = D - W

    if normalised:
        # aux = np.linalg.inv(np.diag([np.sqrt(np.sum(x)) for x in W]))
        aux =  np.diag(1. / np.array([np.sqrt(np.sum(x)) for x in W]))
        L = np.eye(L.shape[0]) - (np.dot(np.dot(aux,W),aux)) # normalised L

    try:
        w, v = np.linalg.eig(L)
        w = np.array(sorted(np.abs(w)))
        plt.plot(np.arange(1, len(w)+1), w, '-o')
        plt.title(title)
        plt.grid('on')
        plt.ylabel(ylabel)
        plt.xlim([1,min(20,len(w)+1)]) # Show maximum 20 components
        if n_clusters > 0:
            plt.axvline(x=n_clusters+.5, linestyle='--', color='r', label='selected clusters')
        plt.legend(loc='upper right', numpoints=1, ncol=10, fontsize=8)#, bbox_to_anchor=(1, 1))
        filename = os.path.join(root,os.path.basename(root)+"_eigenvals."+GLOBAL_FF)
        plt.savefig(filename)
    except np.linalg.LinAlgError:
        logging.critical("Error in plot_eigs: Affinity matrix contained negative"
                         " values. You can try by specifying normalised=False")
    plt.close()