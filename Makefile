all: upload

HDFS_NAME_NODE=foobar

.PHONY: package
upload: package
	hadoop fs -rm -f -r hdfs://$(HDFS_NAME_NODE)/hydra
	hadoop fs -mkdir hdfs://$(HDFS_NAME_NODE)/hydra
	hadoop fs -put hydra.tgz hdfs://$(HDFS_NAME_NODE)/hydra/hydra.tgz

package:
	cd export && tar -cvzf ../hydra.tgz *
