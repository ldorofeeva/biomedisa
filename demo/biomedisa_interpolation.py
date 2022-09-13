#!/usr/bin/python3
##########################################################################
##                                                                      ##
##  Copyright (c) 2022 Philipp Lösel. All rights reserved.              ##
##                                                                      ##
##  This file is part of the open source project biomedisa.             ##
##                                                                      ##
##  Licensed under the European Union Public Licence (EUPL)             ##
##  v1.2, or - as soon as they will be approved by the                  ##
##  European Commission - subsequent versions of the EUPL;              ##
##                                                                      ##
##  You may redistribute it and/or modify it under the terms            ##
##  of the EUPL v1.2. You may not use this work except in               ##
##  compliance with this Licence.                                       ##
##                                                                      ##
##  You can obtain a copy of the Licence at:                            ##
##                                                                      ##
##  https://joinup.ec.europa.eu/page/eupl-text-11-12                    ##
##                                                                      ##
##  Unless required by applicable law or agreed to in                   ##
##  writing, software distributed under the Licence is                  ##
##  distributed on an "AS IS" basis, WITHOUT WARRANTIES                 ##
##  OR CONDITIONS OF ANY KIND, either express or implied.               ##
##                                                                      ##
##  See the Licence for the specific language governing                 ##
##  permissions and limitations under the Licence.                      ##
##                                                                      ##
##########################################################################

import sys, os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
from biomedisa_features.biomedisa_helper import (_get_platform, smooth_img_3x3,
    pre_processing, _error_, read_labeled_slices, read_labeled_slices_allx,
    read_indices_allx, predict_blocksize)
from multiprocessing import freeze_support
import numpy as np
import time

class Biomedisa(object):
     pass

class build_label(object):
     pass

