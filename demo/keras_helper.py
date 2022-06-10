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

from biomedisa_helper import img_resize, load_data, save_data
from tensorflow.keras.optimizers import SGD
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import (
    Input, Conv3D, MaxPooling3D, UpSampling3D, Activation, Reshape,
    BatchNormalization, Concatenate)
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import Callback, ModelCheckpoint, EarlyStopping
from DataGenerator import DataGenerator
from PredictDataGenerator import PredictDataGenerator
import matplotlib.pyplot as plt
import tensorflow as tf
import numpy as np
import cv2
from random import shuffle
from glob import glob
import random
import numba
import re
import os
import time
import h5py

class InputError(Exception):
    def __init__(self, message=None):
        self.message = message

def save_history(history, path_to_model):
    # summarize history for accuracy
    plt.plot(history['accuracy'])
    plt.plot(history['val_accuracy'])
    if 'val_loss' in history:
        plt.legend(['train', 'test'], loc='upper left')
    else:
        plt.legend(['train', 'test (Dice)'], loc='upper left')
    plt.title('model accuracy')
    plt.ylabel('accuracy')
    plt.xlabel('epoch')
    plt.tight_layout()  # To prevent overlapping of subplots
    plt.savefig(path_to_model.replace(".h5","_acc.png"), dpi=300, bbox_inches='tight')
    plt.clf()
    # summarize history for loss
    plt.plot(history['loss'])
    if 'val_loss' in history:
        plt.plot(history['val_loss'])
    plt.title('model loss')
    plt.ylabel('loss')
    plt.xlabel('epoch')
    plt.legend(['train', 'test'], loc='upper left')
    plt.tight_layout()  # To prevent overlapping of subplots
    plt.savefig(path_to_model.replace(".h5","_loss.png"), dpi=300, bbox_inches='tight')
    plt.clf()

def predict_blocksize(labelData, x_puffer, y_puffer, z_puffer):
    zsh, ysh, xsh = labelData.shape
    argmin_z, argmax_z, argmin_y, argmax_y, argmin_x, argmax_x = zsh, 0, ysh, 0, xsh, 0
    for k in range(zsh):
        y, x = np.nonzero(labelData[k])
        if x.any():
            argmin_x = min(argmin_x, np.amin(x))
            argmax_x = max(argmax_x, np.amax(x))
            argmin_y = min(argmin_y, np.amin(y))
            argmax_y = max(argmax_y, np.amax(y))
            argmin_z = min(argmin_z, k)
            argmax_z = max(argmax_z, k)
    zmin, zmax = argmin_z, argmax_z
    argmin_x = argmin_x - x_puffer if argmin_x - x_puffer > 0 else 0
    argmax_x = argmax_x + x_puffer if argmax_x + x_puffer < xsh else xsh
    argmin_y = argmin_y - y_puffer if argmin_y - y_puffer > 0 else 0
    argmax_y = argmax_y + y_puffer if argmax_y + y_puffer < ysh else ysh
    argmin_z = argmin_z - z_puffer if argmin_z - z_puffer > 0 else 0
    argmax_z = argmax_z + z_puffer if argmax_z + z_puffer < zsh else zsh
    return argmin_z,argmax_z,argmin_y,argmax_y,argmin_x,argmax_x

def get_image_dimensions(header, data):

    # read header as string
    b = header.tobytes()
    s = b.decode("utf-8")

    # get image size in header
    lattice = re.search('define Lattice (.*)\n', s)
    lattice = lattice.group(1)
    xsh, ysh, zsh = lattice.split(' ')
    xsh, ysh, zsh = int(xsh), int(ysh), int(zsh)

    # new image size
    z,y,x = data.shape

    # change image size in header
    s = s.replace('%s %s %s' %(xsh,ysh,zsh), '%s %s %s' %(x,y,z),1)
    s = s.replace('Content "%sx%sx%s byte' %(xsh,ysh,zsh), 'Content "%sx%sx%s byte' %(x,y,z),1)

    # return header as array
    b2 = s.encode()
    new_header = np.frombuffer(b2, dtype=header.dtype)
    return new_header

def get_physical_size(header, img_header):

    # read img_header as string
    b = img_header.tobytes()
    s = b.decode("utf-8")

    # get physical size from image header
    lattice = re.search('BoundingBox (.*),\n', s)
    lattice = lattice.group(1)
    i0, i1, i2, i3, i4, i5 = lattice.split(' ')
    bounding_box_i = re.search('&BoundingBox (.*),\n', s)
    bounding_box_i = bounding_box_i.group(1)

    # read header as string
    b = header.tobytes()
    s = b.decode("utf-8")

    # get physical size from header
    lattice = re.search('BoundingBox (.*),\n', s)
    lattice = lattice.group(1)
    l0, l1, l2, l3, l4, l5 = lattice.split(' ')
    bounding_box_l = re.search('&BoundingBox (.*),\n', s)
    bounding_box_l = bounding_box_l.group(1)

    # change physical size in header
    s = s.replace('%s %s %s %s %s %s' %(l0,l1,l2,l3,l4,l5),'%s %s %s %s %s %s' %(i0,i1,i2,i3,i4,i5),1)
    s = s.replace(bounding_box_l,bounding_box_i,1)

    # return header as array
    b2 = s.encode()
    new_header = np.frombuffer(b2, dtype=header.dtype)
    return new_header

