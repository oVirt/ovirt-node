
import logging
import time
import os
import subprocess
import urllib2
import sys

logger = logging.getLogger(__name__)
logging.basicConfig( \
    format='%(levelname)s - %(asctime)s - %(module)s - %(message)s', \
    level=logging.DEBUG)
# Picking up from client-bootstrap.sh
class Igor(object):
  def __init__(self):
    for name in ["APIURL", "SESSION", "CURRENT_STEP", "TESTSUITE", "LIBDIR"]:
      v = "__%s__" % name
      k = "IGOR_%s" % name
      if k in os.environ:
        v = os.environ[k]
      self.__dict__[name.lower()] = v

igor = Igor()

def highlight(txt, char='-'):
  """Surround txt with rules

  >>> highlight("txt")
  ---
  txt
  ---
  """
  rule = char * len(txt)
  return "{rule}\n{txt}\n{rule}".format(rule=rule, txt=txt)

def debug(msg):
  logger.debug(msg) 

def run(cmd, with_retval=False):
  """Run a command cmd.

  >>> run("echo 0")
  '0'
  """
  debug("Running: %s" % cmd)
  proc = subprocess.Popen(cmd, shell=True, \
                          stdout=subprocess.PIPE, \
                          stderr=subprocess.PIPE)
  (stdout, stderr) = proc.communicate()
  proc.wait()
  if stderr:
      logger.warning(stderr)
  r = stdout.strip()
  if with_retval:
      r = (proc.returncode, stdout.strip())
  return r

def add_searchpath(p):
  logger.debug("Adding python searchpath: %s" % p)
  sys.path.append(p)

def debug_curl(url):
  """Curl a URL
  >>> debug_curl("localhost")
  ''
  """
  debug("Calling '%s'" % url)
  return run("curl --silent '%s'" % url)

def api_url(p):
  """Build an api url
  >>> api_url("p")
  '__APIURL__/p'
  """
  return os.path.join(igor.apiurl, p)

def api_call(p):
  """Build and curl an API URL
  >>> api_call("p")
  ''
  """
  return debug_curl(api_url(p))

def step_succeeded():
  api_call("jobs/{session}/step/{step}/success".format(session=igor.session, \
                                                      step=igor.current_step))

def step_failed():
  api_call("jobs/{session}/step/{step}/failed".format(session=igor.session, \
                                                     step=igor.current_step))

def annotate_step(annotation):
  debug("Adding annotation to current step: '%s'" % annotation)
  url = api_url("jobs/{session}/step/current/annotate".format(
                                                        session=igor.session))
  __put_data(url, annotation)


def add_artifact(dst, filename):
  if not os.path.exists(filename):
    raise Exception(("Failed to add artifact '%s', because file '%s' does " + \
                     "not exist") % (dst, filename))

  debug("Adding artifact '%s': '%s'" % (dst, filename))
  url = api_url("jobs/{session}/artifacts/{dst}".format(
                                                        session=igor.session, \
                                                        dst=dst))

  data = open(filename, "rb").read()
  __put_data(url, data)


def touch(filename, comment=""):
  with open(filename, "w") as f:
    f.write(comment)


def __put_data(url, data):
  opener = urllib2.build_opener(urllib2.HTTPHandler)
  request = urllib2.Request(url, data=data)
  request.add_header('Content-Type', 'text/plain')
  request.get_method = lambda: 'PUT'
  resp = opener.open(request)

def quit_testing():
  """This function ends the looping through all testcases, this is needed for
  e.g. reboots
  """
  logger.info("Request to end testing service loop")
  touch("/tmp/quit-testing")


def set_reboot_marker():
  logger.info("Setting reboot marker")
  touch("/tmp/reboot-requested", "This file was created to track if a " + \
                                 "reboot happened.")

def request_reboot():
  logger.info("Express request to reboot")
  set_reboot_marker()
  quit_testing()

# vim: set sw=2:
