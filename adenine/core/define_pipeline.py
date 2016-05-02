#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import numpy as np
from adenine.utils.extra import modified_cartesian, ensure_list

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import Normalizer
from sklearn.decomposition import PCA
from sklearn.decomposition import RandomizedPCA
from sklearn.decomposition import IncrementalPCA
from sklearn.decomposition import KernelPCA
from sklearn.manifold import Isomap
from sklearn.manifold import LocallyLinearEmbedding
from sklearn.manifold import SpectralEmbedding
from sklearn.manifold import MDS
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
from sklearn.cluster import AffinityPropagation
from sklearn.cluster import MeanShift
from sklearn.cluster import SpectralClustering
from sklearn.cluster import AgglomerativeClustering

from adenine.utils.extensions import DummyNone
from adenine.utils.extensions import Imputer
from adenine.utils.extensions import GridSearchCV
from adenine.utils.extensions import silhouette_score


def parse_preproc(key, content):
        """Parse the options of the preprocessing step.

        This function parses the preprocessing step coded as dictionary in the ade_config file.

        Parameters
        -----------
        key : {'None', 'Recenter', 'Standardize', 'Normalize', 'MinMax'}
            The type of selected preprocessing step.

        content : list, len : 2
            A list containing the On/Off flag and a nested list of extra parameters (e.g. [min,max] for Min-Max scaling).

        Returns
        -----------
        pptpl : tuple
            A tuple made like that ('PreprocName', preprocObj), where preprocObj is an sklearn 'transforms' (i.e. it has bot a .fit and .transform method).
        """
        if key.lower() == 'none':
            pp = DummyNone()
        elif key.lower() == 'recenter':
            pp = StandardScaler(with_mean=True, with_std=False)
        elif key.lower() == 'standardize':
            pp = StandardScaler(with_mean=True, with_std=True)
        elif key.lower() == 'normalize':
            pp = Normalizer(norm=content[1][0])
        elif key.lower() == 'minmax':
            pp = MinMaxScaler(feature_range=(content[1][0], content[1][1]))
        else:
            pp = DummyNone()
        return (key, pp)

def parse_dimred(key, content):
    """Parse the options of the dimensionality reduction step.

    This function does the same as parse_preproc but works on the dimensionality reduction & manifold learning options.

    Parameters
    -----------
    key : {'None', 'PCA', 'KernelPCA', 'Isomap', 'LLE', 'SE', 'MDS', 'tSNE'}
        The selected dimensionality reduction algorithm.

    content : list, len : 2
        A list containing the On/Off flag and a nested list of extra parameters (e.g. ['rbf,'poly'] for KernelPCA).

    Returns
    -----------
    drtpl : tuple
        A tuple made like that ('DimRedName', dimredObj), where dimredObj is an sklearn 'transforms' (i.e. it has bot a .fit and .transform method).
    """
    if key.lower() == 'none':
        dr = DummyNone()
    elif key.lower() == 'pca':
        dr = PCA() # this by default takes all the components it can
    elif key.lower() == 'incrementalpca':
        dr = IncrementalPCA()
    elif key.lower() == 'randomizedpca':
        dr = RandomizedPCA()
    elif key.lower() == 'kernelpca':
        dr = KernelPCA(kernel=content, n_components=None)
    elif key.lower() == 'isomap':
        dr = Isomap()
    elif key.lower() == 'lle':
        dr = LocallyLinearEmbedding(method=content)
    elif key.lower() == 'ltsa':
        dr = LocallyLinearEmbedding(method=content)
    elif key.lower() == 'se':
        dr = SpectralEmbedding()
    elif key.lower() == 'mds':
        dr = MDS(metric=(content != 'nonmetric'))
    elif key.lower() == 'tsne':
        dr = TSNE(n_components=3)
    else:
        dr = DummyNone()
    return (key, dr)


