# Installing femb_python

## SLF 7.2

First, enable the EPEL repositories:

yum install -y epel-release
yum update

### Python 2

Install the packages to build ROOT:

yum install -y cmake3 git make gcc-c++ gcc binutils libX11-devel libXpm-devel libXft-devel libXext-devel python redhat-lsb-core python-devel

Download a source tarball of root  v6.08.00+, untar it and enter the directory.

mkdir builddir
cd builddir
cmake3 -DCMAKE_INSTALL_PREFIX=~/root-6.08.02 .. >& logConfigure
cmake3 --build . >& logBuild
cmake3 --build . --target install >& logInstall

Then, install the femb_python dependencies:

yum install git python2-pip python-setuptools python-virtualenv numpy python-matplotlib

### Python 3

Install the packages to build ROOT:

yum install -y cmake3 git make gcc-c++ gcc binutils libX11-devel libXpm-devel libXft-devel libXext-devel python redhat-lsb-core python34 python34-devel

Download a source tarball of root  v6.08.00+, untar it and enter the directory.

mkdir builddir
cd builddir
cmake3 -DCMAKE_INSTALL_PREFIX=~/root-6.08.02-python34 -DPYTHON3=ON -DPYTHON_EXECUTABLE=/usr/bin/python3.4 -DPYTHON_INCLUDE_DIR=/usr/include/python3.4m -DPYTHON_LIBRARY=/usr/lib64/libpython3.4m.so .. >& logConfigure
cmake3 --build . >& logBuild
cmake3 --build . --target install >& logInstall

## Fedora 25

### Python 2

Install the packages to build ROOT:

yum install -y cmake3 git make gcc-c++ gcc binutils libX11-devel libXpm-devel libXft-devel libXext-devel python redhat-lsb-core python-devel 

Download a source tarball of root  v6.08.00+, untar it and enter the directory.

mkdir builddir
cd builddir
cmake3 -DCMAKE_INSTALL_PREFIX=~/root-6.08.02 .. >& logConfigure
cmake3 --build . >& logBuild
cmake3 --build . --target install >& logInstall

Then, install the femb_python dependencies:

yum install git python-pip python-setuptools python-virtualenv numpy python-matplotlib

### Python 3

Install the packages to build ROOT:

yum install -y cmake3 git make gcc-c++ gcc binutils libX11-devel libXpm-devel libXft-devel libXext-devel python redhat-lsb-core python3 python3-devel

Download a source tarball of root  v6.08.00+, untar it and enter the directory.

mkdir builddir
cd builddir
cmake3 -DCMAKE_INSTALL_PREFIX=~/root-6.08.02-python35 -DPYTHON3=ON -DPYTHON_EXECUTABLE=/usr/bin/python3.5 -DPYTHON_INCLUDE_DIR=/usr/include/python3.5m -DPYTHON_LIBRARY=/usr/lib64/libpython3.5m.so .. >& logConfigure
cmake3 --build . >& logBuild
cmake3 --build . --target install >& logInstall


