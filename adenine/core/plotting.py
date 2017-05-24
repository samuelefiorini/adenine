#!/usr/bin/python -W ignore::DeprecationWarning
# -*- coding: utf-8 -*-
"""Adenine plotting module."""

######################################################################
# Copyright (C) 2016 Samuele Fiorini, Federico Tomasi, Annalisa Barla
#
# FreeBSD License
######################################################################

import os
import logging
# import cPickle as pkl
import numpy as np
import scipy as sp
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns; sns.set(font="monospace")
import time
from sklearn import metrics
# Legacy import
try:
    from sklearn.model_selection import StratifiedShuffleSplit
except ImportError:
    from sklearn.cross_validation import StratifiedShuffleSplit

import adenine
from adenine.core.template.d3_template import D3_TREE
from adenine.utils.extra import title_from_filename, Palette

__all__ = ("silhouette", "scatter", "voronoi", "tree",
           "dendrogram", "pcmagnitude", "eigs")

DEFAULT_EXT = 'png'


def silhouette(root, data_in, labels, model=None):
    """Generate and save the silhouette plot of data_in w.r.t labels.

    This function generates the silhouette plot representing how data are
    correctly clustered, based on labels.
    The plots will be saved into the root folder in a tree-like structure.

    Parameters
    -----------
    root : string
        The root path for the output creation

    data_in : array of float, shape : (n_samples, n_dimensions)
        The low space embedding estimated by the dimensionality reduction and
        manifold learning algorithm.

    labels : array of float, shape : n_samples
        The label vector. It can contain true or estimated labels.

    model : sklearn or sklearn-like object
        An instance of the class that evaluates a step.
    """
    if labels is None:
        logging.warning('Cannot make silhouette plot with no real labels.')
        return

    if len(labels) < 2 or len(labels) > data_in.shape[0] - 1:
        logging.warning('Cannot make silhouette if number of labels is %d. '
                        'Valid values are 2 to n_samples - 1 '
                        '(inclusive).', len(labels))
        return

    # Create a subplot with 1 row and 2 columns
    fig, (ax1) = plt.subplots(1, 1)
    fig.set_size_inches(20, 15)

    # The silhouette coefficient can range from -1, 1
    # ax1.set_xlim([-1, 1])

    # The (n_clusters+1)*10 is for inserting blank space between silhouette
    # plots of individual clusters.
    n_clusters = np.unique(labels).shape[0]
    ax1.set_ylim([0, len(data_in) + (n_clusters + 1) * 10])

    # The silhouette_score gives the average value for all the samples.
    # This gives a perspective into the density and separation of the formed
    # clusters
    metric = model.affinity if hasattr(model, 'affinity') else 'euclidean'
    # catch exceptions of Spectral Embedding affinity
    if metric == 'rbf':
        def metric(x, y):
            return metrics.pairwise.rbf_kernel(x.reshape(1, -1),
                                               y.reshape(1, -1))
    if metric == 'nearest_neighbors':
        metric = 'euclidean'
    sample_silhouette_values = metrics.silhouette_samples(data_in, labels,
                                                          metric=metric)
    sil = np.mean(sample_silhouette_values)

    y_lower = 10
    palette = Palette()
    for _, label in enumerate(np.unique(labels)):
        # Aggregate the silhouette scores for samples belonging to
        # cluster i, and sort them
        ith_cluster_silhouette_values = sample_silhouette_values[labels == label]
        ith_cluster_silhouette_values.sort()

        size_cluster_i = ith_cluster_silhouette_values.shape[0]
        y_upper = y_lower + size_cluster_i

        # color = cm.spectral(float(i) / n_clusters)
        color = palette.next()
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
    ax1.set_yticks([])
    # ax1.set_xticks([-0.6, -0.4, -0.2, 0, 0.2, 0.4, 0.6, 0.8, 1])

    plt.suptitle("Silhouette analysis. "
                 "{0} clusters for {2} samples, average score {1:.4f}"
                 .format(n_clusters, sil, data_in.shape[0]))

    filename = os.path.join(
        root, os.path.basename(root) + "_silhouette." + DEFAULT_EXT)
    fig.savefig(filename)
    logging.info('Figure saved %s', filename)
    plt.close()


