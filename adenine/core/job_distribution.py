"""Master slave."""
from __future__ import print_function
import os
import imp
import logging
import shutil
import gzip
import numpy as np

from collections import deque
from six.moves import cPickle as pkl

from adenine.core import define_pipeline
from adenine.core.pipelines import pipe_worker
from adenine.utils import extra

try:
    from mpi4py import MPI

    COMM = MPI.COMM_WORLD
    RANK = COMM.Get_rank()
    NAME = MPI.Get_processor_name()

    IS_MPI_JOB = COMM.Get_size() > 1

except ImportError:
    # print("mpi4py module not found. MPI job distribution disabled.")
    COMM = None
    RANK = 0
    NAME = 'localhost'

    IS_MPI_JOB = False

# MAX_RESUBMISSIONS = 2
# constants to use as tags in communications
DO_WORK = 100
EXIT = 200


def master_dask(pipes, X):
    """Fit and transform/predict some pipelines on some data  using dask.
    """
    import dask
    from distributed import Client
    import multiprocessing as mp
    client = Client('cnode001:8786')

    jobs = []
    pipes_dump = {}

    [future] = client.scatter([X], broadcast=True)
    futures = [client.submit(pipe_worker, None, pipe, None, future) for pipe in pipes]
#    remote_X = client.scatter(X, broadcast=True)
#    ll = len(pipes)
#    futures = client.map(pipe_worker, *([None]*ll, pipes, [None]*ll, [remote_X]*ll))
#    res = client.gather(futures)
#    for i, r in enumerate(res):
#        pipes_dump['pipe'+str(i)] = res

    # Submit jobs
 #   for i, pipe in enumerate(pipes):
 #       pipe_id = 'pipe' + str(i)
 #       proc = client.submit(pipe_worker, *(None, pipe, None, remote_X)) #FIXME
 #       jobs.append(proc)
 #       logging.info("Job: %s submitted", pipe_id)
        # print("Job: %s submitted", pipe_id)

    res = client.gather(futures)
    for i, r in enumerate(res):
        pipes_dump['pipe'+str(i)] = res

    # Collect results
#    for i, proc in enumerate(jobs):
#        pipes_dump['pipe'+str(i)] = proc.result()
#    logging.info("%d jobs collected", i)
    print("%d jobs collected", len(jobs))

    # import joblib as jl
    # jl.Parallel(n_jobs=-1) \
    #     (jl.delayed(pipe_worker)(
    #         'pipe' + str(i), pipe, pipes_dump, X) for i, pipe in enumerate(
    #             pipes))

    return pipes_dump


def master_single_machine(pipes, X):
    """Fit and transform/predict some pipelines on some data (single machine).

    This function fits each pipeline in the input list on the provided data.
    The results are dumped into a pkl file as a dictionary of dictionaries of
    the form {'pipe_id': {'stepID' : [alg_name, level, params, data_out,
    data_in, model_obj, voronoi_suitable_object], ...}, ...}. The model_obj is
    the sklearn model which has been fit on the dataset, the
    voronoi_suitable_object is the very same model but fitted on just the first
    two dimensions of the dataset. If a pipeline fails for some reasons the
    content of the stepID key is a list of np.nan.

    Parameters
    -----------
    pipes : list of list of tuples
        Each tuple contains a label and a sklearn Pipeline object.
    X : array of float, shape : n_samples x n_features, default : ()
        The input data matrix.

    Returns
    -----------
    pipes_dump : dict
        Dictionary with the results of the computation.
    """
    # # FIXME
    return master_dask(pipes, X)

    import multiprocessing as mp
    # jobs = []
    manager = mp.Manager()
    pipes_dump = manager.dict()
    #
    # # Submit jobs
    # for i, pipe in enumerate(pipes):
    #     pipe_id = 'pipe' + str(i)
    #     proc = mp.Process(target=pipe_worker,
    #                       args=(pipe_id, pipe, pipes_dump, X))
    #     jobs.append(proc)
    #     proc.start()
    #     logging.info("Job: %s submitted", pipe_id)
    #
    # # Collect results
    # count = 0
    # for proc in jobs:
    #     proc.join()
    #     count += 1
    # logging.info("%d jobs collected", count)

    # import joblib as jl
    # jl.Parallel(n_jobs=-1) \
    #     (jl.delayed(pipe_worker)(
    #         'pipe' + str(i), pipe, pipes_dump, X) for i, pipe in enumerate(
    #             pipes))


    import distributed.joblib
    from joblib import Parallel, parallel_backend
    import joblib as jl
    # with parallel_backend('dask.distributed', scheduler_host='localhost:8786'):
    with parallel_backend('dask.distributed', scheduler_host='cnode001:8786', scatter=[X]):
        out = jl.Parallel() \
        (jl.delayed(pipe_worker)(None, pipe, None, X) for i, pipe in enumerate(pipes))

    for i, res in enumerate(out):
        pipes_dump['pipe'+str(i)] = res
    print('{} jobs collected'.format(len(pipes_dump.keys())))

    return dict(pipes_dump)