@numba.jit(nopython=True)
def compute_position(position, zsh, ysh, xsh):
    zsh_h, ysh_h, xsh_h = zsh//2, ysh//2, xsh//2
    for k in range(zsh):
        for l in range(ysh):
            for m in range(xsh):
                x = (xsh_h-m)**2
                y = (ysh_h-l)**2
                z = (zsh_h-k)**2
                position[k,l,m] = x+y+z
    return position

def make_axis_divisible_by_patch_size(a, patch_size):
    zsh, ysh, xsh = a.shape
    a = np.append(a, np.zeros((patch_size-(zsh % patch_size), ysh, xsh), a.dtype), axis=0)
    zsh, ysh, xsh = a.shape
    a = np.append(a, np.zeros((zsh, patch_size-(ysh % patch_size), xsh), a.dtype), axis=1)
    zsh, ysh, xsh = a.shape
    a = np.append(a, np.zeros((zsh, ysh, patch_size-(xsh % patch_size)), a.dtype), axis=2)
    a = np.copy(a, order='C')
    return a

def make_conv_block(nb_filters, input_tensor, block):
    def make_stage(input_tensor, stage):
        name = 'conv_{}_{}'.format(block, stage)
        x = Conv3D(nb_filters, (3, 3, 3), activation='relu',
                   padding='same', name=name, data_format="channels_last")(input_tensor)
        name = 'batch_norm_{}_{}'.format(block, stage)
        x = BatchNormalization(name=name)(x)
        x = Activation('relu')(x)
        return x

    x = make_stage(input_tensor, 1)
    x = make_stage(x, 2)
    return x

def make_unet(input_shape, nb_labels):

    nb_plans, nb_rows, nb_cols, _ = input_shape

    inputs = Input(input_shape)
    conv1 = make_conv_block(32, inputs, 1)
    pool1 = MaxPooling3D(pool_size=(2, 2, 2))(conv1)

    conv2 = make_conv_block(64, pool1, 2)
    pool2 = MaxPooling3D(pool_size=(2, 2, 2))(conv2)

    conv3 = make_conv_block(128, pool2, 3)
    pool3 = MaxPooling3D(pool_size=(2, 2, 2))(conv3)

    conv4 = make_conv_block(256, pool3, 4)
    pool4 = MaxPooling3D(pool_size=(2, 2, 2))(conv4)

    conv5 = make_conv_block(512, pool4, 5)
    pool5 = MaxPooling3D(pool_size=(2, 2, 2))(conv5)

    conv6 = make_conv_block(1024, pool5, 6)

    up7 = Concatenate()([UpSampling3D(size=(2, 2, 2))(conv6), conv5])
    conv7 = make_conv_block(512, up7, 7)

    up8 = Concatenate()([UpSampling3D(size=(2, 2, 2))(conv7), conv4])
    conv8 = make_conv_block(256, up8, 8)

    up9 = Concatenate()([UpSampling3D(size=(2, 2, 2))(conv8), conv3])
    conv9 = make_conv_block(128, up9, 9)

    up10 = Concatenate()([UpSampling3D(size=(2, 2, 2))(conv9), conv2])
    conv10 = make_conv_block(64, up10, 10)

    up11 = Concatenate()([UpSampling3D(size=(2, 2, 2))(conv10), conv1])
    conv11 = make_conv_block(32, up11, 11)

    conv12 = Conv3D(nb_labels, (1, 1, 1), name='conv_12_1')(conv11)

    x = Reshape((nb_plans * nb_rows * nb_cols, nb_labels))(conv12)
    x = Activation('softmax')(x)
    outputs = Reshape((nb_plans, nb_rows, nb_cols, nb_labels))(x)

    model = Model(inputs=inputs, outputs=outputs)

    return model

def get_labels(arr, allLabels):
    np_unique = np.unique(arr)
    final = np.zeros_like(arr)
    for k in np_unique:
        final[arr == k] = allLabels[k]
    return final

#=====================
# regular
#=====================