def scatter(root, data_in, labels=None, true_labels=False, model=None):
    """Generate the scatter plot of the dimensionality reduced data set.

    This function generates the scatter plot representing the dimensionality
    reduced data set. The plots will be saved into the root folder in a
    tree-like structure.

    Parameters
    ----------
    root : string
        The root path for the output creation

    data_in : array of float, shape : (n_samples, n_dimensions)
        The low space embedding estimated by the dimensinality reduction and
        manifold learning algorithm.

    labels : array of float, shape : n_samples
        The label vector. It can contain true or estimated labels.

    true_labels : boolean
        Identify if labels contains true or estimated labels.

    model : sklearn or sklearn-like object
        An instance of the class that evaluates a step. In particular this must
        be a clustering model provided with the clusters_centers_ attribute
        (e.g. KMeans).
    """
    if hasattr(model, 'affinity') and model.affinity == 'precomputed':
        logging.info("Scatter cannot be performed with precomputed distances.")
        return

    n_samples, n_dim = data_in.shape

    # Define plot color
    if labels is None:
        labels = np.zeros(n_samples, dtype=np.short)
        hue = ' '
    else:
        labels = np.asarray(labels)
        hue = 'Classes' if true_labels else 'Estimated Labels'

    title = title_from_filename(root)

    # Seaborn scatter plot
    # 2D plot
    X = data_in[:, :2]
    idx = np.argsort(labels)

    df = pd.DataFrame(
        data=np.hstack((X[idx, :2], labels[idx][:, np.newaxis])),
        columns=["$x_1$", "$x_2$", hue]).astype(
            {"$x_1$": float, "$x_2$": float})
    if df.dtypes[hue] != 'O':
        df[hue] = df[hue].astype('int64')
    # Generate seaborn plot
    g = sns.FacetGrid(df, hue=hue, palette="Set1", size=5, legend_out=False)
    g.map(plt.scatter, "$x_1$", "$x_2$", s=100, lw=.5, edgecolor="white")
    if hue != ' ':
        g.add_legend()  # customize legend
    # g.set_xticklabels([])
    # g.set_yticklabels([])
    g.ax.autoscale_view(True, True, True)
    plt.title(title)
    filename = os.path.join(
        root, os.path.basename(root) + "_scatter2D." + DEFAULT_EXT)
    plt.savefig(filename)
    logging.info('Figure saved %s', filename)
    plt.close()

    # 3D plot
    filename = os.path.join(
        root, os.path.basename(root) + "_scatter3D." + DEFAULT_EXT)
    if n_dim < 3:
        logging.warning(
            '%s not generated (data have less than 3 dimensions)', filename)
    else:
        try:
            from mpl_toolkits.mplot3d import Axes3D
            ax = plt.figure().gca(projection='3d')
            # ax.scatter(X[:,0], X[:,1], X[:,2], y, c=y, cmap='hot', s=100,
            #            linewidth=.5, edgecolor="white")
            palette = Palette(n_colors=len(np.unique(labels)))
            for _, label in enumerate(np.unique(labels)):
                idx = np.where(labels == label)[0]
                ax.plot(
                    data_in[:, 0][idx], data_in[:, 1][idx], data_in[:, 2][idx],
                    'o', c=palette.next(), label=str(label), mew=.5,
                    mec="white")

            ax.set_xlabel(r'$x_1$')
            ax.set_ylabel(r'$x_2$')
            ax.set_zlabel(r'$x_3$')
            ax.autoscale_view(True, True, True)
            ax.set_title(title)
            ax.legend(loc='upper left', numpoints=1, ncol=10, fontsize=8,
                      bbox_to_anchor=(0, 0))
            plt.savefig(filename)
            logging.info('Figure saved %s', filename)
            plt.close()
        except StandardError as e:
            logging.error('Error in 3D plot: %s', e)

    # seaborn pairplot
    n_cols = min(n_dim, 3)
    cols = ["$x_{}$".format(i + 1) for i in range(n_cols)]
    X = data_in[:, :3]
    idx = np.argsort(labels)
    df = pd.DataFrame(data=np.hstack((X[idx, :], labels[idx, np.newaxis])),
                      columns=cols + [hue]).astype(
                          dict(zip(cols, [float] * n_cols)))
    if df.dtypes[hue] != 'O':
        df[hue] = df[hue].astype('int64')
    g = sns.PairGrid(df, hue=hue, palette="Set1", vars=cols)
    g = g.map_diag(plt.hist)  # , palette="Set1")
    g = g.map_offdiag(plt.scatter, s=100, linewidth=.5, edgecolor="white")

    # g = sns.pairplot(df, hue=hue, palette="Set1",
    #    vars=["$x_1$","$x_2$","$x_3$"]), size=5)
    if hue != ' ':
        plt.legend(title=hue, bbox_to_anchor=(1.05, 1), loc=2,
                   borderaxespad=0., fontsize="large")
    plt.suptitle(title, x=0.6, y=1.01, fontsize="large")
    filename = os.path.join(
        root, os.path.basename(root) + "_pairgrid." + DEFAULT_EXT)
    g.savefig(filename)
    logging.info('Figure saved %s', filename)
    plt.close()


