import sys
import os
import yaml

files = sys.argv[1:]

for f in files:
  f = os.path.relpath(f)
  data = open(f).read()
  print("Checking syntax of '%s'" % f)
  success = list(yaml.load_all(data)) != None
