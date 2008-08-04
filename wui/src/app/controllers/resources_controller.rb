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

class ResourcesController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  before_filter :pre_json, :only => [:vms_json, :users_json]
  before_filter :pre_vm_actions, :only => [:vm_actions]

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @user = get_login_user
    @vm_resource_pools = VmResourcePool.list_for_user(@user, Permission::PRIV_VIEW)
    @vms = Set.new
    @vm_resource_pools.each { |vm_resource_pool| @vms += vm_resource_pool.vms}
    @vms = @vms.entries
    @action_values = [["Suspend", VmTask::ACTION_SUSPEND_VM],
                      ["Resume", VmTask::ACTION_RESUME_VM],
                      ["Save", VmTask::ACTION_SAVE_VM],
                      ["Restore", VmTask::ACTION_RESTORE_VM]]
  end

  # resource's summary page
  def show
    set_perms(@perm_obj)
    @is_hwpool_admin = @vm_resource_pool.parent.can_modify(@user)
    @action_values = [["Suspend", VmTask::ACTION_SUSPEND_VM],
                      ["Resume", VmTask::ACTION_RESUME_VM],
                      ["Save", VmTask::ACTION_SAVE_VM],
                      ["Restore", VmTask::ACTION_RESTORE_VM]]
    unless @can_view
      flash[:notice] = 'You do not have permission to view this VM Resource Pool: redirecting to top level'
      redirect_to :action => 'list'
    end
    if params[:ajax]
      render :layout => 'tabs-and-content'
    end
    if params[:nolayout]
      render :layout => false
    end
  end

  def quick_summary
    pre_show
    set_perms(@perm_obj)
    @is_hwpool_admin = @vm_resource_pool.parent.can_modify(@user)
    unless @can_view
      flash[:notice] = 'You do not have permission to view this VM Resource Pool: redirecting to top level'
      redirect_to :action => 'list'
    end
    render :layout => 'selection'    
  end

  # resource's vms list page
  def show_vms    
    @actions = [VmTask.label_and_action(VmTask::ACTION_START_VM),
                (VmTask.label_and_action(VmTask::ACTION_SHUTDOWN_VM) << "break"),
                VmTask.label_and_action(VmTask::ACTION_SUSPEND_VM),
                VmTask.label_and_action(VmTask::ACTION_RESUME_VM),
                VmTask.label_and_action(VmTask::ACTION_SAVE_VM),
                VmTask.label_and_action(VmTask::ACTION_RESTORE_VM)]
    show
  end

  # resource's users list page
  def show_users    
    @roles = Permission::ROLES.keys
    show
  end

  def vms_json
    json_list(@vm_resource_pool.vms, 
              [:id, :description, :uuid, :num_vcpus_allocated, :memory_allocated_in_mb, :vnic_mac_addr, :state, :id])
  end

  def users_json
    json_list(@vm_resource_pool.permissions, 
              [:grid_id, :uid, :user_role, :source])
  end

  def new
    render :layout => 'popup'    
  end

  def create
    begin
      @vm_resource_pool.create_with_parent(@parent)
      render :json => { :object => "vm_resource_pool", :success => true, 
                        :alert => "Virtual Machine Pool was successfully created." }
    rescue
      render :json => { :object => "vm_resource_pool", :success => false, 
                        :errors => @vm_resource_pool.errors.localize_error_messages.to_a}
    end    
  end

  def edit
    render :layout => 'popup'    
  end

  def update
    begin
      @vm_resource_pool.update_attributes!(params[:vm_resource_pool])
      render :json => { :object => "vm_resource_pool", :success => true, 
                        :alert => "Virtual Machine Pool was successfully modified." }
    rescue
      render :json => { :object => "vm_resource_pool", :success => false, 
                        :errors => @vm_resource_pool.errors.localize_error_messages.to_a}
    end
  end

  #FIXME: we need permissions checks. user must have permission. We also need to fail
  # for pools that aren't currently empty
  def delete
    vm_pool_ids_str = params[:vm_pool_ids]
    vm_pool_ids = vm_pool_ids_str.split(",").collect {|x| x.to_i}
    vm_pool_names = []
    begin
      VmResourcePool.transaction do
        pools = VmResourcePool.find(:all, :conditions => "id in (#{vm_pool_ids.join(', ')})")
        pools.each do |pool|
          vm_pool_names << pool.name
          pool.destroy
        end
      end
      render :json => { :object => "vm_resource_pool", :success => true, 
                        :alert => "Virtual Machine Pools #{vm_pool_names.join(', ')} were successfully deleted." }
    rescue
      render :json => { :object => "vm_resource_pool", :success => false, 
                        :alert => "Error in deleting Virtual Machine Pools."}
    end
  end

  def destroy
    if @vm_resource_pool.destroy
      alert="Virtual Machine Pool was successfully deleted."
      success=true
    else
      alert="Failed to delete virtual machine pool."
      success=false
    end
    render :json => { :object => "vm_resource_pool", :success => success, :alert => alert }
  end

  def vm_actions
    @action = params[:vm_action]
    @action_label = VmTask.action_label(@action)
    vms_str = params[:vm_ids]
    @vms = vms_str.split(",").collect {|x| Vm.find(x.to_i)}
    @success_list = []
    @failure_list = []
    begin
      @vm_resource_pool.transaction do 
        @vms.each do |vm|
          if vm.queue_action(@user, @action)
            @success_list << vm
            print vm.description, vm.id, "\n"
          else
            @failure_list << vm
          end
        end
      end
    rescue
      flash[:errmsg] = 'Error queueing VM actions.'
      @success_list = []
      @failure_list = []
    end
    render :layout => 'confirmation'    
  end

  protected
  def pre_new
    @vm_resource_pool = VmResourcePool.new
    @parent = Pool.find(params[:parent_id])
    @perm_obj = @parent
    @redir_controller = @perm_obj.get_controller
    @current_pool_id=@parent.id
  end
  def pre_create
    @vm_resource_pool = VmResourcePool.new(params[:vm_resource_pool])
    @parent = Pool.find(params[:parent_id])
    @perm_obj = @parent
    @redir_controller = @perm_obj.get_controller
    @current_pool_id=@parent.id
  end
  def pre_show
    @vm_resource_pool = VmResourcePool.find(params[:id])
    @perm_obj = @vm_resource_pool
    @current_pool_id=@vm_resource_pool.id
  end
  def pre_edit
    @vm_resource_pool = VmResourcePool.find(params[:id])
    @parent = @vm_resource_pool.parent
    @perm_obj = @vm_resource_pool.parent
    @redir_obj = @vm_resource_pool
    @current_pool_id=@vm_resource_pool.id
  end
  def pre_json
    pre_show
    show
  end
  def pre_vm_actions
    @vm_resource_pool = VmResourcePool.find(params[:id])
    @parent = @vm_resource_pool.parent
    @perm_obj = @vm_resource_pool
    @redir_obj = @vm_resource_pool
    authorize_user
  end

end