def voronoi(root, data_in, labels=None, true_labels=False, model=None):
    """Generate the Voronoi tessellation obtained from the clustering algorithm.

    This function generates the Voronoi tessellation obtained from the
    clustering algorithm applied on the data projected on a two-dimensional
    embedding. The plots will be saved into the appropriate folder of the
    tree-like structure created into the root folder.

    Parameters
    -----------
    root : string
        The root path for the output creation

    data_in : array of float, shape : (n_samples, n_dimensions)
        The low space embedding estimated by the dimensinality reduction and
        manifold learning algorithm.

    labels : array of int, shape : n_samples
        The result of the clustering step.

    true_labels : boolean [deprecated]
        Identify if labels contains true or estimated labels.

    model : sklearn or sklearn-like object
        An instance of the class that evaluates a step. In particular this must
        be a clustering model provided with the clusters_centers_ attribute
        (e.g. KMeans).
    """
    n_samples, _ = data_in.shape

    # Define plot color
    if labels is None:
        labels = np.zeros(n_samples, dtype=np.short)
        hue = ' '
    else:
        labels = np.asarray(labels)
        hue = 'Classes'

    title = title_from_filename(root)

    # Seaborn scatter Plot
    idx = np.argsort(labels)
    X = data_in[idx, :2]
    labels = labels[idx, np.newaxis]
    df = pd.DataFrame(
        data=np.hstack((X, labels)), columns=["$x_1$", "$x_2$", hue]).astype(
            {"$x_1$": float, "$x_2$": float})
    if df.dtypes[hue] != 'O':
        df[hue] = df[hue].astype('int64')
    # Generate seaborn plot
    g = sns.FacetGrid(df, hue=hue, palette="Set1", size=5, legend_out=False)
    g.map(plt.scatter, "$x_1$", "$x_2$", s=100, lw=.5, edgecolor="white")
    if hue != ' ':
        g.add_legend()  # customize legend
    g.ax.autoscale_view(True, True, True)
    plt.title(title)

    # Add centroids
    if hasattr(model, 'cluster_centers_'):
        plt.scatter(model.cluster_centers_[:, 0], model.cluster_centers_[:, 1],
                    s=100, marker='h', c='w')

    # Make and add to the Plot the decision boundary.
    # the number of points in that makes the background.
    # Reducing this will decrease the quality of the voronoi background
    npoints = 1000
    x_min, x_max = X[:, 0].min(), X[:, 0].max()
    y_min, y_max = X[:, 1].min(), X[:, 1].max()
    offset = (x_max - x_min) / 5. + (y_max - y_min) / 5.  # zoom out the plot
    xx, yy = np.meshgrid(np.linspace(x_min - offset, x_max + offset, npoints),
                         np.linspace(y_min - offset, y_max + offset, npoints))

    # Obtain labels for each point in mesh. Use last trained model.
    Z = model.predict(np.c_[xx.ravel(), yy.ravel()])
    # Put the result into a color plot
    Z = Z.reshape(xx.shape)

    plt.imshow(Z, interpolation='nearest',
               extent=(xx.min(), xx.max(), yy.min(), yy.max()),
               cmap=plt.get_cmap('Pastel1'), aspect='auto', origin='lower')

    plt.xlim([xx.min(), xx.max()])
    plt.ylim([yy.min(), yy.max()])

    filename = os.path.join(root, os.path.basename(root) + "." + DEFAULT_EXT)
    plt.savefig(filename)
    logging.info('Figure saved %s', filename)
    plt.close()


