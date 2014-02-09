all: upload

.PHONY: package upload download_egg

download_egg:
	wget https://s3.amazonaws.com/downloads.mesosphere.io/master/ubuntu/13.10/mesos_0.16.0_amd64.egg

upload: package example
	hadoop fs -rm -f -r hdfs://$(HDFS_NAME_NODE)/hydra
	hadoop fs -mkdir hdfs://$(HDFS_NAME_NODE)/hydra
	hadoop fs -put hydra.tgz hdfs://$(HDFS_NAME_NODE)/hydra/hydra.tgz
	hadoop fs -put hello_world hdfs://$(HDFS_NAME_NODE)/hydra/hello_world

package:
	cd export && tar -cvzf ../hydra.tgz *

example: hello_world.cpp
	mpicc -o hello_world -g -O2 hello_world.cpp
	
