require 'rexml/document'
include REXML

def findHostSLA(vm)
  host = nil

  vm.vm_resource_pool.get_hardware_pool.hosts.each do |curr|
    # FIXME: we probably need to add in some notion of "load" into this check
    if curr.num_cpus >= vm.num_vcpus_allocated \
      and curr.memory >= vm.memory_allocated \
      and not curr.is_disabled.nil? and curr.is_disabled == 0 \
      and curr.state == Host::STATE_AVAILABLE \
      and (vm.host_id.nil? or (not vm.host_id.nil? and vm.host_id != curr.id))
      host = curr
      break
    end
  end

  if host == nil
    # we couldn't find a host that matches this criteria
    raise "No host matching VM parameters could be found"
  end

  return host
end

def findHost(host_id)
  host = Host.find(:first, :conditions => [ "id = ?", host_id])

  if host == nil
    # Hm, we didn't find the host_id.  Seems odd.  Return a failure
    raise "Could not find host_id " + host_id.to_s
  end

  return host
end

def String.random_alphanumeric(size=16)
  s = ""
  size.times { s << (i = Kernel.rand(62); i += ((i < 10) ? 48 : ((i < 36) ? 55 : 61 ))).chr }
  s
end

def all_storage_pools(conn)
  all_pools = conn.list_defined_storage_pools
  all_pools.concat(conn.list_storage_pools)
  return all_pools
end

def teardown_storage_pools(conn)
  # FIXME: this needs to get a *lot* smarter.  In particular, we want to make
  # sure we can tear down unused pools even when there are other guests running
  if conn.list_domains.empty?
    # OK, there are no running guests on this host anymore.  We can teardown
    # any storage pools that are there without fear
    all_storage_pools(conn).each do |remote_pool_name|
      begin
        pool = conn.lookup_storage_pool_by_name(remote_pool_name)
        pool.destroy
        pool.undefine
      rescue
        # do nothing if any of this failed; the worst that happens is that
        # we leave a pool configured
        puts "Could not teardown pool " + remote_pool_name + "; skipping"
      end
    end
  end
end

def connect_storage_pools(conn, vm)
  # here, build up a list of already defined pools.  We'll use it
  # later to see if we need to define new pools for the storage or just
  # keep using existing ones

  defined_pools = []
  all_storage_pools(conn).each do |remote_pool_name|
    defined_pools << conn.lookup_storage_pool_by_name(remote_pool_name)
  end

  storagedevs = []
  vm.storage_volumes.each do |volume|
    # here, we need to iterate through each volume and possibly attach it
    # to the host we are going to be using
    storage_pool = volume.storage_pool

    if storage_pool == nil
      # Hum.  Specified by the VM description, but not in the storage pool?
      # continue on and hope for the best
      # FIXME: probably want a print to the logs here
      next
    end

    if storage_pool[:type] == "IscsiStoragePool"
      thisstorage = Iscsi.new(storage_pool.ip_addr, storage_pool[:target])
    elsif storage_pool[:type] == "NfsStoragePool"
      thisstorage = NFS.new(storage_pool.ip_addr, storage_pool.export_path)
    else
      # Hm, a storage type we don't understand; skip it
      puts "Storage type " + storage_pool[:type] + " is not understood; skipping"
      next
    end

    thepool = nil
    defined_pools.each do |pool|
      doc = Document.new(pool.xml_desc)
      root = doc.root

      if thisstorage.xmlequal?(doc.root)
        thepool = pool
        break
      end
    end

    if thepool == nil
      thepool = conn.define_storage_pool_xml(thisstorage.getxml)
      thepool.build
      thepool.create
    elsif thepool.info.state == Libvirt::StoragePool::INACTIVE
      # only try to start the pool if it is currently inactive; in all other
      # states, assume it is already running
      thepool.create
    end

    storagedevs << thepool.lookup_volume_by_name(volume.read_attribute(thisstorage.db_column)).path
  end

  return storagedevs
end

class StorageType
  attr_reader :db_column

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
    @db_column = 'lun'

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
    @db_column = 'filename'

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