def tree(root, data_in, labels=None, index=None, model=None):
    """Generate the tree structure obtained from the clustering algorithm.

    This function generates the tree obtained from the clustering algorithm
    applied on the data. The plots will be saved into the appropriate folder of
    the tree-like structure created into the root folder.

    Parameters
    -----------
    root : string
        The root path for the output creation

    data_in : array of float, shape : (n_samples, n_dimensions)
        The low space embedding estimated by the dimensinality reduction and
        manifold learning algorithm.

    labels : array of int, shape : n_samples
        The result of the clustering step.

    index : list of integers (or strings)
        This is the samples identifier, if provided as first column (or row) of
        of the input file. Otherwise it is just an incremental range of size
        n_samples.

    model : sklearn or sklearn-like object
        An instance of the class that evaluates a step. In particular this must
        be a clustering model provided with the clusters_centers_ attribute
        (e.g. KMeans).
    """
    # see http://stackoverflow.com/questions/27386641/how-to-traverse-a-tree-from-sklearn-agglomerativeclustering
    # ii = itertools.count(X.shape[0])
    # [{'node_id': next(ii), 'left': x[0], 'right':x[1]} for x in model.children_]
    aa = []
    for ii, x in enumerate(model.children_):
        ii += data_in.shape[0]
        aa.append([ii, x[0]])
        aa.append([ii, x[1]])
    aa.append([None, ii])
    aa = np.array(aa)
    df = pd.DataFrame(aa).rename(columns=dict(zip(range(2), ['parent', 'name'])))
    # write sample names in the leaves
    lookup_table = dict(zip(np.arange(data_in.shape[0], dtype=float), index))
    df = df.applymap(lambda x: lookup_table.get(x, False) or float(x) if x is not None else x)
    table_filename = "/tmp/table{}.csv".format(time.time())
    df.to_csv(table_filename, index=False)
    
    # now it can be loaded to generate a D3.js tree
    with open(os.path.join(root, os.path.basename(root) + '_tree.html'), 'w') as f:
        svg_crowbar_path = os.path.join(adenine.__path__[0], 'core', 'template', 'svg-crowbar.js')
        f.write(D3_TREE % ("'%s'" % svg_crowbar_path, '"%s"' % table_filename))

    filename = os.path.join(root, os.path.basename(root) + '_tree.pdf')
    try:
        import itertools
        import pydot
        graph = pydot.Dot(graph_type='graph')

        if labels is None:
            labels = np.zeros(1, dtype=np.short)
            palette = Palette('hls', n_colors=np.unique(labels).shape[0])
            palette.palette[0] = (1.0, 1.0, 1.0)
        else:
            palette = Palette('hls', n_colors=np.unique(labels).shape[0])

        colors = dict(
            zip(np.unique(labels), np.arange(np.unique(labels).shape[0])))
        ii = itertools.count(data_in.shape[0])
        for _, x in enumerate(model.children_):
            root_node = next(ii)
            fillcolor = (lambda _:
                         palette.palette.as_hex()[colors[labels[x[_]]]]
                         if x[_] < labels.shape[0] else 'white')
            left_node = pydot.Node(
                str(index[x[0]] if x[0] < len(index) else x[0]),
                style="filled", fillcolor=fillcolor(0))
            right_node = pydot.Node(
                str(index[x[1]] if x[1] < len(index) else x[1]),
                style="filled", fillcolor=fillcolor(1))

            graph.add_node(left_node)
            graph.add_node(right_node)
            graph.add_edge(pydot.Edge(root_node, left_node))
            graph.add_edge(pydot.Edge(root_node, right_node))

        # graph.write_png(filename[:-2]+"ng")
        graph.write_pdf(filename)
        logging.info('Figure saved %s', filename)
    except StandardError as e:
        logging.critical('Cannot create %s. tb: %s', filename, e)


