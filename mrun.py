#!/usr/bin/env python

import mesos
import mesos_pb2

import os
import logging
import re
import sys
import time
import math
import threading
import socket
import time
import tempfile

from optparse import OptionParser
from subprocess import *

def printOutput(p):
  for line in p.stdout:
      print line,

def startMPIExec(procs, slaves, program):
  os.symlink(os.getcwd() + '/export', work_dir + "/export")
  os.chdir(work_dir)

  hosts = ",".join(slaves)
  cmd = ["./export/bin/mpiexec.hydra", "-genv", "LD_LIBRARY_PATH", work_dir + "/libs", "-launcher", "manual", "-n", str(procs), "-hosts", str(hosts)]
  cmd.extend(program)
  p = Popen(cmd, stdout=PIPE)

  proxy_args = []
  while True:
    line = p.stdout.readline()
    if line == 'HYDRA_LAUNCH_END\n':
      break
    proxy_args.append(line)

  # Print rest MPI output.
  t = threading.Thread(target=printOutput, args=([p]))
  t.start()

  return proxy_args

def finalizeSlaves(callbacks):
  time.sleep(1)
  logging.info("Finalize slaves")
  hosts = []
  for slave in callbacks:
    hosts.append(slave[0])
  proxy_args = startMPIExec(total_procs, hosts, mpi_program)

  proxy_id = 0
  for slave in callbacks:
    chost = slave[0]
    cport = int(slave[1])
    proxy_arg = proxy_args[proxy_id]
    proxy_id += 1

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((chost, cport))
    request = work_dir + ";" + proxy_arg
    s.send(request)
    s.close()

    # TODO(nnielsen): Add retry logic; slave might not be listening yet.

  logging.info("Done finalizing slaves")

class HydraScheduler(mesos.Scheduler):

  def __init__(self, options):
    self.proxiesLaunched = 0
    self.proxiesRunning = 0
    self.proxiesFinished = 0
    self.options = options
    self.startedExec = False
    self.slaves = set()
    self.callbacks = []
    self.finalizeTriggered = False

  def registered(self, driver, fid, masterInfo):
    logging.info("Registered with framework ID %s" % fid.value)

  def resourceOffers(self, driver, offers):
    for offer in offers:
      if self.proxiesLaunched == total_nodes:
        driver.declineOffer(offer.id)
        continue

      cpus = 0
      mem = 0
      tasks = []

      if offer.hostname in self.slaves:
        logging.info("Declining offer: offer from slave already scheduled")


      for resource in offer.resources:
        if resource.name == "cpus":
          cpus = resource.scalar.value
        elif resource.name == "mem":
          mem = resource.scalar.value
        elif resource.name == "ports":
          port = resource.ranges.range[0].begin

      if cpus < cores_per_node or mem < mem_per_node:
        logging.info("Declining offer due to too few resources")
        driver.declineOffer(offer.id)
      else:
        tid = self.proxiesLaunched
        self.proxiesLaunched += 1

        logging.info("Launching proxy on offer %s from %s" % (offer.id, offer.hostname))
        task = mesos_pb2.TaskInfo()
        task.task_id.value = str(tid)
        task.slave_id.value = offer.slave_id.value
        task.name = "task %d " % tid

        cpus = task.resources.add()
        cpus.name = "cpus"
        cpus.type = mesos_pb2.Value.SCALAR
        cpus.scalar.value = cores_per_node

        mem = task.resources.add()
        mem.name = "mem"
        mem.type = mesos_pb2.Value.SCALAR
        mem.scalar.value = mem_per_node

        ports = task.resources.add()
        ports.name = "ports"
        ports.type = mesos_pb2.Value.RANGES
        r = ports.ranges.range.add()
        r.begin = port
        r.end = port

	lib = task.command.environment.variables.add()
	lib.name = "LD_LIBRARY_PATH"
	lib.value = work_dir + "/libs"

        hydra_uri = task.command.uris.add()
        hydra_uri.value = "hdfs://" + name_node + "/hydra/hydra.tgz"
        executable_uri = task.command.uris.add()
        executable_uri.value = "hdfs://" + name_node + "/hydra/" + mpi_program[0]

        task.command.value = "python hydra-proxy.py %d" % port

        tasks.append(task)

        logging.info("Replying to offer: launching proxy %d on host %s" % (tid, offer.hostname))
        logging.info("Call-back at %s:%d" % (offer.hostname, port))

        self.callbacks.append([offer.hostname, port])
        self.slaves.add(offer.hostname)

        driver.launchTasks(offer.id, tasks)

  def statusUpdate(self, driver, update):
    if (update.state == mesos_pb2.TASK_FAILED or
        update.state == mesos_pb2.TASK_KILLED or
        update.state == mesos_pb2.TASK_LOST):
      logging.error("A task finished unexpectedly: " + update.message)
      driver.stop()

    if (update.state == mesos_pb2.TASK_RUNNING):
      self.proxiesRunning += 1
      # Trigger real launch when threshold is met.
      if self.proxiesRunning >= total_nodes and not self.finalizeTriggered:
        self.finalizeTriggered = True
        threading.Thread(target = finalizeSlaves, args = ([self.callbacks])).start()

    if (update.state == mesos_pb2.TASK_FINISHED):
      self.proxiesFinished += 1
      if self.proxiesFinished == total_nodes:
        logging.info("All processes done, exiting")
        driver.stop()

  def offerRescinded(self, driver, offer_id):
    logging.info("Offer %s rescinded" % offer_id)


