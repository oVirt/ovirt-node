# Copyright (C) 2008 Red Hat, Inc.
# Written by Chris Lalancette <clalance@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.

require 'utils'

require 'libvirt'

require 'models/storage_task.rb'
require 'models/vm_task.rb'
require 'models/storage_pool.rb'
require 'models/iscsi_storage_pool.rb'
require 'models/nfs_storage_pool.rb'
require 'models/motor_pool.rb'

def refresh_pool(task)
  puts "refresh_pool"

  pool = StoragePool.find(task[:storage_pool_id])

  if pool == nil
    setTaskState(task, Task::STATE_FAILED, "Could not find storage pool")
    return
  end

  if pool[:type] == "IscsiStoragePool"
    storage = Iscsi.new(pool.ip_addr, pool.target)
  elsif pool[:type] == "NfsStoragePool"
    storage = NFS.new(pool.ip_addr, pool.export_path)
  else
    setTaskState(task, Task::STATE_FAILED, "Unknown storage pool type " + pool[:type].to_s)
    return
  end

  # find all of the hosts in the same pool as the storage
  hosts = Host.find(:all, :conditions =>
                    [ "hardware_pool_id = ?", pool.hardware_pool_id ])

  conn = nil
  hosts.each do |host|
    begin
      conn = Libvirt::open("qemu+tcp://" + host.hostname + "/system")

      # if we didn't raise an exception, we connected; get out of here
      break
    rescue
      # if we couldn't connect for whatever reason, just try the next host
      next
    end
  end

  if conn == nil
    setTaskState(task, Task::STATE_FAILED, "Could not find a host to scan storage")
    return
  end

  remote_pool_defined = false
  remote_pool_started = false
  remote_pool = nil

  # here, run through the list of already defined pools on the remote side
  # and see if a pool matching the XML already exists.  If it does
  # we don't try to define it again, we just scan it
  pool_defined = false
  conn.list_defined_storage_pools.each do |remote_pool_name|
    tmppool = conn.lookup_storage_pool_by_name(remote_pool_name)
    doc = Document.new(tmppool.xml_desc(0))

    if storage.xmlequal?(doc.root)
      pool_defined = true
      remote_pool = tmppool
      break
    end
  end
  if not pool_defined
    remote_pool = conn.define_storage_pool_xml(storage.getxml, 0)
    remote_pool.build(0)
    remote_pool_defined = true
  end

  remote_pool_info = remote_pool.info
  if remote_pool_info.state == Libvirt::StoragePool::INACTIVE
    # only try to start the pool if it is currently inactive; in all other
    # states, assume it is already running
    begin
      remote_pool.create(0)
    rescue
      # this can fail, for instance, if the remote storage that the user
      # put in is not actually available.  We just return here with a failure;
      # there's not a lot more we can do
      setTaskState(task, Task::STATE_FAILED,"Could not create storage volume")
      conn.close
      return
    end
    remote_pool_started = true
  end

  vols = remote_pool.list_volumes
  vols.each do |volname|
    volptr = remote_pool.lookup_volume_by_name(volname)
    existing_vol = StorageVolume.find(:first, :conditions =>
                                      [ "path = ?", volptr.path ])
    if existing_vol != nil
      # in this case, this path already exists in the database; just skip
      next
    end

    volinfo = volptr.info

    storage_volume = StorageVolume.new
    storage_volume.path = volptr.path
    storage_volume.size = volinfo.capacity / 1024
    storage_volume.storage_pool_id = pool.id
    storage_volume[:type] = StoragePool::STORAGE_TYPES[pool.get_type_label] + "StorageVolume"
    storage_volume.write_attribute(storage.db_column, volname)
    storage_volume.save
  end
  if remote_pool_started
    remote_pool.destroy
  end
  if remote_pool_defined
    remote_pool.undefine
  end
  conn.close

  # FIXME: if we encounter errors after defining the pool, we should try to
  # clean up after ourselves

  setTaskState(task, Task::STATE_FINISHED)
end