def dendrogram(root, data_in, labels=None, index=None, model=None, n_max=150):
    """Generate and save the dendrogram obtained from the clustering algorithm.

    This function generates the dendrogram obtained from the clustering
    algorithm applied on the data. The plots will be saved into the appropriate
    folder of the tree-like structure created into the root folder. The row
    colors of the heatmap are the either true or estimated data labels.

    Parameters
    -----------
    root : string
        The root path for the output creation

    data_in : array of float, shape : (n_samples, n_dimensions)
        The low space embedding estimated by the dimensinality reduction and
        manifold learning algorithm.

    labels : array of int, shape : n_samples
        The result of the clustering step.

    index : list of integers (or strings)
        This is the samples identifier, if provided as first column (or row) of
        of the input file. Otherwise it is just an incremental range of size
        n_samples.

    model : sklearn or sklearn-like object
        An instance of the class that evaluates a step. In particular this must
        be a clustering model provided with the clusters_centers_ attribute
        (e.g. KMeans).

    n_max : int, (INACTIVE)
        The maximum number of samples to include in the dendrogram.
        When the number of samples is bigger than n_max, only n_max samples
        randomly extracted from the dataset are represented. The random
        extraction is performed using
        sklearn.model_selection.StratifiedShuffleSplit
        (or sklearn.cross_validation.StratifiedShuffleSplit for legacy
        reasons).
    """
    # define col names
    col = ["$x_{" + str(i) + "}$" for i in np.arange(0, data_in.shape[1], 1)]
    df = pd.DataFrame(data=data_in, columns=col, index=index)

    # -- Code for row colors adapted from:
    # https://stanford.edu/~mwaskom/software/seaborn/examples/structured_heatmap.html
    # Create a custom palette to identify the classes
    if labels is None:
        labels = np.zeros(df.shape[0], dtype=np.short)
    else:
        mapping = dict(
            zip(np.unique(labels), np.arange(np.unique(labels).shape[0])))
        labels = np.vectorize(mapping.get)(labels)

    n_colors = np.unique(labels).shape[0]
    custom_pal = sns.color_palette("hls", n_colors)
    custom_lut = dict(zip(map(str, range(n_colors)), custom_pal))

    # Convert the palette to vectors that will be drawn on the matrix side
    custom_colors = pd.Series(map(str, labels)).map(custom_lut)

    # Create a custom colormap for the heatmap values
    cmap = sns.diverging_palette(220, 20, n=7, as_cmap=True)

    if model.affinity == 'precomputed':
        import scipy.spatial.distance as ssd
        from scipy.cluster.hierarchy import linkage
        # convert the redundant square matrix into a condensed one.
        # Even if the docs of scipy said so, linkage function does not
        # understand that the matrix is precomputed, unless it is 1-dimensional
        Z = linkage(ssd.squareform(data_in), method=model.linkage,
                    metric='euclidean')
        g = sns.clustermap(
            df, method=model.linkage, row_linkage=Z, col_linkage=Z,
            linewidths=.5, cmap=cmap)

    else:
        # workaround to a different name used for manhattan/cityblock distance
        if model.affinity == 'manhattan':
            model.affinity = 'cityblock'

        g = sns.clustermap(df, method=model.linkage, metric=model.affinity,
                           row_colors=custom_colors, linewidths=.5, cmap=cmap)

    plt.setp(g.ax_heatmap.yaxis.get_majorticklabels(), rotation=0, fontsize=5)
    filename = os.path.join(root, os.path.basename(root) +
                            '_dendrogram.' + DEFAULT_EXT)
    g.savefig(filename)
    logging.info('Figure saved %s', filename)
    plt.close()


def pcmagnitude(root, points, title='', ylabel=''):
    """Plot the trend of principal components magnitude.

    Parameters
    -----------
    root : string
        The root path for the output creation.

    points : array of float, shape : n_components
        This could be the explained variance ratio or the eigenvalues of the
        centered matrix, according to the PCA algorithm of choice, respectively
        PCA or KernelPCA.

    title : string
        Plot title.

    ylabel : string
        Y-axis label.
    """
    plt.plot(np.arange(1, len(points) + 1), points, '-o')
    plt.title(title)
    plt.grid('on')
    plt.ylabel(ylabel)
    plt.xlim([1, min(20, len(points) + 1)])  # Show maximum 20 components
    plt.ylim([0, 1])
    filename = os.path.join(root, os.path.basename(root) +
                            "_magnitude." + DEFAULT_EXT)
    plt.savefig(filename)
    plt.close()