if __name__ == "__main__":
  parser = OptionParser(usage="Usage: %prog [options] mesos_master mpi_program")
  parser.disable_interspersed_args()
  parser.add_option("-N", "--nodes",
                    help="number of nodes to run processes (default 1)",
                    dest="nodes", type="int", default=1)
  parser.add_option("-n", "--num",
                    help="total number of MPI processes (default 1)",
                    dest="procs", type="int", default=1)
  parser.add_option("-c", "--cpus-per-task",
                    help="number of cores per MPI process (default 1)",
                    dest="cores", type="int", default=1)
  parser.add_option("-m","--mem",
                    help="number of MB of memory per MPI process (default 1GB)",
                    dest="mem", type="int", default=1024)
  parser.add_option("--proxy",
                    help="url to proxy binary", dest="proxy", type="string")
  parser.add_option("--name",
                    help="framework name", dest="name", type="string")
  parser.add_option("--hdfs",
                    help="HDFS Name node", dest="name_node", type="string")
  parser.add_option("-p","--path",
                    help="path to look for MPICH2 binaries (mpiexec)",
                    dest="path", type="string", default="")
  parser.add_option("-v", action="store_true", dest="verbose")

  # Add options to configure cpus and mem.
  (options,args) = parser.parse_args()
  if len(args) < 2:
    print >> sys.stderr, "At least two parameters required."
    print >> sys.stderr, "Use --help to show usage."
    exit(2)


  if options.verbose == True:
    logging.basicConfig(level=logging.INFO)

  total_procs = options.procs
  total_nodes = options.nodes
  cores = options.cores
  procs_per_node = math.ceil(total_procs / total_nodes)
  cores_per_node = procs_per_node * cores
  mem_per_node = options.mem
  mpi_program = args[1:]
  
  name_node = options.name_node
  if name_node == None:
    name_node = os.environ.get("HDFS_NAME_NODE")
    if name_node == None:
      print >> sys.stderr, "HDFS name node not found."
      exit(2)

  logging.info("Connecting to Mesos master %s" % args[0])
  logging.info("Total processes %d" % total_procs)
  logging.info("Total nodes %d" % total_nodes)
  logging.info("Procs per node %d" % procs_per_node)
  logging.info("Cores per node %d" % cores_per_node)

  scheduler = HydraScheduler(options)

  framework = mesos_pb2.FrameworkInfo()
  framework.user = ""

  if options.name is not None:
    framework.name = options.name
  else:
    framework.name = "MPICH2 Hydra : %s" % mpi_program[0]
  
  work_dir = tempfile.mkdtemp()

  driver = mesos.MesosSchedulerDriver(
    scheduler,
    framework,
    args[0])

  sys.exit(0 if driver.run() == mesos_pb2.DRIVER_STOPPED else 1)
