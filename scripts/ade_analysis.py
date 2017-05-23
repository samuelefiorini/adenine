#!/usr/bin/env python
"""Adenine analysis script."""
######################################################################
# Copyright (C) 2016 Samuele Fiorini, Federico Tomasi, Annalisa Barla
#
# FreeBSD License
######################################################################

from __future__ import print_function

import imp
import sys
import os
import time
import logging
import argparse
import gzip
import numpy as np
try:
    import cPickle as pkl
except:
    import pickle as pkl

from adenine.core import analyze_results
from adenine.utils import extra


def init_main():
    """Init analysis main."""
    from adenine import __version__
    parser = argparse.ArgumentParser(description='Adenine script for '
                                                 'analysing pipelines.')
    parser.add_argument('--version', action='version',
                        version='%(prog)s v' + __version__)
    parser.add_argument("result_folder", help="specify results directory")
    args = parser.parse_args()

    root_folder = args.result_folder
    filename = [f for f in os.listdir(root_folder)
                if os.path.isfile(os.path.join(root_folder, f)) and
                '.pkl' in f  and f != "__data.pkl"]
    if not filename:
        sys.stderr.write("No .pkl file found in {}. Aborting...\n"
                         .format(root_folder))
        sys.exit(-1)

    # Run analysis
    # print("Starting the analysis of {}".format(filename))
    main(os.path.join(os.path.abspath(root_folder), filename[0]))


def main(dumpfile):
    """Analyze the pipelines."""
    # Load the configuration file
    config_path = os.path.dirname(dumpfile)
    config_path = os.path.join(os.path.abspath(config_path), 'ade_config.py')
    config = imp.load_source('ade_config', config_path)
    extra.set_module_defaults(config, {'file_format': 'pdf',
                                       'plotting_context': 'paper',
                                       'verbose': False})
    if hasattr(config, 'use_compression'):
        use_compression = config.use_compression
    else:
        use_compression = False

    # Load the results used with ade_run.py
    try:
        if use_compression:
            with gzip.open(os.path.join(os.path.dirname(dumpfile),
                                        '__data.pkl.tz'), 'r') as fdata:
                data_X_y_index = pkl.load(fdata)
                data = data_X_y_index['X']
                labels = data_X_y_index['y']
                index = data_X_y_index['index']
        else:
            with open(os.path.join(os.path.dirname(dumpfile),
                                   '__data.pkl'), 'r') as fdata:
                data_X_y_index = pkl.load(fdata)
                data = data_X_y_index['X']
                labels = data_X_y_index['y']
                index = data_X_y_index['index']
    except IOError:
        if use_compression:
            data_filename = '__data.pkl.tz'
        else:
            data_filename = '__data.pkl'

        sys.stderr.write("Cannot load {} Reloading data from "
                         "config file ...".format(data_filename))
        data = config.X
        labels = config.y
        index = config.index if hasattr(config, 'index') \
            else np.arange(data.shape[0])

    # Read the feature names from the config file
    feat_names = config.feat_names if hasattr(config, 'feat_names') \
        else np.arange(data.shape[1])
    # Initialize the log file
    filename = 'results_' + os.path.basename(dumpfile)[0:-7]
    logfile = os.path.join(os.path.dirname(dumpfile), filename + '.log')
    logging.basicConfig(filename=logfile, level=logging.INFO, filemode='w',
                        format='%(levelname)s (%(name)s): %(message)s')
    root_logger = logging.getLogger()
    lsh = logging.StreamHandler()
    lsh.setLevel(20 if config.verbose else logging.ERROR)
    lsh.setFormatter(
        logging.Formatter('%(levelname)s (%(name)s): %(message)s'))
    root_logger.addHandler(lsh)

    tic = time.time()
    print("\nUnpickling output ...", end=' ')
    # Load the results
    if use_compression:
        with gzip.open(dumpfile, 'r') as fres:
            res = pkl.load(fres)
    else:
        with open(dumpfile, 'r') as fres:
            res = pkl.load(fres)

    print("done: {} s".format(extra.sec_to_time(time.time() - tic)))

    # Analyze the pipelines
    analyze_results.analyze(input_dict=res, root=os.path.dirname(dumpfile),
                            y=labels, feat_names=feat_names, index=index,
                            plotting_context=config.plotting_context,
                            file_format=config.file_format)

    root_logger.handlers[0].close()


if __name__ == '__main__':
    init_main()
