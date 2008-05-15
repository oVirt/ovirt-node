# 
# Copyright (C) 2008 Red Hat, Inc.
# Written by Scott Seago <sseago@redhat.com>
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

class HardwareController < ApplicationController

  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  before_filter :pre_json, :only => [:vm_pools_json, :users_json, 
                                     :storage_volumes_json]
  before_filter :pre_modify, :only => [:add_hosts, :move_hosts, 
                                       :add_storage, :move_storage, 
                                       :create_storage, :delete_storage]


  def show
    set_perms(@perm_obj)
    unless @can_view
      flash[:notice] = 'You do not have permission to view this hardware pool: redirecting to top level'
      redirect_to :controller => "dashboard"
    end
  end
  
  def json
    id = params[:id]
    if id
      @pool = Pool.find(id)
      set_perms(@pool)
      unless @can_view
        flash[:notice] = 'You do not have permission to view this hardware pool: redirecting to top level'
        redirect_to :controller => "dashboard"
        return
      end
    end
    if @pool
      pools = @pool.children
      open_list = []
    else
      pools = Pool.list_for_user(get_login_user,Permission::PRIV_VIEW)
      current_id = params[:current_id]
      if current_id
        current_pool = Pool.find(current_id)
        open_list = current_pool.self_and_ancestors
      else
        open_list = []
      end
    end

    render :json => Pool.nav_json(pools, open_list)
  end

  def show_vms
    show
  end

  def show_users
    show
    @roles = Permission::ROLES.keys
  end

  def show_hosts
    show
    @hardware_pools = HardwarePool.find :all
  end
  
  def show_graphs
    show
  end

  def show_storage
    show
    @hardware_pools = HardwarePool.find :all
  end

  def hosts_json
    if params[:id]
      pre_json
      hosts = @pool.hosts
    else
      # FIXME: no permissions checks here yet, no filtering of current pool yet
      hosts = Host.find(:all)
    end
    json_list(hosts, 
              [:id, :hostname, :uuid, :hypervisor_type, :num_cpus, :cpu_speed, :arch, :memory_in_mb, :is_disabled_str])
  end

  def vm_pools_json
    json_list(@pool.sub_vm_resource_pools, 
              [:id, :name])
  end

  def users_json
    json_list(@pool.permissions, 
              [:user, :user_role])
  end

  def storage_pools_json
    if params[:id]
      pre_json
      storage_pools = @pool.storage_pools
    else
      # FIXME: no permissions checks here yet, no filtering of current pool yet
      storage_pools = StoragePool.find(:all)
    end
    json_list(storage_pools, 
              [:id, :display_name, :ip_addr, :get_type_label])
  end

  def storage_volumes_json
    json_list(@pool.all_storage_volumes, 
              [:display_name, :size_in_gb, :get_type_label])
  end

  def new
    @pools = @pool.self_and_like_siblings
  end

  def create
    if @pool.create_with_parent(@parent)
      flash[:notice] = 'Hardware Pool successfully created'
      redirect_to  :action => 'show', :id => @pool
    else
      render :action => "new"
    end
  end

  def edit
  end

  def update
    if @pool.update_attributes(params[:pool])
      flash[:notice] = 'Hardware Pool was successfully updated.'
      redirect_to  :action => 'show', :id => @pool
    else
      render :action => "edit"
    end
  end

  #FIXME: we need permissions checks. user must have permission on src pool
  # in addition to the current pool (which is checked). We also need to fail
  # for hosts that aren't currently empty
  def add_hosts
    host_ids_str = params[:host_ids]
    host_ids = host_ids_str.split(",").collect {|x| x.to_i}
    
    @pool.transaction do
      hosts = Host.find(:all, :conditions => "id in (#{host_ids.join(', ')})")
      hosts.each do |host|
        host.hardware_pool = @pool
        host.save!
      end
    end
    render :text => "added hosts (#{host_ids.join(', ')})"
  end

  #FIXME: we need permissions checks. user must have permission on src pool
  # in addition to the current pool (which is checked). We also need to fail
  # for hosts that aren't currently empty
  def move_hosts
    target_pool_id = params[:target_pool_id]
    host_ids_str = params[:host_ids]
    host_ids = host_ids_str.split(",").collect {|x| x.to_i}
    
    @pool.transaction do
      hosts = Host.find(:all, :conditions => "id in (#{host_ids.join(', ')})")
      hosts.each do |host|
        host.hardware_pool_id = target_pool_id
        host.save!
      end
    end
    render :text => "added hosts (#{host_ids.join(', ')})"
  end

  #FIXME: we need permissions checks. user must have permission on src pool
  # in addition to the current pool (which is checked). We also need to fail
  # for storage that aren't currently empty
  def add_storage
    storage_pool_ids_str = params[:storage_pool_ids]
    storage_pool_ids = storage_pool_ids_str.split(",").collect {|x| x.to_i}
    
    @pool.transaction do
      storage_pools = StoragePool.find(:all, :conditions => "id in (#{storage_pool_ids.join(', ')})")
      storage_pools.each do |storage_pool|
        storage_pool.hardware_pool = @pool
        storage_pool.save!
      end
    end
    render :text => "added storage (#{storage_pool_ids.join(', ')})"
  end

  #FIXME: we need permissions checks. user must have permission on src pool
  # in addition to the current pool (which is checked). We also need to fail
  # for storage that aren't currently empty
  def move_storage
    target_pool_id = params[:target_pool_id]
    storage_pool_ids_str = params[:storage_pool_ids]
    storage_pool_ids = storage_pool_ids_str.split(",").collect {|x| x.to_i}
    
    @pool.transaction do
      storage = StoragePool.find(:all, :conditions => "id in (#{storage_pool_ids.join(', ')})")
      storage.each do |storage_pool|
        storage_pool.hardware_pool_id = target_pool_id
        storage_pool.save!
      end
    end
    render :text => "added storage (#{storage_pool_ids.join(', ')})"
  end

  def destroy
    parent = @pool.parent
    if not(parent)
      flash[:notice] = "You can't delete the top level Hardware pool."
      redirect_to :action => 'show', :id => @pool
    elsif not(@pool.children.empty?)
      flash[:notice] = "You can't delete a Pool without first deleting its children."
      redirect_to :action => 'show', :id => @pool
    else
      @pool.move_contents_and_destroy
      flash[:notice] = 'Hardware Pool successfully destroyed'
      redirect_to :action => 'show', :id => @pool.parent_id
    end
  end

  private
  #filter methods
  def pre_new
    @pool = HardwarePool.new
    @parent = Pool.find(params[:parent_id])
    @perm_obj = @parent
    @current_pool_id=@parent.id
  end
  def pre_create
    @pool = HardwarePool.new(params[:pool])
    @parent = Pool.find(params[:parent_id])
    @perm_obj = @parent
    @current_pool_id=@parent.id
  end
  def pre_edit
    @pool = HardwarePool.find(params[:id])
    @parent = @pool.parent
    @perm_obj = @pool
    @current_pool_id=@pool.id
  end
  def pre_show
    @pool = HardwarePool.find(params[:id])
    @perm_obj = @pool
    @current_pool_id=@pool.id
  end
  def pre_json
    pre_show
    show
  end
  def pre_modify
    pre_edit
    authorize_admin
  end
end