@extra.timed
def master(config):
    """Distribute pipelines with mpi4py or multiprocessing."""
    # Pipeline definition
    pipes = define_pipeline.parse_steps(
        [config.step0, config.step1,
         config.step2, config.step3])

    if not IS_MPI_JOB:
        return master_single_machine(pipes, config.X)

    # RUN PIPELINES
    nprocs = COMM.Get_size()
    # print(NAME + ": start running slaves", nprocs, NAME)
    queue = deque(list(enumerate(pipes)))

    pipe_dump = dict()
    count = 0
    n_pipes = len(queue)

    # seed the slaves by sending work to each processor
    for rankk in range(1, min(nprocs, n_pipes)):
        pipe_tuple = queue.popleft()
        COMM.send(pipe_tuple, dest=rankk, tag=DO_WORK)
        # print(NAME + ": send to rank", rankk)

    # loop until there's no more work to do. If queue is empty skips the loop.
    while queue:
        pipe_tuple = queue.popleft()
        # receive result from slave
        status = MPI.Status()
        pipe_id, step_dump = COMM.recv(
            source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status)
        pipe_dump[pipe_id] = step_dump
        count += 1
        # send to the same slave new work
        COMM.send(pipe_tuple, dest=status.source, tag=DO_WORK)

    # there's no more work to do, so receive all the results from the slaves
    for rankk in range(1, min(nprocs, n_pipes)):
        # print(NAME + ": master - waiting from", rankk)
        status = MPI.Status()
        pipe_id, step_dump = COMM.recv(
            source=MPI.ANY_SOURCE, tag=MPI.ANY_TAG, status=status)
        pipe_dump[pipe_id] = step_dump
        count += 1

    # tell all the slaves to exit by sending an empty message with the EXIT_TAG
    for rankk in range(1, nprocs):
        # print(NAME + ": master - killing", rankk)
        COMM.send(0, dest=rankk, tag=EXIT)

    # print(NAME + ": terminating master")
    return pipe_dump


def slave(X):
    """Pipeline evaluation.

    Parameters
    ----------
    X : array of float, shape : n_samples x n_features, default : ()
        The input data matrix.
    """
    try:
        while True:
            status_ = MPI.Status()
            received = COMM.recv(source=0, tag=MPI.ANY_TAG, status=status_)
            # check the tag of the received message
            if status_.tag == EXIT:
                return
            # do the work
            i, pipe = received
            # print(NAME + ": slave received", RANK, i)
            pipe_id = 'pipe' + str(i)
            step_dump = pipe_worker(
                pipe_id, pipe, None, X)
            COMM.send((pipe_id, step_dump), dest=0, tag=0)

    except StandardError as exc:
        print("Quitting ... TB:", str(exc))


def main(config_file):
    """Generate the pipelines."""

    if RANK == 0:
        # Load the configuration file
        config_path = os.path.abspath(config_file)

        # For some reason, it must be atomic
        imp.acquire_lock()
        config = imp.load_source('ade_config', config_path)
        imp.release_lock()

    # this barrier prevents the slave to re-download the same GEO
    # dataset if not locally present
    if IS_MPI_JOB:
        # Wait for all jobs to end
        COMM.barrier()

    if RANK != 0:
        # Load the configuration file
        config_path = os.path.abspath(config_file)

        # For some reason, it must be atomic
        imp.acquire_lock()
        config = imp.load_source('ade_config', config_path)
        imp.release_lock()

    if hasattr(config, 'use_compression'):
        use_compression = config.use_compression
    else:
        use_compression = False

    extra.set_module_defaults(
        config, {
            'step0': {'Impute': [False]},
            'step1': {'None': [True]},
            'step2': {'None': [True]},
            'step3': {'None': [False]},
            'exp_tag': 'debug',
            'output_root_folder': 'results',
            'verbose': False})

    # Read the variables from the config file
    X = config.X

    if RANK == 0:
        # Get the experiment tag and the output root folder
        exp_tag, root = config.exp_tag, config.output_root_folder
        if not os.path.exists(root):
            os.makedirs(root)

        filename = '_'.join(('ade', exp_tag, extra.get_time()))
        logfile = os.path.join(root, filename + '.log')
        logging.basicConfig(filename=logfile, level=logging.INFO, filemode='w',
                            format='%(levelname)s (%(name)s): %(message)s')
        root_logger = logging.getLogger()
        lsh = logging.StreamHandler()
        lsh.setLevel(logging.DEBUG if config.verbose else logging.ERROR)
        lsh.setFormatter(
            logging.Formatter('%(levelname)s (%(name)s): %(message)s'))
        root_logger.addHandler(lsh)
        pipes_dump = master(config)
    else:
        slave(X)

    if IS_MPI_JOB:
        # Wait for all jobs to end
        COMM.barrier()

    if RANK == 0:
        # Output Name
        outfile = filename
        outfolder = os.path.join(root, outfile)

        # Create exp folder into the root folder
        os.makedirs(outfolder)

        # pkl Dump
        logging.info('Saving Adenine results...')
        if use_compression:
            with gzip.open(os.path.join(outfolder, outfile + '.pkl.tz'),
                           'wb') as out:
                pkl.dump(pipes_dump, out)
            logging.info("Dump : %s", os.path.join(outfolder, outfile + '.pkl.tz'))
        else:
            with open(os.path.join(outfolder, outfile + '.pkl'), 'wb') as out:
                pkl.dump(pipes_dump, out)
                logging.info("Dump : %s", os.path.join(outfolder, outfile + '.pkl'))

        # Retrieve info from the config file
        _index = config.index if hasattr(config, 'index') \
            else np.arange(X.shape[0])
        _y = config.y if hasattr(config, 'y') else None
        if use_compression:
            with gzip.open(os.path.join(outfolder, '__data.pkl.tz'), 'wb') as out:
                pkl.dump({'X': X, 'y': _y, 'index': _index}, out)
            logging.info("Dump : %s", os.path.join(outfolder, '__data.pkl.tz'))
        else:
            with open(os.path.join(outfolder, '__data.pkl'), 'wb') as out:
                pkl.dump({'X': X, 'y': _y, 'index': _index}, out)
            logging.info("Dump : %s", os.path.join(outfolder, '__data.pkl'))

        # Copy the ade_config just used into the outFolder
        shutil.copy(config_path, os.path.join(outfolder, 'ade_config.py'))

        root_logger.handlers[0].close()

        # Move the logging file into the outFolder
        shutil.move(logfile, outfolder)