def load_training_data(normalize, img_dir, label_dir, channels, x_scale, y_scale, z_scale,
        crop_data, configuration_data=None, allLabels=None, x_puffer=25, y_puffer=25, z_puffer=25):

    # get filenames
    img_names, label_names = [], []
    for data_type in ['.am','.tif','.tiff','.hdr','.mhd','.mha','.nrrd','.nii','.nii.gz']:
        tmp_img_names = glob(img_dir+'/**/*'+data_type, recursive=True)
        tmp_label_names = glob(label_dir+'/**/*'+data_type, recursive=True)
        tmp_img_names = sorted(tmp_img_names)
        tmp_label_names = sorted(tmp_label_names)
        img_names.extend(tmp_img_names)
        label_names.extend(tmp_label_names)

    # load first label
    a, header, extension = load_data(label_names[0], 'first_queue', True)
    if a is None:
        InputError.message = "Invalid label data %s." %(os.path.basename(label_names[0]))
        raise InputError()
    if crop_data:
        argmin_z,argmax_z,argmin_y,argmax_y,argmin_x,argmax_x = predict_blocksize(a, x_puffer, y_puffer, z_puffer)
        a = np.copy(a[argmin_z:argmax_z,argmin_y:argmax_y,argmin_x:argmax_x], order='C')
    a = a.astype(np.uint8)
    np_unique = np.unique(a)
    label = np.zeros((z_scale, y_scale, x_scale), dtype=a.dtype)
    for k in np_unique:
        tmp = np.zeros_like(a)
        tmp[a==k] = 1
        tmp = img_resize(tmp, z_scale, y_scale, x_scale)
        label[tmp==1] = k

    # load first img
    img, _ = load_data(img_names[0], 'first_queue')
    if img is None:
        InputError.message = "Invalid image data %s." %(os.path.basename(img_names[0]))
        raise InputError()
    if crop_data:
        img = np.copy(img[argmin_z:argmax_z,argmin_y:argmax_y,argmin_x:argmax_x], order='C')
    img = img.astype(np.float32)
    img = img_resize(img, z_scale, y_scale, x_scale)
    img -= np.amin(img)
    img /= np.amax(img)
    if configuration_data is not None:
        mu, sig = configuration_data[5], configuration_data[6]
        mu_tmp, sig_tmp = np.mean(img), np.std(img)
        img = (img - mu_tmp) / sig_tmp
        img = img * sig + mu
    else:
        mu, sig = np.mean(img), np.std(img)

    for img_name, label_name in zip(img_names[1:], label_names[1:]):

        # append label
        a, _ = load_data(label_name, 'first_queue')
        if a is None:
            InputError.message = "Invalid label data %s." %(os.path.basename(name))
            raise InputError()
        if crop_data:
            argmin_z,argmax_z,argmin_y,argmax_y,argmin_x,argmax_x = predict_blocksize(a, x_puffer, y_puffer, z_puffer)
            a = np.copy(a[argmin_z:argmax_z,argmin_y:argmax_y,argmin_x:argmax_x], order='C')
        a = a.astype(np.uint8)
        np_unique = np.unique(a)
        next_label = np.zeros((z_scale, y_scale, x_scale), dtype=a.dtype)
        for k in np_unique:
            tmp = np.zeros_like(a)
            tmp[a==k] = 1
            tmp = img_resize(tmp, z_scale, y_scale, x_scale)
            next_label[tmp==1] = k
        label = np.append(label, next_label, axis=0)

        # append image
        a, _ = load_data(img_name, 'first_queue')
        if a is None:
            InputError.message = "Invalid image data %s." %(os.path.basename(name))
            raise InputError()
        if crop_data:
            a = np.copy(a[argmin_z:argmax_z,argmin_y:argmax_y,argmin_x:argmax_x], order='C')
        a = a.astype(np.float32)
        a = img_resize(a, z_scale, y_scale, x_scale)
        a -= np.amin(a)
        a /= np.amax(a)
        if normalize:
            mu_tmp, sig_tmp = np.mean(a), np.std(a)
            a = (a - mu_tmp) / sig_tmp
            a = a * sig + mu
        img = np.append(img, a, axis=0)

    # scale image data to [0,1]
    img[img<0] = 0
    img[img>1] = 1

    # compute position data
    position = None
    if channels == 2:
        position = np.empty((z_scale, y_scale, x_scale), dtype=np.float32)
        position = compute_position(position, z_scale, y_scale, x_scale)
        position = np.sqrt(position)
        position /= np.amax(position)
        for k in range(len(img_names[1:])):
            a = np.copy(position)
            position = np.append(position, a, axis=0)

    # labels must be in ascending order
    if allLabels is not None:
        counts = None
        for k, l in enumerate(allLabels):
            label[label==l] = k
    else:
        allLabels, counts = np.unique(label, return_counts=True)
        for k, l in enumerate(allLabels):
            label[label==l] = k

    # configuration data
    configuration_data = np.array([channels, x_scale, y_scale, z_scale, normalize, mu, sig])

    return img, label, position, allLabels, configuration_data, header, extension, counts

class MetaData(Callback):
    def __init__(self, path_to_model, configuration_data, allLabels, extension, header):
        self.path_to_model = path_to_model
        self.configuration_data = configuration_data
        self.allLabels = allLabels
        self.extension = extension
        self.header = header

    def on_epoch_end(self, epoch, logs={}):
        hf = h5py.File(self.path_to_model, 'r')
        if not '/meta' in hf:
            hf.close()
            hf = h5py.File(self.path_to_model, 'r+')
            group = hf.create_group('meta')
            group.create_dataset('configuration', data=self.configuration_data)
            group.create_dataset('labels', data=self.allLabels)
            if self.extension == '.am':
                group.create_dataset('extension', data=self.extension)
                group.create_dataset('header', data=self.header)
        hf.close()

