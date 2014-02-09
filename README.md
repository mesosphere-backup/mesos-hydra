mesos-hydra
===========

MPICH2 Hydra scheduler for Apache Mesos.

The stock MPI framework in Mesos is targeted MPICH2 with MPD process management. This framework allows users to use the default Hydra process manager.

Usage:

    $ ./mrun -N <#Nodes> -n <#MPI processes> -c <#Cores per MPI process> <leading-master> <mpi-program>

This is still a experimental framework and any participation and feedback is appreciated.

## Installation on Elastic Mesos

First off, go ahead and launch a cluster at http://elastic.mesosphere.io.
Then log into one of the master nodes and fetch the Hydra framework:

    $ wget https://github.com/mesosphere/mesos-hydra/archive/master.zip
    $ unzip master.zip
    $ cd mesos-hydra-master
    $ sudo aptitude install python2.7-protobuf python-distribute make g++ build-essential gfortran libcr0 default-jdk
    $ wget http://www.cebacad.net/files/mpich/ubuntu/mpich-3.1rc2/mpich_3.1rc2-1ubuntu_amd64.deb
    $ sudo dpkg -i mpich_3.1rc2-1ubuntu_amd64.deb
    $ export HDFS_NAME_NODE=<hdfs_name_node>
    $ make download_egg
    $ make
    $ ./mrun -N 3 -n 6 <leading_master> ./hello_world
    I0209 02:54:30.842380 17588 sched.cpp:218] No credentials provided. Attempting to register without authentication
    I0209 02:54:30.842560 17588 sched.cpp:230] Detecting new master
    Number of tasks= 6 My rank= 1 Running on ec2-54-211-204-163.compute-1.amazonaws.com
    Number of tasks= 6 My rank= 0 Running on ec2-54-204-134-8.compute-1.amazonaws.com
    Number of tasks= 6 My rank= 3 Running on ec2-54-204-134-8.compute-1.amazonaws.com
    Number of tasks= 6 My rank= 2 Running on ec2-107-21-190-250.compute-1.amazonaws.com
    Number of tasks= 6 My rank= 5 Running on ec2-107-21-190-250.compute-1.amazonaws.com
    Number of tasks= 6 My rank= 4 Running on ec2-54-211-204-163.compute-1.amazonaws.com
    
    
## Known issues

### Missing library dependencies

MPICH2 usually expects a mounted parallel filesystem but mesos-hydra only use and depends on HDFS. This means that necessary libraries needs to be shipped with the MPI command to the slaves. This can be worked around by copying the needed libraries to export/libs and rerun make.

### mrun hangs with node, process configuration X

mesos-hydra will decline offers indefinitely if too greedy resource constraints have been set up (for example requiring more cores than nodes provide). This will make mrun hang and should be avoided if possible.
