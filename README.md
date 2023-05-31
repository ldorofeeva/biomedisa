# Biomedisa

- [Overview](#overview)
- [Hardware requirements](#hardware-requirements)
- [Software requirements](#software-requirements)
- [Installation (command-line-only)](#installation-command-line-only)
- [Full installation (GUI)](#full-installation-gui)
- [Biomedisa interpolation](#biomedisa-interpolation)
- [Biomedisa deep learning](#biomedisa-deep-learning)
- [Biomedisa features](#biomedisa-features)
- [Update Biomedisa](#update-biomedisa)
- [Releases](#releases)
- [Authors](#authors)
- [FAQ](#faq)
- [Citation](#citation)
- [License](#license)

# Overview
Biomedisa (https://biomedisa.org) is a free and easy-to-use open-source online platform for segmenting large volumetric images, e.g. CT and MRI scans, at Heidelberg University and the Australian National University. Biomedisa's semi-automated segmentation is based on a smart interpolation of sparsely pre-segmented slices, taking into account the complete underlying image data. In addition, Biomedisa enables deep learning for the fully automated segmentation of series of similar samples. It can be used in combination with segmentation tools such as Amira, ImageJ/Fiji and 3D Slicer. If you are using Biomedisa or the data for your research please cite: Lösel, P.D. et al. [Introducing Biomedisa as an open-source online platform for biomedical image segmentation.](https://www.nature.com/articles/s41467-020-19303-w) *Nat. Commun.* **11**, 5577 (2020).

# Hardware requirements
+ One or more NVIDIA GPUs with compute capability 3.0 or higher or an Intel CPU.
+ 32 GB RAM or more (depending on the size of the image data).

# Software requirements
+ [NVIDIA GPU drivers](https://www.nvidia.com/drivers) for GPU support
+ [CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit-archive) or [Intel Runtime for OpenCL](https://www.intel.com/content/www/us/en/developer/articles/tool/opencl-drivers.html)

# Installation (command-line-only)
+ [Ubuntu 20.04 + Smart Interpolation + CUDA + GPU](https://github.com/biomedisa/biomedisa/blob/master/README/ubuntu2004_interpolation_cuda11.3_gpu_cli.md)
+ [Ubuntu 20.04 + Smart Interpolation + OpenCL + CPU](https://github.com/biomedisa/biomedisa/blob/master/README/ubuntu2004_interpolation_opencl_cpu_cli.md)
+ [Ubuntu 20.04 + Deep Learning](https://github.com/biomedisa/biomedisa/blob/master/README/ubuntu2004_deeplearning_cuda11.3_cli.md)
+ [Windows 10 + Smart Interpolation + CUDA + GPU](https://github.com/biomedisa/biomedisa/blob/master/README/windows10_interpolation_cuda_gpu_cli.md)
+ [Windows 10 + Smart Interpolation + OpenCL + GPU](https://github.com/biomedisa/biomedisa/blob/master/README/windows10_interpolation_opencl_gpu_cli.md)
+ [Windows 10 + Smart Interpolation + OpenCL + CPU](https://github.com/biomedisa/biomedisa/blob/master/README/windows10_interpolation_opencl_cpu_cli.md)
+ [Windows 10 + Deep Learning](https://github.com/biomedisa/biomedisa/blob/master/README/windows10_deeplearning_cuda11.3_cli.md)

# Full installation (GUI)
+ [Ubuntu 20.04](https://github.com/biomedisa/biomedisa/blob/master/README/ubuntu2004_cuda11.3.md)
+ [Ubuntu 22.04](https://github.com/biomedisa/biomedisa/blob/master/README/ubuntu2204_cuda11.8.md)
+ [Windows 10 (21H2 or higher)](https://github.com/biomedisa/biomedisa/blob/master/README/windows11.md)
+ [Windows 11](https://github.com/biomedisa/biomedisa/blob/master/README/windows11.md)

# Biomedisa interpolation

#### Small example
Download the tumor test example from the [gallery](https://biomedisa.org/gallery/) or directly as follows:
```
# Brain tumor
wget --no-check-certificate https://biomedisa.org/download/demo/?id=tumor.tif -O ~/Downloads/tumor.tif
wget --no-check-certificate https://biomedisa.org/download/demo/?id=labels.tumor.tif -O ~/Downloads/labels.tumor.tif
```

Run the Biomedisa interpolation. The result will be saved in `Downloads` as `final.tumor.tif`.
```
# Ubuntu
python3 ~/git/biomedisa/demo/biomedisa_interpolation.py ~/Downloads/tumor.tif ~/Downloads/labels.tumor.tif

# Windows
python git\biomedisa\demo\biomedisa_interpolation.py Downloads\tumor.tif Downloads\labels.tumor.tif
```

#### Further examples
Download further examples from the [gallery](https://biomedisa.org/gallery/) or directly as follows:
```
# Trigonopterus
wget --no-check-certificate https://biomedisa.org/download/demo/?id=trigonopterus.tif -O ~/Downloads/trigonopterus.tif
wget --no-check-certificate https://biomedisa.org/download/demo/?id=labels.trigonopterus_smart.am -O ~/Downloads/labels.trigonopterus_smart.am

# Mineralized wasp
wget --no-check-certificate https://biomedisa.org/download/demo/?id=NMB_F2875.tif -O ~/Downloads/NMB_F2875.tif
wget --no-check-certificate https://biomedisa.org/download/demo/?id=labels.NMB_F2875.tif -O ~/Downloads/labels.NMB_F2875.tif
```

Run the segmentation using e.g. 4 GPUs.
```
# Ubuntu
mpiexec -np 4 python3 ~/git/biomedisa/demo/biomedisa_interpolation.py ~/Downloads/NMB_F2875.tif ~/Downloads/labels.NMB_F2875.tif

# Windows
mpiexec -np 4 python -u git\biomedisa\demo\biomedisa_interpolation.py Downloads\NMB_F2875.tif Downloads\labels.NMB_F2875.tif
```

Obtain uncertainty and smoothing as optional results.
```
python3 ~/git/biomedisa/demo/biomedisa_interpolation.py ~/Downloads/tumor.tif ~/Downloads/labels.tumor.tif --uncertainty --smooth 100
```

Use pre-segmentation with different orientations (not exclusively xy-plane).
```
python3 ~/git/biomedisa/demo/biomedisa_interpolation.py 'path_to_image' 'path_to_labels' --allaxis
```

For more information, type
```
python3 ~/git/biomedisa/demo/biomedisa_interpolation.py --help
```

#### Memory error
If memory errors (either GPU or host memory) occur, you can start the segmentation as follows:
```
python3 ~/git/biomedisa/demo/split_volume.py 'path_to_image' 'path_to_labels' -np 4 -sz 2 -sy 2 -sx 2
```
Where `-n` is the number of GPUs and each axis (`x`,`y` and `z`) is divided into two overlapping parts. The volume is thus divided into `2*2*2=8` subvolumes. These are segmented separately and then reassembled.

# Biomedisa deep learning

#### Automatic segmentation using a trained network
Download a trained neural network and a test image from the [gallery](https://biomedisa.org/gallery/) or directly as follows:
```
wget --no-check-certificate https://biomedisa.org/download/demo/?id=heart.h5 -O ~/Downloads/heart.h5
wget --no-check-certificate https://biomedisa.org/download/demo/?id=testing_axial_crop_pat13.nii.gz -O ~/Downloads/testing_axial_crop_pat13.nii.gz
```

Use the trained neural network to predict the result of the test image with a batch size of 6 batches. The result will be saved in `Downloads` as `final.testing_axial_crop_pat13.tif`.
```
# Ubuntu
python3 ~/git/biomedisa/demo/biomedisa_deeplearning.py ~/Downloads/testing_axial_crop_pat13.nii.gz ~/Downloads/heart.h5 --predict -bs 6

# Windows
python git\biomedisa\demo\biomedisa_deeplearning.py Downloads\testing_axial_crop_pat13.nii.gz Downloads\heart.h5 -p -bs 6
```

#### Train a neural network for automatic segmentation
To train the neural network yourself, download and extract the training data from the [gallery](https://biomedisa.org/gallery/) or directly as follows:
```
wget --no-check-certificate https://biomedisa.org/download/demo/?id=training_heart.tar -O ~/Downloads/training_heart.tar
wget --no-check-certificate https://biomedisa.org/download/demo/?id=training_heart_labels.tar -O ~/Downloads/training_heart_labels.tar
cd ~/Downloads
tar -xf training_heart.tar
tar -xf training_heart_labels.tar
```

Train a neural network with 200 epochs and batch size (-bs) of 24. The result will be saved in `Downloads` as `heart.h5`. If you have a single GPU or low memory, reduce the batch size to 6.
```
# Ubuntu
python3 ~/git/biomedisa/demo/biomedisa_deeplearning.py ~/Downloads/training_heart ~/Downloads/training_heart_labels --train --epochs 200 -bs 24

# Windows
python git\biomedisa\demo\biomedisa_deeplearning.py Downloads\training_heart Downloads\training_heart_labels --train --epochs 200 -bs 24
```

#### Validate the network during training
Specify directories containing validation images and validation labels.
```
python3 ~/git/biomedisa/demo/biomedisa_deeplearning.py ~/Downloads/training_heart ~/Downloads/training_heart_labels --train --val_images ~/Downloads/validation_images --val_labels ~/Downloads/validation_labels
```

Split your data into 80% training data and 20% validation data and use early stopping if there is no improvement within 10 epochs.
```
python3 ~/git/biomedisa/demo/biomedisa_deeplearning.py ~/Downloads/training_heart ~/Downloads/training_heart_labels --train --validation_split 0.8 --early_stopping 10
```

#### Automatic cropping
Both the training and inference data should be cropped to the region of interest for best performance. As an alternative to manual cropping, you can use Biomedisa's AI-based automatic cropping. After training, auto cropping is automatically applied to your inference data.
```
python3 ~/git/biomedisa/demo/biomedisa_deeplearning.py 'path_to_images' 'path_to_labels' --train --crop_data
```

#### Get help
For more information, type
```
python3 ~/git/biomedisa/demo/biomedisa_deeplearning.py --help
```

# Biomedisa features

#### Load and save data (such as Amira Mesh, TIFF, NRRD, NIfTI or DICOM)
```
# import functions
import sys
sys.path.append(path_to_biomedisa)  # e.g. '/home/<user>/git/biomedisa'
from biomedisa_features.biomedisa_helper import load_data, save_data

# load data as numpy array (for DICOM, path_to_data must be a directory containing the slices)
data, header = load_data(path_to_data)

# save data (for TIFF, header=None)
save_data(path_to_data, data, header)
```

#### Create STL mesh from segmentation (label values are saved as attributes)
```
# import functions
import os, sys
sys.path.append(path_to_biomedisa)  # e.g. '/home/<user>/git/biomedisa'
from biomedisa_features.biomedisa_helper import load_data, save_data
from biomedisa_features.create_mesh import get_voxel_spacing, save_mesh

# load segmentation
data, header, extension = load_data(path_to_data, return_extension=True)

# get voxel spacing
xres, yres, zres = get_voxel_spacing(header, data, extension)
print(f'Voxel spacing: x_spacing, y_spacing, z_spacing = {xres}, {yres}, {zres}')

# save stl file
path_to_data = path_to_data.replace(os.path.splitext(path_to_data)[1],'.stl')
save_mesh(path_to_data, data, xres, yres, zres)
```
or call directly
```
python3 git/biomedisa/biomedisa_features/create_mesh.py <path_to_data>
```

# Update Biomedisa
If you have used `git clone`, change to the Biomedisa directory and make a pull request.
```
cd git/biomedisa
git pull
```

If you have installed the full version of Biomedisa (including MySQL database), you also need to update the database.
```
python3 manage.py migrate
```

If you have installed an [Apache Server](https://github.com/biomedisa/biomedisa/blob/master/README/APACHE_SERVER.md), you need to restart the server.
```
sudo service apache2 restart
```

# Releases

For the versions available, see the [list of releases](https://github.com/biomedisa/biomedisa/releases). 

# Authors

* **Philipp D. Lösel**

See also the list of [contributors](https://github.com/biomedisa/biomedisa/blob/master/credits.md) who participated in this project.

# FAQ
Frequently asked questions can be found at: https://biomedisa.org/faq/.

# Citation

If you use the package or the online platform, please cite the following paper.

`Lösel, P.D. et al. Introducing Biomedisa as an open-source online platform for biomedical image segmentation. Nat. Commun. 11, 5577 (2020).`

# License

This project is covered under the **EUROPEAN UNION PUBLIC LICENCE v. 1.2 (EUPL)**.

