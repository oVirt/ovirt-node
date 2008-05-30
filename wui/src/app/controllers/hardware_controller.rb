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
  
  # retrieves data to be used by availablilty bar charts
  def available_graph
    target =  params[:target]
    available = nil
    used = nil
    if target == 'memory'
        available = @available_memory
        used      = @used_memory
    elsif target == 'storage'
        available = @available_storage
        used      = @used_storage
    elsif target == 'vms'
        available = @available_vms
        used      = @used_vms
    end

    color = 'blue'
    color = 'red' if (used.to_f / (available + used).to_f) > 0.75  # 3/4 is the critical boundry for now

    graph_object = {
       :timepoints => [],
       :dataset => 
        [
            {
                :name => target + "used",
                :values => [used],
                :fill => color,
                :stroke => 'lightgray',
                :strokeWidth => 1
            },
            {
                :name => target + "available",
                :values => [available],
                :fill => 'white',
                :stroke => 'lightgray',
                :strokeWidth => 1
            }
       ]
    }
    render :json => graph_object
  end

  # retrieves data used by history graphs
  def history_graph
    today = DateTime.now
    dates = [ Date::ABBR_MONTHNAMES[today.month] + ' ' + today.day.to_s ]
    1.upto(6){ |x|  # TODO get # of days from wui
       dte = today - x
       dates.push( Date::ABBR_MONTHNAMES[dte.month] + ' ' + dte.day.to_s )
    }
    dates.reverse! # want in ascending order

    target = params[:target]
    peakvalues = nil
    avgvalues  = nil
    if target == 'host_usage'
       peakvalues = [95.97, 91.80, 88.16, 86.64, 99.14, 75.14, 85.69] # TODO real values!
       avgvalues  = [3.39, 2.83, 1.61, 0.00, 4.56, 1.23, 5.32] # TODO real values!
    elsif target == 'storage_usage'
       peakvalues = [11.12, 22.29, 99.12, 13.23, 54.32, 17.91, 50.1] # TODO real values!
       avgvalues  = [19.23, 19.23, 19.23, 29.12, 68.96, 43.11, 0.1] # TODO real values!
    elsif target == 'vm_pool_usage_history'
       peakvalues = [42, 42, 42, 42, 42, 42, 42] # TODO real values!
       avgvalues  = [0, 0, 0, 0, 0, 0, 0] # TODO real values!
    elsif target == 'overall_load'
       peakvalues = [19.68, 20.08, 19.84, 17.76, 0.0, 14.78, 9.71] # TODO real values!
       avgvalues  = [0, 1, 2, 4, 8, 16, 32] # TODO real values!
    end

    graph_object = {
       :timepoints => dates,
       :dataset => 
        [
            {
                :name => target + "peak",
                :values =>  peakvalues,
                :stroke => @peak_color,
                :strokeWidth => 1
            },
            {
                :name => target + "average",
                :values => avgvalues, 
                :stroke => @average_color,
                :strokeWidth => 1
            }
       ]
    }
    render :json => graph_object
  end

  def network_traffic_graph
    target =  params[:target]
    network_load = nil
    if target == 'in'
        network_load      = @network_traffic['in']
    elsif target == 'out'
        network_load = @network_traffic['out']
    elsif target == 'io'
        network_load = @network_traffic['io']
    end

    network_load_remaining = 1024 - network_load

    color = 'blue'
    color = 'red' if (network_load.to_f / 1024.to_f) > 0.75  # 3/4 is the critical boundry for now

    graph_object = {
       :timepoints => [],
       :dataset => 
        [
            {
                :name => target,
                :values => [network_load],
                :fill => color,
                :stroke => 'lightgray',
                :strokeWidth => 1
            },
            {
                :name => target + "remaining",
                :values => [network_load_remaining],
                :fill => 'white',
                :stroke => 'lightgray',
                :strokeWidth => 1
            }
       ]
    }
    render :json => graph_object
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
    if params[:id]
      pre_json
      hosts = @pool.hosts
      find_opts = {}
      include_pool = false
    else
      # FIXME: no permissions or usage checks here yet
      # filtering on which pool to exclude
      id = params[:exclude_id]
      hosts = Host
      find_opts = {:include => :hardware_pool, 
        :conditions => ["pools.id != ?", id]}
      include_pool = true
    end
    attr_list = [:id, :hostname, :uuid, :hypervisor_type, :num_cpus, :cpu_speed, :arch, :memory_in_mb, :is_disabled_str]
    attr_list.insert(2, [:hardware_pool, :name]) if include_pool
    json_list(hosts, attr_list, [:all], find_opts)
  end

  def vm_pools_json
    json_list(Pool, 
              [:id, :name], 
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
      id = params[:exclude_id]
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

    # TODO pull real values in
    @available_memory = 18
    @used_memory = 62
    
    @available_storage = 183
    @used_storage = 61

    @available_vms = 1
    @used_vms = 26

    @peak_color = 'red'
    @average_color = 'blue'

    # TODO pull real values in
    @network_traffic   = { 'in' => 100, 'out' => 1024, 'io' => 200 }
    @network_errors = { 'in' => 0, 'out' => 4, 'io' => 2 }
    @network_trends = { 'in' => 'up', 'out' => 'down', 'io' => 'check' }
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