class Metrics(Callback):
    def __init__(self, img, label, list_IDs, dim_patch, dim_img, batch_size, path_to_model, early_stopping, validation_freq, n_classes):
        self.dim_patch = dim_patch
        self.dim_img = dim_img
        self.list_IDs = list_IDs
        self.batch_size = batch_size
        self.label = label
        self.img = img
        self.path_to_model = path_to_model
        self.early_stopping = early_stopping
        self.validation_freq = validation_freq
        self.n_classes = n_classes

    def on_train_begin(self, logs={}):
        self.history = {}
        self.history['val_accuracy'] = []
        self.history['accuracy'] = []
        self.history['loss'] = []

    def on_epoch_end(self, epoch, logs={}):
        if epoch % self.validation_freq == 0:

            result = np.zeros((*self.dim_img, self.n_classes), dtype=np.float32)

            len_IDs = len(self.list_IDs)
            n_batches = int(np.floor(len_IDs / self.batch_size))

            for batch in range(n_batches):
                # Generate indexes of the batch
                list_IDs_batch = self.list_IDs[batch*self.batch_size:(batch+1)*self.batch_size]

                # Initialization
                X_val = np.empty((self.batch_size, *self.dim_patch, 1), dtype=np.float32)
                y_val = np.empty((self.batch_size, *self.dim_patch), dtype=np.int32)

                # Generate data
                for i, ID in enumerate(list_IDs_batch):

                    # get patch indices
                    k = ID // (self.dim_img[1]*self.dim_img[2])
                    rest = ID % (self.dim_img[1]*self.dim_img[2])
                    l = rest // self.dim_img[2]
                    m = rest % self.dim_img[2]

                    X_val[i,:,:,:,0] = self.img[k:k+self.dim_patch[0],l:l+self.dim_patch[1],m:m+self.dim_patch[2]]
                    y_val[i,:,:,:] = self.label[k:k+self.dim_patch[0],l:l+self.dim_patch[1],m:m+self.dim_patch[2]]

                # Prediction segmentation
                y_predict = np.asarray(self.model.predict(X_val, verbose=0, steps=None))

                for i, ID in enumerate(list_IDs_batch):

                    # get patch indices
                    k = ID // (self.dim_img[1]*self.dim_img[2])
                    rest = ID % (self.dim_img[1]*self.dim_img[2])
                    l = rest // self.dim_img[2]
                    m = rest % self.dim_img[2]

                    result[k:k+self.dim_patch[0],l:l+self.dim_patch[1],m:m+self.dim_patch[2]] += y_predict[i]

            # Compute dice score
            result = np.argmax(result, axis=-1)
            result = result.astype(np.uint8)
            dice = 2 * np.logical_and(self.label==result, (self.label+result)>0).sum() / \
                   float((self.label>0).sum() + (result>0).sum())

            # save best model only
            if epoch == 0:
                self.model.save(str(self.path_to_model))
            elif round(dice,5) > max(self.history['val_accuracy']):
                self.model.save(str(self.path_to_model))

            # add accuracy to history
            self.history['val_accuracy'].append(round(dice,5))
            self.history['accuracy'].append(round(logs["accuracy"],5))
            self.history['loss'].append(round(logs["loss"],5))
            logs["val_accuracy"] = max(self.history['val_accuracy'])
            save_history(self.history, self.path_to_model)

            # print accuracies
            print()
            print('val_acc (Dice):', self.history['val_accuracy'])
            print('train_acc:', self.history['accuracy'])
            print()

            # early stopping
            if self.early_stopping > 0 and max(self.history['val_accuracy']) not in self.history['val_accuracy'][-self.early_stopping:]:
                self.model.stop_training = True

def train_semantic_segmentation(normalize, path_to_img, path_to_labels, x_scale, y_scale,
            z_scale, crop_data, path_to_model, z_patch, y_patch, x_patch, epochs,
            batch_size, channels, validation_split, stride_size, class_weights,
            flip_x, flip_y, flip_z, rotate, early_stopping, val_tf, learning_rate,
            path_val_img, path_val_labels, validation_stride_size, validation_freq,
            validation_batch_size):

    # training data
    img, label, position, allLabels, configuration_data, header, extension, counts = load_training_data(normalize,
                    path_to_img, path_to_labels, channels, x_scale, y_scale, z_scale, crop_data, None, None)

    # img shape
    zsh, ysh, xsh = img.shape

    # validation data
    if path_val_img:
        img_val, label_val, position_val, _, _, _, _, _ = load_training_data(normalize,
                        path_val_img, path_val_labels, channels, x_scale, y_scale, z_scale, crop_data, configuration_data, allLabels)

    elif validation_split:
        number_of_images = zsh // z_scale
        split = round(number_of_images * validation_split)
        img_val = np.copy(img[split*z_scale:])
        label_val = np.copy(label[split*z_scale:])
        img = np.copy(img[:split*z_scale])
        label = np.copy(label[:split*z_scale])
        zsh, ysh, xsh = img.shape
        if channels == 2:
            position_val = np.copy(position[split*z_scale:])
            position = np.copy(position[:split*z_scale])

    # list of IDs
    list_IDs = []

    # get IDs of patches
    for k in range(0, zsh-z_patch+1, stride_size):
        for l in range(0, ysh-y_patch+1, stride_size):
            for m in range(0, xsh-x_patch+1, stride_size):
                list_IDs.append(k*ysh*xsh+l*xsh+m)

    if path_val_img or validation_split:

        # img_val shape
        zsh_val, ysh_val, xsh_val = img_val.shape

        # list of validation IDs
        list_IDs_val = []

        # get validation IDs of patches
        for k in range(0, zsh_val-z_patch+1, validation_stride_size):
            for l in range(0, ysh_val-y_patch+1, validation_stride_size):
                for m in range(0, xsh_val-x_patch+1, validation_stride_size):
                    list_IDs_val.append(k*ysh_val*xsh_val+l*xsh_val+m)

    # number of labels
    nb_labels = len(allLabels)

    # input shape
    input_shape = (z_patch, y_patch, x_patch, channels)

    # parameters
    params = {'batch_size': batch_size,
              'dim': (z_patch, y_patch, x_patch),
              'dim_img': (zsh, ysh, xsh),
              'n_classes': nb_labels,
              'n_channels': channels,
              'class_weights': class_weights,
              'augment': (flip_x, flip_y, flip_z, rotate)}

    # data generator
    validation_generator = None
    training_generator = DataGenerator(img, label, position, list_IDs, counts, True, **params)
    if path_val_img or validation_split:
        if val_tf:
            params['batch_size'] = validation_batch_size
            params['dim_img'] = (zsh_val, ysh_val, xsh_val)
            params['augment'] = (False, False, False, 0)
            params['class_weights'] = False
            validation_generator = DataGenerator(img_val, label_val, position_val, list_IDs_val, counts, False, **params)
        else:
            metrics = Metrics(img_val, label_val, list_IDs_val, (z_patch, y_patch, x_patch), (zsh_val, ysh_val, xsh_val), validation_batch_size,
                              path_to_model, early_stopping, validation_freq, nb_labels)

    # optimizer
    sgd = SGD(learning_rate=learning_rate, decay=1e-6, momentum=0.9, nesterov=True)

    # create a MirroredStrategy
    if os.name == 'nt':
        cdo = tf.distribute.HierarchicalCopyAllReduce()
    else:
        cdo = tf.distribute.NcclAllReduce()
    strategy = tf.distribute.MirroredStrategy(cross_device_ops=cdo)
    print('Number of devices: {}'.format(strategy.num_replicas_in_sync))

    # compile model
    with strategy.scope():
        model = make_unet(input_shape, nb_labels)
        model.compile(loss='categorical_crossentropy',
                      optimizer=sgd,
                      metrics=['accuracy'])

    # save meta data
    meta_data = MetaData(path_to_model, configuration_data, allLabels, extension, header)

    # model checkpoint
    if path_val_img or validation_split:
        if val_tf:
            model_checkpoint_callback = ModelCheckpoint(
                filepath=str(path_to_model),
                save_weights_only=False,
                monitor='val_accuracy',
                mode='max',
                save_best_only=True)
            callbacks = [model_checkpoint_callback, meta_data]
            if early_stopping > 0:
                callbacks.insert(0, EarlyStopping(monitor='val_accuracy', mode='max', patience=early_stopping))
        else:
            callbacks = [metrics, meta_data]
    else:
        callbacks = [ModelCheckpoint(filepath=str(path_to_model)), meta_data]

    # train model
    history = model.fit(training_generator,
              epochs=epochs,
              validation_data=validation_generator,
              callbacks=callbacks)

    # save results in figure on train end
    if path_val_img or validation_split:
        if val_tf:
            save_history(history.history, path_to_model)