if __name__ == '__main__':
    freeze_support()

    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    if rank == 0:

        # create biomedisa
        bm = Biomedisa()

        # time
        bm.TIC = time.time()

        # path to data
        bm.path_to_data = sys.argv[1]
        bm.path_to_labels = sys.argv[2]

        # arguments
        bm.label = build_label()
        bm.label.only = 'all'
        bm.label.ignore = 'none'
        bm.label.nbrw = 10
        bm.label.sorw = 4000
        bm.label.compression = True
        bm.label.uncertainty = True if any(x in sys.argv for x in ['--uncertainty','-uq']) else False
        bm.label.allaxis = 1 if '-allx' in sys.argv else 0
        bm.label.smooth = 0
        bm.denoise = True if any(x in sys.argv for x in ['--denoise','-d']) else False
        bm.platform = None
        bm.process = 'biomedisa_interpolation'
        bm.django_env = False
        for i, val in enumerate(sys.argv):
            if val in ['--smooth','-s']:
                bm.label.smooth = int(sys.argv[i+1])
            elif val in ['--nbrw']:
                bm.label.nbrw = int(sys.argv[i+1])
            elif val in ['--sorw']:
                bm.label.sorw = int(sys.argv[i+1])
            elif val in ['--platform','-p']:
                bm.platform = str(sys.argv[i+1])

        # load and preprocess data
        bm = pre_processing(bm)

        # get platform
        bm = _get_platform(bm)

        # smooth, uncertainty and allx are not supported for opencl
        if bm.success and bm.platform.split('_')[0] == 'opencl':
            if bm.label.smooth:
                bm.label.smooth = 0
                print('Warning: Smoothing is not yet supported for opencl. Process starts without smoothing.')
            if bm.label.uncertainty:
                bm.label.uncertainty = False
                print('Warning: Uncertainty is not yet supported for opencl. Process starts without uncertainty.')
            if bm.label.allaxis:
                bm.success = False
                print('Error: Allx is not yet supported for opencl.')

        if not bm.success:

            # send not executable
            for dest in range(1, size):
                comm.send(bm.success, dest=dest, tag=0)

        else:

            # create path_to_final
            filename, extension = os.path.splitext(os.path.basename(bm.path_to_data))
            if extension == '.gz':
                filename = filename[:-4]
            filename = 'final.' + filename
            bm.path_to_final = bm.path_to_data.replace(os.path.basename(bm.path_to_data), filename + bm.final_image_type)

            # path_to_uq and path_to_smooth
            filename, extension = os.path.splitext(bm.path_to_final)
            if extension == '.gz':
                filename = filename[:-4]
            bm.path_to_smooth = filename + '.smooth' + bm.final_image_type
            bm.path_to_uq = filename + '.uncertainty.tif'

            # data type
            if bm.data.dtype == 'uint8':
                pass
            elif bm.data.dtype == 'int8':
                bm.data = bm.data.astype(np.int16)
                bm.data += 128
                bm.data = bm.data.astype(np.uint8)
            else:
                bm.data = bm.data.astype(float)
                bm.data -= np.amin(bm.data)
                bm.data /= np.amax(bm.data)
                bm.data *= 255.0
                bm.data = bm.data.astype(np.float32)

            # denoise image data
            if bm.denoise:
                bm.data = smooth_img_3x3(bm.data)

            # image size
            bm.imageSize = int(bm.data.nbytes * 10e-7)

            # add boundaries
            zsh, ysh, xsh = bm.data.shape
            tmp = np.zeros((1+zsh+1, 1+ysh+1, 1+xsh+1), dtype=bm.labelData.dtype)
            tmp[1:-1, 1:-1, 1:-1] = bm.labelData
            bm.labelData = tmp.copy(order='C')
            tmp = np.zeros((1+zsh+1, 1+ysh+1, 1+xsh+1), dtype=bm.data.dtype)
            tmp[1:-1, 1:-1, 1:-1] = bm.data
            bm.data = tmp.copy(order='C')
            bm.zsh, bm.ysh, bm.xsh = bm.data.shape

            # check if labeled slices are adjacent
            if bm.label.allaxis:
                bm.indices = []
                indices_tmp = read_indices_allx(bm.labelData, 0)
                bm.indices.extend(indices_tmp)
                tmp = np.swapaxes(bm.labelData, 0, 1)
                tmp = np.ascontiguousarray(tmp)
                indices_tmp = read_indices_allx(tmp, 1)
                bm.indices.extend(indices_tmp)
                tmp = np.swapaxes(tmp, 0, 2)
                tmp = np.ascontiguousarray(tmp)
                indices_tmp = read_indices_allx(tmp, 2)
                bm.indices.extend(indices_tmp)

                # labels must not be adjacent
                neighbours = False
                for k in range(3):
                    sub_indices = [x for (x, y) in bm.indices if y == k]
                    sub_indices_minus_one = [x - 1 for x in sub_indices]
                    if any(i in sub_indices for i in sub_indices_minus_one):
                        neighbours = True
                if neighbours:
                    message = 'At least one empty slice between labels required.'
                    bm = _error_(bm, message)

            # send executable
            for dest in range(1, size):
                comm.send(bm.success, dest=dest, tag=0)

            if bm.success:

                # When is domain decomposition faster?
                bm = predict_blocksize(bm)
                nbytes = (bm.argmax_z - bm.argmin_z) * (bm.argmax_y - bm.argmin_y) * (bm.argmax_x - bm.argmin_x) * 4

                # small or large
                if nbytes * bm.nol < 1e10 and nbytes < 2e9:

                    # send "small" to childs
                    for dest in range(1, size):
                        comm.send(1, dest=dest, tag=1)

                    # reduce blocksize
                    bm.data = np.copy(bm.data[bm.argmin_z:bm.argmax_z, bm.argmin_y:bm.argmax_y, bm.argmin_x:bm.argmax_x], order='C')
                    bm.labelData = np.copy(bm.labelData[bm.argmin_z:bm.argmax_z, bm.argmin_y:bm.argmax_y, bm.argmin_x:bm.argmax_x], order='C')

                    # read labeled slices
                    if bm.label.allaxis:
                        bm.indices, bm.labels = [], []
                        indices_tmp, labels_tmp = read_labeled_slices_allx(bm.labelData, 0)
                        bm.indices.extend(indices_tmp)
                        bm.labels.append(labels_tmp)
                        tmp = np.swapaxes(bm.labelData, 0, 1)
                        tmp = np.ascontiguousarray(tmp)
                        indices_tmp, labels_tmp = read_labeled_slices_allx(tmp, 1)
                        bm.indices.extend(indices_tmp)
                        bm.labels.append(labels_tmp)
                        tmp = np.swapaxes(tmp, 0, 2)
                        tmp = np.ascontiguousarray(tmp)
                        indices_tmp, labels_tmp = read_labeled_slices_allx(tmp, 2)
                        bm.indices.extend(indices_tmp)
                        bm.labels.append(labels_tmp)
                    else:
                        bm.indices, bm.labels = read_labeled_slices(bm.labelData)

                    # number of ngpus
                    ngpus = min(bm.available_devices, len(bm.indices), size)

                    # send number of GPUs to childs
                    for dest in range(1, size):
                        comm.send(ngpus, dest=dest, tag=2)

                    # create subcommunicator
                    sub_comm = MPI.Comm.Split(comm, 1, rank)

                    from biomedisa_small import _diffusion_child
                    _diffusion_child(sub_comm, bm)

                else:

                    # send "large" to childs
                    for dest in range(1, size):
                        comm.send(0, dest=dest, tag=1)

                    # number of ngpus
                    ngpus = min(bm.available_devices, (bm.argmax_z - bm.argmin_z) // 100, size)
                    ngpus = max(ngpus, 1)

                    # send number of GPUs to childs
                    for dest in range(1, size):
                        comm.send(ngpus, dest=dest, tag=2)

                    # create subcommunicator
                    sub_comm = MPI.Comm.Split(comm, 1, rank)

                    from biomedisa_large import _diffusion_child
                    _diffusion_child(sub_comm, bm)

    else:

        # check if executable
        executable = comm.recv(source=0, tag=0)

        if executable:

            # get small or large
            small = comm.recv(source=0, tag=1)

            # get number of gpus
            ngpus = comm.recv(source=0, tag=2)

            # create sub communicator
            if rank >= ngpus:
                sub_comm = MPI.Comm.Split(comm, 0, rank)     # set process to idle
            else:
                sub_comm = MPI.Comm.Split(comm, 1, rank)

                if small:
                    from biomedisa_small import _diffusion_child
                    _diffusion_child(sub_comm)
                else:
                    from biomedisa_large import _diffusion_child
                    _diffusion_child(sub_comm)

