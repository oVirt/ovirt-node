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
#

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
      return
    end
    if params[:ajax]
      render :layout => 'tabs-and-content'
    end
    if params[:nolayout]
      render :layout => false
    end
  end
  
  def json_view_tree
    json_tree_internal(Permission::PRIV_VIEW, false)
  end
  def json_move_tree
    json_tree_internal(Permission::PRIV_MODIFY, true)
  end
  def json_tree_internal(privilege, filter_vm_pools)
    id = params[:id]
    if id
      @pool = Pool.find(id)
      set_perms(@pool)
      unless @pool.has_privilege(@user, privilege)
        flash[:notice] = 'You do not have permission to access this hardware pool: redirecting to top level'
        redirect_to :controller => "dashboard"
        return
      end
    end
    if @pool
      pools = @pool.children
      pools = Pool.select_hardware_pools(pools) if filter_vm_pools
      open_list = []
    else
      pools = Pool.list_for_user(get_login_user,Permission::PRIV_VIEW)
      pools = Pool.select_hardware_pools(pools) if filter_vm_pools
      current_id = params[:current_id]
      if current_id
        current_pool = Pool.find(current_id)
        open_list = current_pool.self_and_ancestors
      else
        open_list = []
      end
    end

    render :json => Pool.nav_json(pools, open_list, filter_vm_pools)
  end

  def show_vms
    show
  end

  def show_users    
    @roles = Permission::ROLES.keys
    show
  end

  def show_hosts    
    @hardware_pools = HardwarePool.find :all
    show
  end
  
  def show_graphs
    show
  end

  def show_storage
    show
    @hardware_pools = HardwarePool.find :all
  end

  def quick_summary
    pre_show
    set_perms(@perm_obj)
    unless @can_view
      flash[:notice] = 'You do not have permission to view this Hardware Pool: redirecting to top level'
      redirect_to :action => 'list'
    end
    render :layout => 'selection'    
  end

  def hosts_json
    if params[:exclude_host]
      pre_json
      hosts = @pool.hosts
      find_opts = {:conditions => ["id != ?", params[:exclude_host]]}
      include_pool = false
    elsif params[:id]
      pre_json
      hosts = @pool.hosts
      find_opts = {}
      include_pool = false
    else
      # FIXME: no permissions or usage checks here yet
      # filtering on which pool to exclude
      id = params[:exclude_pool]
      hosts = Host
      find_opts = {:include => :hardware_pool, 
        :conditions => ["pools.id != ?", id]}
      include_pool = true
    end
    attr_list = []
    attr_list << :id if params[:checkboxes]
    attr_list << :hostname
    attr_list << [:hardware_pool, :name] if include_pool
    attr_list += [:uuid, :hypervisor_type, :num_cpus, :cpu_speed, :arch, :memory_in_mb, :status_str, :id]
    json_list(hosts, attr_list, [:all], find_opts)
  end

  def vm_pools_json
    json_list(Pool, 
              [:id, :name, :id], 
              [@pool, :children],
              {:finder => 'call_finder', :conditions => ["type = 'VmResourcePool'"]})
  end

  def users_json
    json_list(@pool.permissions, 
              [:id, :uid, :user_role])
  end

  def storage_pools_json
    if params[:id]
      pre_json
      storage_pools = @pool.storage_pools
      find_opts = {}
      include_pool = false
    else
      # FIXME: no permissions or usage checks here yet
      # filtering on which pool to exclude
      id = params[:exclude_pool]
      storage_pools = StoragePool
      find_opts = {:include => :hardware_pool, 
        :conditions => ["pools.id != ?", id]}
      include_pool = true
    end
    attr_list = [:id, :display_name, :ip_addr, :get_type_label]
    attr_list.insert(2, [:hardware_pool, :name]) if include_pool
    json_list(storage_pools, attr_list, [:all], find_opts)
  end

  def storage_volumes_json
    json_list(@pool.all_storage_volumes, 
              [:display_name, :size_in_gb, :get_type_label])
  end

  def move
    pre_modify
    @resource_type = params[:resource_type]
    render :layout => 'popup'    
  end

  def new
    @resource_type = params[:resource_type]
    @resource_ids = params[:resource_ids]
    render :layout => 'popup'    
  end

  def create
    resource_type = params[:resource_type]
    resource_ids_str = params[:resource_ids]
    resource_ids = []
    resource_ids = resource_ids_str.split(",").collect {|x| x.to_i} if resource_ids_str
    begin
      @pool.create_with_resources(@parent, resource_type, resource_ids)
      reply = { :object => "pool", :success => true, 
                        :alert => "Hardware Pool was successfully created." }
      reply[:resource_type] = resource_type if resource_type
      render :json => reply
    rescue
      render :json => { :object => "pool", :success => false, 
                        :errors => @pool.errors.localize_error_messages.to_a  }
    end

  end

  def edit
    render :layout => 'popup'    
  end

  def update
    begin
      @pool.update_attributes!(params[:pool])
      render :json => { :object => "pool", :success => true, 
                        :alert => "Hardware Pool was successfully modified." }
    rescue
      render :json => { :object => "pool", :success => false, 
                        :errors => @pool.errors.localize_error_messages.to_a}
    end
  end

  #FIXME: we need permissions checks. user must have permission on src pool
  # in addition to the current pool (which is checked). We also need to fail
  # for hosts that aren't currently empty
  def add_hosts
    host_ids_str = params[:resource_ids]
    host_ids = host_ids_str.split(",").collect {|x| x.to_i}

    begin
      @pool.transaction do
        @pool.move_hosts(host_ids, @pool.id)
      end
      render :json => { :object => "host", :success => true, 
        :alert => "Hosts were successfully added to this Hardware pool." }
    rescue
      render :json => { :object => "host", :success => false, 
        :alert => "Error adding Hosts to this Hardware pool." }
    end
  end

  #FIXME: we need permissions checks. user must have permission on src pool
  # in addition to the current pool (which is checked). We also need to fail
  # for hosts that aren't currently empty
  def move_hosts
    target_pool_id = params[:target_pool_id]
    host_ids_str = params[:resource_ids]
    host_ids = host_ids_str.split(",").collect {|x| x.to_i}
    
    begin
      @pool.transaction do
        @pool.move_hosts(host_ids, target_pool_id)
      end
      render :json => { :object => "host", :success => true, 
        :alert => "Hosts were successfully moved." }
    rescue
      render :json => { :object => "host", :success => false, 
        :alert => "Error moving hosts." }
    end
  end

  #FIXME: we need permissions checks. user must have permission on src pool
  # in addition to the current pool (which is checked). We also need to fail
  # for storage that aren't currently empty
  def add_storage
    storage_pool_ids_str = params[:resource_ids]
    storage_pool_ids = storage_pool_ids_str.split(",").collect {|x| x.to_i}
    
    begin
      @pool.transaction do
        @pool.move_storage(storage_pool_ids, @pool.id)
      end
      render :json => { :object => "storage_pool", :success => true, 
        :alert => "Storage Pools were successfully added to this Hardware pool." }
    rescue
      render :json => { :object => "storage_pool", :success => false, 
        :alert => "Error adding storage pools to this Hardware pool." }
    end
  end

  #FIXME: we need permissions checks. user must have permission on src pool
  # in addition to the current pool (which is checked). We also need to fail
  # for storage that aren't currently empty
  def move_storage
    target_pool_id = params[:target_pool_id]
    storage_pool_ids_str = params[:resource_ids]
    storage_pool_ids = storage_pool_ids_str.split(",").collect {|x| x.to_i}

    begin
      @pool.transaction do
        @pool.move_storage(storage_pool_ids, target_pool_id)
      end
      render :json => { :object => "storage_pool", :success => true, 
        :alert => "Storage Pools were successfully moved." }
    rescue
      render :json => { :object => "storage_pool", :success => false, 
        :alert => "Error moving storage pools." }
    end
  end

  def removestorage
    pre_modify
    render :layout => 'popup'    
  end

  def destroy
    parent = @pool.parent
    if not(parent)
      alert="You can't delete the top level Hardware pool."
      success=false
    elsif not(@pool.children.empty?)
      alert = "You can't delete a Pool without first deleting its children."
      success=false
    else
      if @pool.move_contents_and_destroy
        alert="Hardware Pool was successfully deleted."
        success=true
      else
        alert="Failed to delete hardware pool."
        success=false
      end
    end
    render :json => { :object => "pool", :success => success, :alert => alert }
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