def load_prediction_data(path_to_img, channels, x_scale, y_scale, z_scale,
                        normalize, mu, sig, region_of_interest):

    # read image data
    img, img_header, img_ext = load_data(path_to_img, 'first_queue', return_extension=True)
    if img is None:
        InputError.message = "Invalid image data %s." %(os.path.basename(path_to_img))
        raise InputError()
    if img_ext != '.am':
        img_header = None
    z_shape, y_shape, x_shape = img.shape

    # automatic cropping of image to region of interest
    if np.any(region_of_interest):
        min_z, max_z, min_y, max_y, min_x, max_x = region_of_interest[:]
        img = np.copy(img[min_z:max_z,min_y:max_y,min_x:max_x], order='C')
        region_of_interest = np.array([min_z,max_z,min_y,max_y,min_x,max_x,z_shape,y_shape,x_shape])
        z_shape, y_shape, x_shape = max_z-min_z, max_y-min_y, max_x-min_x

    # scale image data
    img = img.astype(np.float32)
    img = img_resize(img, z_scale, y_scale, x_scale)
    img -= np.amin(img)
    img /= np.amax(img)
    if normalize:
        mu_tmp, sig_tmp = np.mean(img), np.std(img)
        img = (img - mu_tmp) / sig_tmp
        img = img * sig + mu
        img[img<0] = 0
        img[img>1] = 1

    # compute position data
    position = None
    if channels == 2:
        position = np.empty((z_scale, y_scale, x_scale), dtype=np.float32)
        position = compute_position(position, z_scale, y_scale, x_scale)
        position = np.sqrt(position)
        position /= np.amax(position)

    return img, img_header, position, z_shape, y_shape, x_shape, region_of_interest

def predict_semantic_segmentation(img, position, path_to_model, path_to_final,
    z_patch, y_patch, x_patch, z_shape, y_shape, x_shape, compress, header,
    img_header, channels, stride_size, allLabels, batch_size, region_of_interest):

    # img shape
    zsh, ysh, xsh = img.shape

    # list of IDs
    list_IDs = []

    # get nIds of patches
    for k in range(0, zsh-z_patch+1, stride_size):
        for l in range(0, ysh-y_patch+1, stride_size):
            for m in range(0, xsh-x_patch+1, stride_size):
                list_IDs.append(k*ysh*xsh+l*xsh+m)

    # make length of list divisible by batch size
    rest = batch_size - (len(list_IDs) % batch_size)
    list_IDs = list_IDs + list_IDs[:rest]

    # parameters
    params = {'dim': (z_patch, y_patch, x_patch),
              'dim_img': (zsh, ysh, xsh),
              'batch_size': batch_size,
              'n_channels': channels}

    # data generator
    predict_generator = PredictDataGenerator(img, position, list_IDs, **params)

    # create a MirroredStrategy
    if os.name == 'nt':
        cdo = tf.distribute.HierarchicalCopyAllReduce()
    else:
        cdo = tf.distribute.NcclAllReduce()
    strategy = tf.distribute.MirroredStrategy(cross_device_ops=cdo)

    # load model
    with strategy.scope():
        model = load_model(str(path_to_model))

    # predict
    probabilities = model.predict(predict_generator, verbose=0, steps=None)

    # create final
    final = np.zeros((zsh, ysh, xsh, probabilities.shape[4]), dtype=np.float32)
    nb = 0
    for k in range(0, zsh-z_patch+1, stride_size):
        for l in range(0, ysh-y_patch+1, stride_size):
            for m in range(0, xsh-x_patch+1, stride_size):
                final[k:k+z_patch, l:l+y_patch, m:m+x_patch] += probabilities[nb]
                nb += 1

    # get final
    out = np.argmax(final, axis=3)
    out = out.astype(np.uint8)

    # rescale final to input size
    np_unique = np.unique(out)
    label = np.zeros((z_shape, y_shape, x_shape), dtype=out.dtype)
    for k in np_unique:
        tmp = np.zeros_like(out)
        tmp[out==k] = 1
        tmp = img_resize(tmp, z_shape, y_shape, x_shape)
        label[tmp==1] = k

    # revert automatic cropping
    if np.any(region_of_interest):
        min_z,max_z,min_y,max_y,min_x,max_x,z_shape,y_shape,x_shape = region_of_interest[:]
        tmp = np.zeros((z_shape, y_shape, x_shape), dtype=out.dtype)
        tmp[min_z:max_z,min_y:max_y,min_x:max_x] = label
        label = np.copy(tmp)

    # save final
    label = label.astype(np.uint8)
    label = get_labels(label, allLabels)
    if header is not None:
        header = get_image_dimensions(header, label)
        if img_header is not None:
            header = get_physical_size(header, img_header)
    save_data(path_to_final, label, header=header, compress=compress)

