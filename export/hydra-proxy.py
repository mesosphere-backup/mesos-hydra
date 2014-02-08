#!/usr/bin/env python

import re
import socket
import sys
from subprocess import *

if len(sys.argv) < 2:
  print "usage: hydra-proxy.py <port>"
  sys.exit(1)

port = int(sys.argv[1])
host = 'localhost' #socket.gethostname()

print "Listening on %s:%d" % (host, port)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((host, port))
s.listen(1)
conn, addr = s.accept()
print 'Connected by', addr
data = conn.recv(1024)
conn.close()

# Takes hydra proxy launch command and gather parameters
# Example: HYDRA_LAUNCH: /usr/local/bin/hydra_pmi_proxy --control-port caph:62821 --rmk user --launcher manual --demux poll --pgid 0 --retries 10 --usize -2 --proxy-id 0
m = re.search('hydra_pmi_proxy (.*)', data)
if m is not None:
  args = m.group(1)
  argv = args.split()
  cmd = ["./bin/hydra_pmi_proxy"]
  cmd.extend(argv)
  print "Execute: " + str(cmd)

  # To work around _not_ being on a parallel file system, we use chroot hack.
  os.chroot(os.getcwd())
  p = Popen(cmd)
  p.wait()
else:
  print "Unknown proxy format"
  sys.exit(1)

sys.exit(0)
