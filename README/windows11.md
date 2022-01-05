# Windows 10 (version 21H2 only) and Windows 11
With this you set up an already configured version of Biomedisa in a virtual machine with WSL (~23 GB). This only works on Windows 10 (version 21h2) and Windows 11. If necessary, you can update your system under the Windows settings "Update & Security" or with the [Windows Update Assistant](https://support.microsoft.com/en-us/topic/windows-10-update-assistant-3550dfb2-a015-7765-12ea-fba2ac36fb3f). The Biomedisa installation will be located in `C:\Users\username\AppData\Biomedisa-2x.xx.x`.

- [Install NVIDIA driver](#install-nvidia-driver)
- [Install WSL2 with administrative privileges](#install-wsl2-with-administrative-privileges)
- [Reboot and activate "Virtualization" in the BIOS](#reboot-and-activate-virtualization-in-the-bios)
- [Download and extract Biomedisa](#download-and-extract-biomedisa)
- [Run installation script](#run-install-script)
- [Start Biomedisa using the shortcut](#start-biomedisa-using-the-shortcut)
- [Delete installation files](#delete-installation-files)
- [Uninstallation](#uninstallation)

#### Install NVIDIA driver
Download and install [NVIDIA](https://www.nvidia.com/Download/Find.aspx?lang=en-us) driver.

#### Enable "Virtualization" in the BIOS
At Intel it is typically called "Intel Virtualization Technology" and can be found under "CPU configuration". You may arrive at this menu by clicking on “Advanced” or “Advanced Mode”. Depending upon your PC, look for any of these or similar names such as Hyber-V, Vanderpool, SVM, AMD-V, Intel Virtualization Technology or VT-X.

#### Install WSL2 with administrative privileges and reboot
```
wsl --install
```

#### Download and extract installation files
+ [Biomedisa + Cuda 11.0 (Pascal, Volta)](https://biomedisa.org/media/Biomedisa-22.01.1p.zip)
+ [Biomedisa + Cuda 11.4 (Ampere)](https://biomedisa.org/media/Biomedisa-22.01.1.zip)

#### Run installation script
```
install.cmd
```

#### Start Biomedisa
Login as superuser "biomedisa" with password "biomedisa".

#### Delete installation files
Delete the downloaded files to save space.

#### Uninstallation
Find your Biomedisa version.
```
wsl -l -v
```
Remove specific Biomedisa version.
```
wsl --unregister Biomedisa-2x.xx.x
```