def predict_pre_final(img, path_to_model, x_scale, y_scale, z_scale, z_patch, y_patch, x_patch, \
                      normalize, mu, sig, channels, stride_size, batch_size):

    # img shape
    z_shape, y_shape, x_shape = img.shape

    # load position data
    if channels == 2:
        position = np.empty((z_scale, y_scale, x_scale), dtype=np.float32)
        position = compute_position(position, z_scale, y_scale, x_scale)
        position = np.sqrt(position)
        position /= np.amax(position)

    # resize img data
    img = img.astype(np.float32)
    img = img_resize(img, z_scale, y_scale, x_scale)
    img -= np.amin(img)
    img /= np.amax(img)
    if normalize:
        mu_tmp, sig_tmp = np.mean(img), np.std(img)
        img = (img - mu_tmp) / sig_tmp
        img = img * sig + mu
        img[img<0] = 0
        img[img>1] = 1

    # img shape
    zsh, ysh, xsh = img.shape

    # get number of 3D-patches
    nb = 0
    for k in range(0, zsh-z_patch+1, stride_size):
        for l in range(0, ysh-y_patch+1, stride_size):
            for m in range(0, xsh-x_patch+1, stride_size):
                nb += 1

    # allocate memory
    x_test = np.empty((nb, z_patch, y_patch, x_patch, channels), dtype=img.dtype)

    # create testing set
    nb = 0
    for k in range(0, zsh-z_patch+1, stride_size):
        for l in range(0, ysh-y_patch+1, stride_size):
            for m in range(0, xsh-x_patch+1, stride_size):
                x_test[nb,:,:,:,0] = img[k:k+z_patch, l:l+y_patch, m:m+x_patch]
                if channels == 2:
                    x_test[nb,:,:,:,1] = position[k:k+z_patch, l:l+y_patch, m:m+x_patch]
                nb += 1

    # reshape testing set
    x_test = x_test.reshape(nb, z_patch, y_patch, x_patch, channels)

    # create a MirroredStrategy
    if os.name == 'nt':
        cdo = tf.distribute.HierarchicalCopyAllReduce()
    else:
        cdo = tf.distribute.NcclAllReduce()
    strategy = tf.distribute.MirroredStrategy(cross_device_ops=cdo)

    # load model
    with strategy.scope():
        model = load_model(str(path_to_model))

    # predict
    tmp = model.predict(x_test, batch_size=batch_size, verbose=0, steps=None)

    # create final
    final = np.zeros((zsh, ysh, xsh, tmp.shape[4]), dtype=np.float32)
    nb = 0
    for k in range(0, zsh-z_patch+1, stride_size):
        for l in range(0, ysh-y_patch+1, stride_size):
            for m in range(0, xsh-x_patch+1, stride_size):
                final[k:k+z_patch, l:l+y_patch, m:m+x_patch] += tmp[nb]
                nb += 1

    # get final
    out = np.argmax(final, axis=3)
    out = out.astype(np.uint8)

    # rescale final to input size
    np_unique = np.unique(out)
    label = np.zeros((z_shape, y_shape, x_shape), dtype=out.dtype)
    for k in np_unique:
        tmp = np.zeros_like(out)
        tmp[out==k] = 1
        tmp = img_resize(tmp, z_shape, y_shape, x_shape)
        label[tmp==1] = k

    return label

#=====================
# refine
#=====================