def eigs(root, affinity, n_clusters=0, title='', ylabel='', normalised=True,
         n_components=20, filename=None, ylim='auto', rw=False):
    """Plot eigenvalues of the Laplacian associated to data affinity matrix.

    Parameters
    -----------
    root : string
        The root path for the output creation.

    affinity : array of float, shape : (n_samples, n_samples)
        The affinity matrix.

    n_clusters : int, optional
        The number of clusters.

    title : string, optional
        Plot title.

    ylabel : string, optional
        Y-axis label.

    normalised : boolean, optional, default True
        Choose whether to normalise the Laplacian matrix.

    n_components : int, optional, default 20
        Number of components to show in the plot.

    filename : None or str, optional, default None
        If not None, overrides default filename for saving the plot.

    ylim : 'auto', None, tuple or list, optional, default 'auto'
        If 'auto', choose the highest eigenvalue for the height of the plot.
        If None, plt.ylim is not called (matplotlib default is used).
        Otherwise, specify manually the desired ylim.

    rw : boolean, optional, default False
        Normalise the Laplacian matrix as the random walks point of view.
        This should be better suited with unclear data distributions.
    """
    # Efficient way to extract the main diagonal from a sparse matrix
    if isinstance(affinity, sp.sparse.csr.csr_matrix):
        dd = affinity.diagonal()
    else:  # or from a dense one
        dd = np.diag(affinity)
    W = affinity - np.diag(dd)
    D = np.diag([np.sum(x) for x in W])
    laplacian = D - W

    if rw:
        # compute normalised laplacian as random walks. Better with unclear
        # distributions
        aux = np.diag(1. / np.array([np.sum(x) for x in W]))
        laplacian = np.eye(laplacian.shape[0]) - np.dot(aux, W)
    elif normalised:
        # Compute the normalised Laplacian
        # aux = np.linalg.inv(np.diag([np.sqrt(np.sum(x)) for x in W]))
        aux = np.diag(1. / np.array([np.sqrt(np.sum(x)) for x in W]))
        laplacian = np.eye(laplacian.shape[0]) - (np.dot(np.dot(aux, W), aux))

    # TODO: replace the previous manual laplacian creation with sklearn utils.
    # Performance gain and np.allclose checks already performed with success.
    # from sklearn.utils import graph
    # laplacian = graph.graph_laplacian(affinity, normed=normalised)
    # warn: RW is not implemented in sklearn

    try:
        w = np.linalg.eigvals(laplacian)
        w = np.array(sorted(np.abs(w)))
        plt.plot(np.arange(1, len(w) + 1), w, '-o',
                 label='eigenvalues (sorted' +
                       (' and normalised rw)' if rw else
                        (' and normalised)' if normalised else ')')))
        plt.title(title)
        plt.grid('on')
        plt.ylabel(ylabel)
        plt.xlim([1, min(n_components, len(w) + 1)])  # Show max n_components
        if ylim == 'auto':
            plt.ylim((0, w[:min(n_components, len(w) + 1)][-1] +
                     2 * (w[:min(n_components, len(w) + 1)][-1] -
                          w[:min(n_components, len(w) + 1)][-2])))
        elif ylim is not None:
            plt.ylim(ylim)
        if n_clusters > 0:
            plt.axvline(x=n_clusters + .5, linestyle='--', color='r',
                        label='selected clusters')
        plt.legend(loc='upper left', numpoints=1, ncol=10, fontsize=8)
        # , bbox_to_anchor=(1, 1))
        if filename is None:
            filename = os.path.join(root, os.path.basename(root) +
                                    "_eigenvals." + DEFAULT_EXT)
        plt.savefig(filename)
    except np.linalg.LinAlgError:
        logging.critical("Error in plot_eigs: Affinity matrix contained "
                         "negative values. You can try by specifying "
                         "normalised=False")
    plt.close()
