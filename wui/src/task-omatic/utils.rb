require 'rexml/document'
include REXML

require 'models/task'

def setTaskState(task, state, msg = nil)
  task.state = state
  task.message = msg
  task.save
end

def String.random_alphanumeric(size=16)
  s = ""
  size.times { s << (i = Kernel.rand(62); i += ((i < 10) ? 48 : ((i < 36) ? 55 : 61 ))).chr }
  s
end

class StorageType
  def xmlequal?(docroot)
    return false
  end

  def getxml
    return @xml.to_s
  end
end

class Iscsi < StorageType
  def initialize(ipaddr, target)
    @type = 'iscsi'
    @ipaddr = ipaddr
    @target = target

    @xml = Document.new
    @xml.add_element("pool", {"type" => @type})

    @xml.root.add_element("name")

    @xml.root.elements["name"].text = String.random_alphanumeric

    @xml.root.add_element("source")
    @xml.root.elements["source"].add_element("host", {"name" => @ipaddr})
    @xml.root.elements["source"].add_element("device", {"path" => @target})

    @xml.root.add_element("target")
    @xml.root.elements["target"].add_element("path")
    @xml.root.elements["target"].elements["path"].text = "/dev/disk/by-id"
  end

  def xmlequal?(docroot)
    return (docroot.attributes['type'] == @type and
      docroot.elements['source'].elements['host'].attributes['name'] == @ipaddr and
      docroot.elements['source'].elements['device'].attributes['path'] == @target)
  end
end

class NFS < StorageType
  def initialize(host, remote_path)
    @type = 'netfs'
    @host = host
    @remote_path = remote_path
    @name = String.random_alphanumeric

    @xml = Document.new
    @xml.add_element("pool", {"type" => @type})

    @xml.root.add_element("name")

    @xml.root.elements["name"].text = @name

    @xml.root.add_element("source")
    @xml.root.elements["source"].add_element("host", {"name" => @host})
    @xml.root.elements["source"].add_element("dir", {"path" => @remote_path})
    @xml.root.elements["source"].add_element("format", {"type" => "nfs"})

    @xml.root.add_element("target")
    @xml.root.elements["target"].add_element("path")
    @xml.root.elements["target"].elements["path"].text = "/mnt/" + @name
  end

  def xmlequal?(docroot)
    return (docroot.attributes['type'] == @type and
      docroot.elements['source'].elements['host'].attributes['name'] == @host and
      docroot.elements['source'].elements['dir'].attributes['path'] == @remote_path)
  end
end