def load_training_data_refine(path_to_model, x_scale, y_scale, z_scale, patch_size, z_patch, y_patch, x_patch, normalize, \
                    img_list, label_list, channels, stride_size, allLabels, mu, sig, batch_size):

    # get filenames
    img_names, label_names = [], []
    for img_name, label_name in zip(img_list, label_list):

        img_dir, img_ext = os.path.splitext(img_name)
        if img_ext == '.gz':
            img_dir, img_ext = os.path.splitext(img_dir)

        label_dir, label_ext = os.path.splitext(label_name)
        if label_ext == '.gz':
            label_dir, label_ext = os.path.splitext(label_dir)

        if img_ext == '.tar' and label_ext == '.tar':
            for data_type in ['.am','.tif','.tiff','.hdr','.mhd','.mha','.nrrd','.nii','.nii.gz']:
                tmp_img_names = glob(img_dir+'/**/*'+data_type, recursive=True)
                tmp_label_names = glob(label_dir+'/**/*'+data_type, recursive=True)
                tmp_img_names = sorted(tmp_img_names)
                tmp_label_names = sorted(tmp_label_names)
                img_names.extend(tmp_img_names)
                label_names.extend(tmp_label_names)
        else:
            img_names.append(img_name)
            label_names.append(label_name)

    # predict pre-final
    final = []
    for name in img_names:
        a, _ = load_data(name, 'first_queue')
        if a is None:
            InputError.message = "Invalid image data %s." %(os.path.basename(name))
            raise InputError()
        a = predict_pre_final(a, path_to_model, x_scale, y_scale, z_scale, z_patch, y_patch, x_patch, \
                              normalize, mu, sig, channels, stride_size, batch_size)
        a = a.astype(np.float32)
        a /= len(allLabels) - 1
        #a = make_axis_divisible_by_patch_size(a, patch_size)
        final.append(a)

    # load img data
    img = []
    for name in img_names:
        a, _ = load_data(name, 'first_queue')
        a = a.astype(np.float32)
        a -= np.amin(a)
        a /= np.amax(a)
        if normalize:
            mu_tmp, sig_tmp = np.mean(a), np.std(a)
            a = (a - mu_tmp) / sig_tmp
            a = a * sig + mu
            a[a<0] = 0
            a[a>1] = 1
        #a = make_axis_divisible_by_patch_size(a, patch_size)
        img.append(a)

    # load label data
    label = []
    for name in label_names:
        a, _ = load_data(name, 'first_queue')
        if a is None:
            InputError.message = "Invalid label data %s." %(os.path.basename(name))
            raise InputError()
        #a = make_axis_divisible_by_patch_size(a, patch_size)
        label.append(a)

    # labels must be in ascending order
    for i in range(len(label)):
        for k, l in enumerate(allLabels):
            label[i][label[i]==l] = k

    return img, label, final

def config_training_data_refine(img, label, final, patch_size, stride_size):

    # get number of patches
    nb = 0
    for i in range(len(img)):
        zsh, ysh, xsh = img[i].shape
        for k in range(0, zsh-patch_size+1, stride_size):
            for l in range(0, ysh-patch_size+1, stride_size):
                for m in range(0, xsh-patch_size+1, stride_size):
                    tmp = np.copy(final[i][k:k+patch_size, l:l+patch_size, m:m+patch_size])
                    #if 0.1 * patch_size**3 < np.sum(tmp > 0) < 0.9 * patch_size**3:
                    if np.any(tmp[1:]!=tmp[0,0,0]):
                        nb += 1

    # create training data
    x_train = np.empty((nb, patch_size, patch_size, patch_size, 2), dtype=img[0].dtype)
    y_train = np.empty((nb, patch_size, patch_size, patch_size), dtype=label[0].dtype)

    nb = 0
    for i in range(len(img)):
        zsh, ysh, xsh = img[i].shape
        for k in range(0, zsh-patch_size+1, stride_size):
            for l in range(0, ysh-patch_size+1, stride_size):
                for m in range(0, xsh-patch_size+1, stride_size):
                    tmp = np.copy(final[i][k:k+patch_size, l:l+patch_size, m:m+patch_size])
                    #if 0.1 * patch_size**3 < np.sum(tmp > 0) < 0.9 * patch_size**3:
                    if np.any(tmp[1:]!=tmp[0,0,0]):
                        x_train[nb,:,:,:,0] = img[i][k:k+patch_size, l:l+patch_size, m:m+patch_size]
                        x_train[nb,:,:,:,1] = tmp
                        y_train[nb] = label[i][k:k+patch_size, l:l+patch_size, m:m+patch_size]
                        nb += 1

    return x_train, y_train

def train_semantic_segmentation_refine(img, label, final, path_to_model, patch_size, \
                    epochs, batch_size, allLabels, validation_split, stride_size):

    # number of labels
    nb_labels = len(allLabels)

    # load training
    x_train, y_train = config_training_data_refine(img, label, final, patch_size, stride_size)
    x_train = x_train.astype(np.float32)
    y_train = y_train.astype(np.int32)

    # make arrays divisible by batch_size
    rest = x_train.shape[0] % batch_size
    rest = x_train.shape[0] - rest
    x_train = x_train[:rest]
    y_train = y_train[:rest]

    # reshape arrays
    nsh, zsh, ysh, xsh, _ = x_train.shape
    x_train = x_train.reshape(nsh, zsh, ysh, xsh, 2)
    y_train = y_train.reshape(nsh, zsh, ysh, xsh, 1)

    # create one-hot vector
    y_train = to_categorical(y_train, num_classes=nb_labels)

    # input shape
    input_shape = (patch_size, patch_size, patch_size, 2)

    # optimizer
    sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)

    # create a MirroredStrategy
    if os.name == 'nt':
        cdo = tf.distribute.HierarchicalCopyAllReduce()
    else:
        cdo = tf.distribute.NcclAllReduce()
    strategy = tf.distribute.MirroredStrategy(cross_device_ops=cdo)
    print('Number of devices: {}'.format(strategy.num_replicas_in_sync))

    # compile model
    with strategy.scope():
        model = make_unet(input_shape, nb_labels)
        model.compile(loss='categorical_crossentropy',
                  optimizer=sgd,
                  metrics=['accuracy'])

    # fit model
    model.fit(x_train, y_train,
              epochs=epochs,
              batch_size=batch_size,
              validation_split=validation_split)

    # save model
    model.save(str(path_to_model))

