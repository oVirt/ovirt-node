class DashboardController < ApplicationController

  def index
    @default_pool = MotorPool.find(:first)
    set_perms(@default_pool)
    @organizational_pools = OrganizationalPool.find(:all)
    @network_maps = NetworkMap.find(:all)
    @host_collections = HostCollection.find(:all)
    @available_hosts = Host.find(:all)
    @available_storage_volumes = StorageVolume.find(:all)
    @hosts = Host.find(:all)
    @storage_volumes = StorageVolume.find(:all)
    @vms = Vm.find(:all)
  end
end