def parse_clustering(key, content):
    """Parse the options of the clustering step.

    This function does the same as parse_preproc but works on the clustering options.

    Parameters
    -----------
    key : {'KMeans', 'KernelKMeans', 'AP', 'MS', 'Spectral', 'Hierarchical'}
        The selected dimensionality reduction algorithm.

    content : list, len : 2
        A list containing the On/Off flag and a nested list of extra parameters (e.g. ['rbf,'poly'] for KernelKMeans).

    Returns
    -----------
    cltpl : tuple
        A tuple made like that ('ClusteringName', clustObj), where clustObj implements the .fit method.
    """
    if content.get('n_clusters', '') == 'auto' or content.get('preference', '') == 'auto':
        # Wrapper class that automatically detects the best number of clusters via 10-Fold CV
        content.pop('n_clusters','')
        content.pop('preference','')

        kwargs = {'param_grid': [], 'n_jobs': -1,
                  'scoring': silhouette_score, 'cv': 10}

        if key.lower() == 'kmeans':
            content.setdefault('init', 'k-means++')
            content.setdefault('n_jobs', 1)
            kwargs['estimator'] = KMeans(**content)
        elif key.lower() == 'ap':
            kwargs['estimator'] = AffinityPropagation(**content)
            kwargs['affinity'] = kwargs['estimator'].affinity
        else:
            logging.warning("n_clusters = 'auto' specified outside kmeans or ap."
                            " Creating GridSearchCV pipeline anyway ...")
        cl = GridSearchCV(**kwargs)

    else:
        if key.lower() == 'kmeans':
            content.setdefault('n_jobs', -1)
            cl = KMeans(**content)
        elif key.lower() == 'ap':
            content.setdefault('preference', 1)
            cl = AffinityPropagation(**content)
        elif key.lower() == 'ms':
            cl = MeanShift(**content)
        elif key.lower() == 'spectral':
            cl = SpectralClustering(**content)
        elif key.lower() == 'hierarchical':
            cl = AgglomerativeClustering(**content)
        else:
            cl = DummyNone()
    return (key, cl)

def parse_steps(steps):
    """Parse the steps and create the pipelines.

    This function parses the steps coded as dictionaries in the ade_config files and creates a sklearn pipeline objects for each combination of imputing -> preprocessing -> dimensinality reduction -> clustering algorithms.

    A typical step may be of the following form:
        stepX = {'Algorithm': [On/Off flag, [variant0, ...]]}
    where On/Off flag = {True, False} and variantX = 'string'.

    Parameters
    -----------
    steps : list of dictionaries
        A list of (usually 4) dictionaries that contains the details of the pipelines to implement.

    Returns
    -----------
    pipes : list of sklearn.pipeline.Pipeline
        The returned list must contain every possible combination of imputing -> preprocessing -> dimensionality reduction -> clustering algorithms. The maximum number of pipelines that could be generated is 20, even if the number of combinations is higher.
    """
    max_n_pipes = 100 # avoiding unclear (too-long) outputs
    pipes = []       # a list of list of tuples input of sklearn Pipeline
    imputing, preproc, dimred, clustering = steps[:4]

    # Parse the imputing options
    i_lst_of_tpls = []
    if imputing['Impute'][0]: # On/Off flag
        for name in imputing['Replacement']:
            imp = Imputer(missing_values=imputing['Missing'][0],
                          strategy=name)
            i_lst_of_tpls.append(("Impute_"+name, imp))

    # Parse the preprocessing options
    pp_lst_of_tpls = []
    for key in list(preproc.keys()):
        if preproc[key][0]: # On/Off flag
            pp_lst_of_tpls.append(parse_preproc(key, preproc[key]))

    # Parse the dimensionality reduction & manifold learning options
    dr_lst_of_tpls = []
    for key in list(dimred.keys()):
        if dimred[key][0]: # On/Off flag
            if len(dimred[key]) > 1:# For each variant (e.g. 'rbf' or
                for k in dimred[key][1]: # 'poly' for KernelPCA)
                    dr_lst_of_tpls.append(parse_dimred(key, k))
            else:
                dr_lst_of_tpls.append(parse_dimred(key, dimred[key]))

    # Parse the clustering options
    cl_lst_of_tpls = []
    for key in list(clustering.keys()):
        if clustering[key][0]: # On/Off flag
            if len(clustering[key]) > 1: # Discriminate from just flag or flag + args
                _dict_content = clustering[key][1]
                # for ll in modified_cartesian(*map(ensure_list,list(_dict_content.itervalues()))):
                for ll in modified_cartesian(*list(map(ensure_list,list(_dict_content.values())))): # python3 TODO: try except here
                    _single_content = {__k: __v for __k, __v in zip(list(_dict_content), ll)}
                    if not (_single_content.get('affinity','') in ['manhattan', 'precomputed'] and _single_content.get('linkage','') == 'ward'):
                        # print _single_content
                        cl_lst_of_tpls.append(parse_clustering(key, _single_content))

            else: # just flag case
                cl_lst_of_tpls.append(parse_clustering(key, dict()))


    # Generate the list of list of tuples (i.e. the list of pipelines)
    pipes = modified_cartesian(i_lst_of_tpls, pp_lst_of_tpls, dr_lst_of_tpls, cl_lst_of_tpls, pipes_mode=True)
    for pipe in pipes:
        logging.info("Generated pipeline: \n {} \n".format(pipe))
    logging.info("*** {} pipeline(s) generated ***".format(len(pipes)))

    # Get only the first max_n_pipes
    if len(pipes) > max_n_pipes:
        logging.warning("Maximum number of pipelines reached. I'm keeping the first {}".format(max_n_pipes))
        pipes = pipes[0:max_n_pipes]

    return pipes
