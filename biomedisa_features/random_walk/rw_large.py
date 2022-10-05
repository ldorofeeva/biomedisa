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

import django
django.setup()
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from biomedisa_app.models import Upload, Profile
from biomedisa_app.views import send_notification, send_error_message
from biomedisa_features.biomedisa_helper import (_get_device, save_data, _error_, unique_file_path,
    splitlargedata, read_labeled_slices_allx_large, read_labeled_slices_large, sendToChildLarge)
from biomedisa_features.active_contour import active_contour
from biomedisa_features.remove_outlier import remove_outlier
from biomedisa_features.create_slices import create_slices
from biomedisa_app.config import config
from multiprocessing import Process

from mpi4py import MPI
import os, sys
import numpy as np
import time
import socket
import math

if config['OS'] == 'linux':
    from redis import Redis
    from rq import Queue

def _diffusion_child(comm, bm=None):

    rank = comm.Get_rank()
    ngpus = comm.Get_size()

    nodename = socket.gethostname()
    name = '%s %s' %(nodename, rank)
    print(name)

    if rank == 0:

        # reduce blocksize
        bm.data = np.copy(bm.data[bm.argmin_z:bm.argmax_z, bm.argmin_y:bm.argmax_y, bm.argmin_x:bm.argmax_x], order='C')
        bm.labelData = np.copy(bm.labelData[bm.argmin_z:bm.argmax_z, bm.argmin_y:bm.argmax_y, bm.argmin_x:bm.argmax_x], order='C')

        # domain decomposition
        sizeofblocks = (bm.argmax_z - bm.argmin_z) // ngpus
        blocks = [0]
        for k in range(ngpus-1):
            block_temp = blocks[-1] + sizeofblocks
            blocks.append(block_temp)
        blocks.append(bm.argmax_z - bm.argmin_z)
        print('blocks =', blocks)

        # read labeled slices
        if bm.label.allaxis:
            tmp = np.swapaxes(bm.labelData, 0, 1)
            tmp = np.ascontiguousarray(tmp)
            indices_01, _ = read_labeled_slices_allx_large(tmp)
            tmp = np.swapaxes(tmp, 0, 2)
            tmp = np.ascontiguousarray(tmp)
            indices_02, _ = read_labeled_slices_allx_large(tmp)

        # send data to childs
        for destination in range(ngpus-1,-1,-1):

            # ghost blocks
            blockmin = blocks[destination]
            blockmax = blocks[destination+1]
            datablockmin = blockmin - 100
            datablockmax = blockmax + 100
            datablockmin = 0 if datablockmin < 0 else datablockmin
            datablockmax = (bm.argmax_z - bm.argmin_z) if datablockmax > (bm.argmax_z - bm.argmin_z) else datablockmax
            datablock = np.copy(bm.data[datablockmin:datablockmax], order='C')
            labelblock = np.copy(bm.labelData[datablockmin:datablockmax], order='C')

            # read labeled slices
            if bm.label.allaxis:
                labelblock = labelblock.astype(np.int32)
                labelblock[:blockmin - datablockmin] = -1
                labelblock[blockmax - datablockmin:] = -1
                indices_child, labels_child = [], []
                indices_00, labels_00 = read_labeled_slices_allx_large(labelblock)
                indices_child.append(indices_00)
                labels_child.append(labels_00)
                tmp = np.swapaxes(labelblock, 0, 1)
                tmp = np.ascontiguousarray(tmp)
                labels_01 = np.zeros((0, tmp.shape[1], tmp.shape[2]), dtype=np.int32)
                for slcIndex in indices_01:
                    labels_01 = np.append(labels_01, [tmp[slcIndex]], axis=0)
                indices_child.append(indices_01)
                labels_child.append(labels_01)
                tmp = np.swapaxes(tmp, 0, 2)
                tmp = np.ascontiguousarray(tmp)
                labels_02 = np.zeros((0, tmp.shape[1], tmp.shape[2]), dtype=np.int32)
                for slcIndex in indices_02:
                    labels_02 = np.append(labels_02, [tmp[slcIndex]], axis=0)
                indices_child.append(indices_02)
                labels_child.append(labels_02)
            else:
                labelblock[:blockmin - datablockmin] = 0
                labelblock[blockmax - datablockmin:] = 0
                indices_child, labels_child = read_labeled_slices_large(labelblock)

            # print indices of labels
            print('indices child %s:' %(destination), indices_child)

            if destination > 0:
                blocks_temp = blocks[:]
                blocks_temp[destination] = blockmin - datablockmin
                blocks_temp[destination+1] = blockmax - datablockmin
                dataListe = splitlargedata(datablock)
                sendToChildLarge(comm, indices_child, destination, dataListe, labels_child,
                        bm.label.nbrw, bm.label.sorw, blocks_temp, bm.label.allaxis,
                        bm.allLabels, bm.label.smooth, bm.label.uncertainty, bm.platform)

            else:

                # select platform
                if bm.platform == 'cuda':
                    import pycuda.driver as cuda
                    cuda.init()
                    dev = cuda.Device(rank)
                    ctx, queue = dev.make_context(), None
                    if bm.label.allaxis:
                        from biomedisa_features.random_walk.pycuda_large_allx import walk
                    else:
                        from biomedisa_features.random_walk.pycuda_large import walk
                else:
                    ctx, queue = _get_device(bm.platform, rank)
                    from biomedisa_features.random_walk.pyopencl_large import walk

                # run random walks
                tic = time.time()
                memory_error, final, final_uncertainty, final_smooth = walk(comm, datablock, labels_child, indices_child,
                            bm.label.nbrw, bm.label.sorw, blockmin-datablockmin, blockmax-datablockmin,
                            name, bm.allLabels, bm.label.smooth, bm.label.uncertainty, ctx, queue, bm.platform)
                tac = time.time()
                print('Walktime_%s: ' %(name) + str(int(tac - tic)) + ' ' + 'seconds')

                # free device
                if bm.platform == 'cuda':
                    ctx.pop()
                    del ctx

        if memory_error:
            bm = _error_(bm, 'GPU out of memory. Image too large.')

        else:

            # gather data
            for source in range(1, ngpus):
                lendataListe = comm.recv(source=source, tag=0)
                for l in range(lendataListe):
                    data_z, data_y, data_x = comm.recv(source=source, tag=10+(2*l))
                    receivedata = np.empty((data_z, data_y, data_x), dtype=np.uint8)
                    comm.Recv([receivedata, MPI.BYTE], source=source, tag=10+(2*l+1))
                    final = np.append(final, receivedata, axis=0)

            # save finals
            final2 = np.zeros((bm.zsh, bm.ysh, bm.xsh), dtype=np.uint8)
            final2[bm.argmin_z:bm.argmax_z, bm.argmin_y:bm.argmax_y, bm.argmin_x:bm.argmax_x] = final
            final2 = final2[1:-1, 1:-1, 1:-1]
            bm.path_to_final = unique_file_path(bm.path_to_final, bm.image.user.username)
            save_data(bm.path_to_final, final2, bm.header, bm.final_image_type, bm.label.compression)

            # uncertainty
            if final_uncertainty is not None:
                final_uncertainty *= 255
                final_uncertainty = final_uncertainty.astype(np.uint8)
                for source in range(1, ngpus):
                    lendataListe = comm.recv(source=source, tag=0)
                    for l in range(lendataListe):
                        data_z, data_y, data_x = comm.recv(source=source, tag=10+(2*l))
                        receivedata = np.empty((data_z, data_y, data_x), dtype=np.uint8)
                        comm.Recv([receivedata, MPI.BYTE], source=source, tag=10+(2*l+1))
                        final_uncertainty = np.append(final_uncertainty, receivedata, axis=0)
                # save finals
                final2 = np.zeros((bm.zsh, bm.ysh, bm.xsh), dtype=np.uint8)
                final2[bm.argmin_z:bm.argmax_z, bm.argmin_y:bm.argmax_y, bm.argmin_x:bm.argmax_x] = final_uncertainty
                final2 = final2[1:-1, 1:-1, 1:-1]
                bm.path_to_uq = unique_file_path(bm.path_to_uq, bm.image.user.username)
                save_data(bm.path_to_uq, final2, compress=bm.label.compression)

            # smooth
            if final_smooth is not None:
                for source in range(1, ngpus):
                    lendataListe = comm.recv(source=source, tag=0)
                    for l in range(lendataListe):
                        data_z, data_y, data_x = comm.recv(source=source, tag=10+(2*l))
                        receivedata = np.empty((data_z, data_y, data_x), dtype=np.uint8)
                        comm.Recv([receivedata, MPI.BYTE], source=source, tag=10+(2*l+1))
                        final_smooth = np.append(final_smooth, receivedata, axis=0)
                # save finals
                final2 = np.zeros((bm.zsh, bm.ysh, bm.xsh), dtype=np.uint8)
                final2[bm.argmin_z:bm.argmax_z, bm.argmin_y:bm.argmax_y, bm.argmin_x:bm.argmax_x] = final_smooth
                final2 = final2[1:-1, 1:-1, 1:-1]
                bm.path_to_smooth = unique_file_path(bm.path_to_smooth, bm.image.user.username)
                save_data(bm.path_to_smooth, final2, bm.header, bm.final_image_type, bm.label.compression)

            # create final objects
            shortfilename = os.path.basename(bm.path_to_final)
            filename = 'images/' + bm.image.user.username + '/' + shortfilename
            tmp = Upload.objects.create(pic=filename, user=bm.image.user, project=bm.image.project, final=1, active=1, imageType=3, shortfilename=shortfilename)
            tmp.friend = tmp.id
            tmp.save()
            if final_uncertainty is not None:
                shortfilename = os.path.basename(bm.path_to_uq)
                filename = 'images/' + bm.image.user.username + '/' + shortfilename
                Upload.objects.create(pic=filename, user=bm.image.user, project=bm.image.project, final=4, imageType=3, shortfilename=shortfilename, friend=tmp.id)
            if final_smooth is not None:
                shortfilename = os.path.basename(bm.path_to_smooth)
                filename = 'images/' + bm.image.user.username + '/' + shortfilename
                smooth = Upload.objects.create(pic=filename, user=bm.image.user, project=bm.image.project, final=5, imageType=3, shortfilename=shortfilename, friend=tmp.id)

            # write in logs
            t = int(time.time() - bm.TIC)
            if t < 60:
                time_str = str(t) + ' sec'
            elif 60 <= t < 3600:
                time_str = str(t // 60) + ' min ' + str(t % 60) + ' sec'
            elif 3600 < t:
                time_str = str(t // 3600) + ' h ' + str((t % 3600) // 60) + ' min ' + str(t % 60) + ' sec'
            with open(bm.path_to_time, 'a') as timefile:
                print('%s %s %s %s MB %s on %s' %(time.ctime(), bm.image.user.username, bm.image.shortfilename, bm.imageSize, time_str, config['SERVER_ALIAS']), file=timefile)
            print('Total calculation time:', time_str)

            # send notification
            send_notification(bm.image.user.username, bm.image.shortfilename, time_str, config['SERVER_ALIAS'])

            # start subprocesses
            if config['OS'] == 'linux':
                # acwe
                q = Queue('acwe', connection=Redis())
                job = q.enqueue_call(active_contour, args=(bm.image.id, tmp.id, bm.label.id,), timeout=-1)

                # cleanup
                q = Queue('cleanup', connection=Redis())
                job = q.enqueue_call(remove_outlier, args=(bm.image.id, tmp.id, tmp.id, bm.label.id,), timeout=-1)
                if final_smooth is not None:
                    job = q.enqueue_call(remove_outlier, args=(bm.image.id, smooth.id, tmp.id, bm.label.id, False,), timeout=-1)

                # create slices
                q = Queue('slices', connection=Redis())
                job = q.enqueue_call(create_slices, args=(bm.path_to_data, bm.path_to_final,), timeout=-1)
                if final_smooth is not None:
                    job = q.enqueue_call(create_slices, args=(bm.path_to_data, bm.path_to_smooth,), timeout=-1)
                if final_uncertainty is not None:
                    job = q.enqueue_call(create_slices, args=(bm.path_to_uq, None,), timeout=-1)

            elif config['OS'] == 'windows':

                # acwe
                Process(target=active_contour, args=(bm.image.id, tmp.id, bm.label.id)).start()

                # cleanup
                Process(target=remove_outlier, args=(bm.image.id, tmp.id, tmp.id, bm.label.id)).start()
                if final_smooth is not None:
                    Process(target=remove_outlier, args=(bm.image.id, smooth.id, tmp.id, bm.label.id, False)).start()

                # create slices
                Process(target=create_slices, args=(bm.path_to_data, bm.path_to_final)).start()
                if final_smooth is not None:
                    Process(target=create_slices, args=(bm.path_to_data, bm.path_to_smooth)).start()
                if final_uncertainty is not None:
                    Process(target=create_slices, args=(bm.path_to_uq, None)).start()

    else:

        lendataListe = comm.recv(source=0, tag=0)
        for k in range(lendataListe):
            data_z, data_y, data_x, data_dtype = comm.recv(source=0, tag=10+(2*k))
            if k==0: data = np.zeros((0, data_y, data_x), dtype=data_dtype)
            data_temp = np.empty((data_z, data_y, data_x), dtype=data_dtype)
            if data_dtype == 'uint8':
                comm.Recv([data_temp, MPI.BYTE], source=0, tag=10+(2*k+1))
            else:
                comm.Recv([data_temp, MPI.FLOAT], source=0, tag=10+(2*k+1))
            data = np.append(data, data_temp, axis=0)

        nbrw, sorw, allx, smooth, uncertainty, platform = comm.recv(source=0, tag=1)

        if allx:
            labels = []
            for k in range(3):
                lenlabelsListe = comm.recv(source=0, tag=2+k)
                for l in range(lenlabelsListe):
                    labels_z, labels_y, labels_x = comm.recv(source=0, tag=100+(2*k))
                    if l==0: labels_tmp = np.zeros((0, labels_y, labels_x), dtype=np.int32)
                    tmp = np.empty((labels_z, labels_y, labels_x), dtype=np.int32)
                    comm.Recv([tmp, MPI.INT], source=0, tag=100+(2*k+1))
                    labels_tmp = np.append(labels_tmp, tmp, axis=0)
                labels.append(labels_tmp)
        else:
            lenlabelsListe = comm.recv(source=0, tag=2)
            for k in range(lenlabelsListe):
                labels_z, labels_y, labels_x = comm.recv(source=0, tag=100+(2*k))
                if k==0: labels = np.zeros((0, labels_y, labels_x), dtype=np.int32)
                tmp = np.empty((labels_z, labels_y, labels_x), dtype=np.int32)
                comm.Recv([tmp, MPI.INT], source=0, tag=100+(2*k+1))
                labels = np.append(labels, tmp, axis=0)

        allLabels = comm.recv(source=0, tag=99)
        indices = comm.recv(source=0, tag=8)
        blocks = comm.recv(source=0, tag=9)

        blockmin = blocks[rank]
        blockmax = blocks[rank+1]

        # select platform
        if platform == 'cuda':
            import pycuda.driver as cuda
            cuda.init()
            dev = cuda.Device(rank)
            ctx, queue = dev.make_context(), None
            if allx:
                from biomedisa_features.random_walk.pycuda_large_allx import walk
            else:
                from biomedisa_features.random_walk.pycuda_large import walk
        else:
            ctx, queue = _get_device(platform, rank)
            from biomedisa_features.random_walk.pyopencl_large import walk

        # run random walks
        tic = time.time()
        memory_error, final, final_uncertainty, final_smooth = walk(comm, data, labels, indices, nbrw, sorw,
                blockmin, blockmax, name, allLabels, smooth, uncertainty, ctx, queue, platform)
        tac = time.time()
        print('Walktime_%s: ' %(name) + str(int(tac - tic)) + ' ' + 'seconds')

        # free device
        if platform == 'cuda':
            ctx.pop()
            del ctx

        # send finals
        if not memory_error:
            dataListe = splitlargedata(final)
            comm.send(len(dataListe), dest=0, tag=0)
            for k, dataTemp in enumerate(dataListe):
                dataTemp = dataTemp.copy(order='C')
                comm.send([dataTemp.shape[0], dataTemp.shape[1], dataTemp.shape[2]], dest=0, tag=10+(2*k))
                comm.Send([dataTemp, MPI.BYTE], dest=0, tag=10+(2*k+1))

            if final_uncertainty is not None:
                final_uncertainty *= 255
                final_uncertainty = final_uncertainty.astype(np.uint8)
                dataListe = splitlargedata(final_uncertainty)
                comm.send(len(dataListe), dest=0, tag=0)
                for k, dataTemp in enumerate(dataListe):
                    dataTemp = dataTemp.copy(order='C')
                    comm.send([dataTemp.shape[0], dataTemp.shape[1], dataTemp.shape[2]], dest=0, tag=10+(2*k))
                    comm.Send([dataTemp, MPI.BYTE], dest=0, tag=10+(2*k+1))

            if final_smooth is not None:
                dataListe = splitlargedata(final_smooth)
                comm.send(len(dataListe), dest=0, tag=0)
                for k, dataTemp in enumerate(dataListe):
                    dataTemp = dataTemp.copy(order='C')
                    comm.send([dataTemp.shape[0], dataTemp.shape[1], dataTemp.shape[2]], dest=0, tag=10+(2*k))
                    comm.Send([dataTemp, MPI.BYTE], dest=0, tag=10+(2*k+1))