def load_refine_data(path_to_img, path_to_final, patch_size, normalize, allLabels, mu, sig):

    # read image data
    img, _ = load_data(path_to_img, 'first_queue')
    if img is None:
        InputError.message = "Invalid image data %s." %(os.path.basename(path_to_img))
        raise InputError()
    z_shape, y_shape, x_shape = img.shape
    img = img.astype(np.float32)
    img -= np.amin(img)
    img /= np.amax(img)
    if normalize:
        mu_tmp, sig_tmp = np.mean(img), np.std(img)
        img = (img - mu_tmp) / sig_tmp
        img = img * sig + mu
        img[img<0] = 0
        img[img>1] = 1
    #img = make_axis_divisible_by_patch_size(img, patch_size)

    # load label data
    label, _ = load_data(path_to_final, 'first_queue')
    if label is None:
        InputError.message = "Invalid label data %s." %(os.path.basename(path_to_final))
        raise InputError()
    #label = make_axis_divisible_by_patch_size(label, patch_size)

    # labels must be in ascending order
    for k, l in enumerate(allLabels):
        label[label==l] = k

    # load final data and scale to [0,1]
    final = np.copy(label)
    final = final.astype(np.float32)
    final /= len(allLabels) - 1

    return img, label, final, z_shape, y_shape, x_shape

def refine_semantic_segmentation(path_to_img, path_to_final, path_to_model, patch_size,
                                 compress, header, img_header, normalize, stride_size, allLabels,
                                 mu, sig, batch_size):

    # load refine data
    img, label, final, z_shape, y_shape, x_shape = load_refine_data(path_to_img, path_to_final,
                                             patch_size, normalize, allLabels, mu, sig)

    # get number of 3D-patches
    nb = 0
    zsh, ysh, xsh = img.shape
    for k in range(0, zsh-patch_size+1, stride_size):
        for l in range(0, ysh-patch_size+1, stride_size):
            for m in range(0, xsh-patch_size+1, stride_size):
                tmp = label[k:k+patch_size, l:l+patch_size, m:m+patch_size]
                #if 0.1 * patch_size**3 < np.sum(tmp > 0) < 0.9 * patch_size**3:
                if np.any(tmp[1:]!=tmp[0,0,0]):
                    nb += 1

    # create prediction set
    x_test = np.empty((nb, patch_size, patch_size, patch_size, 2), dtype=img.dtype)
    nb = 0
    zsh, ysh, xsh = img.shape
    for k in range(0, zsh-patch_size+1, stride_size):
        for l in range(0, ysh-patch_size+1, stride_size):
            for m in range(0, xsh-patch_size+1, stride_size):
                tmp = label[k:k+patch_size, l:l+patch_size, m:m+patch_size]
                #if 0.1 * patch_size**3 < np.sum(tmp > 0) < 0.9 * patch_size**3:
                if np.any(tmp[1:]!=tmp[0,0,0]):
                    x_test[nb,:,:,:,0] = img[k:k+patch_size, l:l+patch_size, m:m+patch_size]
                    x_test[nb,:,:,:,1] = final[k:k+patch_size, l:l+patch_size, m:m+patch_size]
                    nb += 1

    # reshape prediction data
    x_test = x_test.reshape(nb, patch_size, patch_size, patch_size, 2)

    # create a MirroredStrategy
    if os.name == 'nt':
        cdo = tf.distribute.HierarchicalCopyAllReduce()
    else:
        cdo = tf.distribute.NcclAllReduce()
    strategy = tf.distribute.MirroredStrategy(cross_device_ops=cdo)

    # load model
    with strategy.scope():
        model = load_model(str(path_to_model))

    # predict
    prob = model.predict(x_test, batch_size=batch_size, verbose=0, steps=None)

    # create final
    nb = 0
    zsh, ysh, xsh = img.shape
    final = np.zeros((zsh, ysh, xsh, prob.shape[4]), dtype=np.float32)
    for k in range(0, zsh-patch_size+1, stride_size):
        for l in range(0, ysh-patch_size+1, stride_size):
            for m in range(0, xsh-patch_size+1, stride_size):
                tmp = label[k:k+patch_size, l:l+patch_size, m:m+patch_size]
                #if 0.1 * patch_size**3 < np.sum(tmp > 0) < 0.9 * patch_size**3:
                if np.any(tmp[1:]!=tmp[0,0,0]):
                    final[k:k+patch_size, l:l+patch_size, m:m+patch_size] += prob[nb]
                    nb += 1

    final = np.argmax(final, axis=3)
    final = final.astype(np.uint8)

    out = np.copy(label)
    for k in range(0, zsh-patch_size+1, stride_size):
        for l in range(0, ysh-patch_size+1, stride_size):
            for m in range(0, xsh-patch_size+1, stride_size):
                tmp = label[k:k+patch_size, l:l+patch_size, m:m+patch_size]
                #if 0.1 * patch_size**3 < np.sum(tmp > 0) < 0.9 * patch_size**3:
                if np.any(tmp[1:]!=tmp[0,0,0]):
                    out[k:k+patch_size, l:l+patch_size, m:m+patch_size] = final[k:k+patch_size, l:l+patch_size, m:m+patch_size]

    # save final
    out = out.astype(np.uint8)
    out = get_labels(out, allLabels)
    out = out[:z_shape, :y_shape, :x_shape]
    if header is not None:
        header = get_image_dimensions(header, out)
        if img_header is not None:
            header = get_physical_size(header, img_header)
    save_data(path_to_final, out, header=header, compress=compress)

