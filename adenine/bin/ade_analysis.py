#!/usr/bin/python -W ignore::DeprecationWarning
# -*- coding: utf-8 -*-

import imp, sys, os
import time
import logging
import cPickle as pkl
from adenine.core import analyze_results

def main(dumpfile):

    # Load the configuration file
    config_path = os.path.dirname(dumpfile)
    config_path = os.path.join(os.path.abspath(config_path), 'ade_config.py')
    config = imp.load_source('ade_config', config_path)

    # Read the variables from the config file
    X, y, feat_names, class_names = config.X, config.y, config.feat_names, config.class_names

    # Initialize the log file
    fileName = 'results_'+os.path.basename(dumpfile)[0:-4]
    logFileName = os.path.join(os.path.dirname(dumpfile), fileName+'.log')
    logging.basicConfig(filename=logFileName, level=logging.INFO, filemode='w')

    # Load the results
    with open(dumpfile, 'r') as f:
        res = pkl.load(f)

    tic = time.time()
    # Analyze the pipelines
    analyze_results.start(inputDict=res, rootFolder=os.path.dirname(dumpfile), y=y, feat_names=feat_names, class_names=class_names)
    tac = time.time()
    print("\n\nanalyze_results.start: Elapsed time : {}".format(tac-tic))



# ----------------------------  RUN MAIN ---------------------------- #
if __name__ == '__main__':

    if len(sys.argv) < 2:
        print("USAGE: ade_analysis.py <RESULTS_FOLDER> ")
        sys.exit(-1)
    else:
        fileNames = [ f for f in os.listdir(sys.argv[1]) if os.path.isfile(os.path.join(sys.argv[1],f)) ]
        found = False
        for f in fileNames:
            if f.endswith('.pkl'):
                found, fileName = True, f
                break

        if not found:
            print("No .pkl file found in {}".format(sys.argv[1]))
            sys.exit(-1)
        else:
            # print("Starting the analysis of {}".format(fileName))
            main(os.path.join(sys.argv[1],fileName)) # Run analysis