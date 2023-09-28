# Windows 10 + CUDA + GPU (command-line-only)

- [Install Microsoft Visual Studio 2022](#install-microsoft-visual-studio-2022)
- [Set Path Variables](#set-path-variables)
- [Install NVIDIA driver](#install-nvidia-driver)
- [Install CUDA Toolkit](#install-cuda-toolkit)
- [Install Microsoft MPI](#install-microsoft-mpi)
- [Install Git](#install-git)
- [Clone Biomedisa](#clone-biomedisa)
- [Install Anaconda3](#install-anaconda3)
- [Install conda environment](#install-conda-environment)
- [Biomedisa examples](#biomedisa-examples)

#### Install Microsoft Visual Studio 2022
Download and install [MS Visual Studio](https://visualstudio.microsoft.com/de/thank-you-downloading-visual-studio/?sku=Community&channel=Release&version=VS2022&source=VSLandingPage&passive=false&cid=2030).
```
Select "Desktop development with C++"
Install
Restart Windows
```

#### Set Path Variables
Open Windows Search  
Type `View advanced system settings`  
Click `Environment Variables...`  
Add the following value to the **System variable** `Path`
Please check whether the path exists and adjust it if necessary. Year `2022` and version number `14.37.32822` can be different.
```
C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.37.32822\bin\Hostx64\x64
```

#### Install NVIDIA Driver
Download and install [NVIDIA](https://www.nvidia.com/Download/Find.aspx?lang=en-us).  
Choose *Windows Driver Type:* Standard  
Choose *Recommended/Beta:* Studio Driver

#### Install CUDA Toolkit
Download and install [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads).

#### Install Microsoft MPI
Download and install [Microsoft MPI](https://www.microsoft.com/en-us/download/details.aspx?id=57467).
```
Select "msmpisetup.exe"
```

#### Install Git
Download and install [Git](https://github.com/git-for-windows/git/releases/download/v2.28.0.windows.1/Git-2.28.0-64-bit.exe).

#### Clone Biomedisa
```
mkdir git
cd git
git clone https://github.com/biomedisa/biomedisa.git
```

#### Install Anaconda3
Download and install [Anaconda3](https://www.anaconda.com/products/individual#windows).

#### Install conda environment
Open Anaconda Prompt (e.g. Windows Search `Anaconda Prompt`).
```
conda env create -f git\biomedisa\conda_environment.yml
```

#### Biomedisa examples
Activate conda environment.
```
conda activate biomedisa
```
Download test files from [Gallery](https://biomedisa.de/gallery/) and run
```
# smart interpolation
python git\biomedisa\demo\biomedisa_interpolation.py Downloads\tumor.tif Downloads\labels.tumor.tif

# deep learning
python git\biomedisa\demo\biomedisa_deeplearning.py Downloads\testing_axial_crop_pat13.nii.gz Downloads\heart.h5 -p -bs 12
```
