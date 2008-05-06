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

class VmController < ApplicationController
  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :controller => 'dashboard' }

  before_filter :pre_vm_action, :only => [:vm_action, :cancel_queued_tasks]

  def show
    set_perms(@perm_obj)
    @actions = @vm.get_action_and_label_list
    unless @can_view
      flash[:notice] = 'You do not have permission to view this vm: redirecting to top level'
      redirect_to :controller => 'resources', :controller => 'dashboard'
    end
  end

  def new
  end

  def create
    if @vm.save
      @task = VmTask.new({ :user    => @user,
                         :vm_id   => @vm.id,
                         :action  => VmTask::ACTION_CREATE_VM,
                         :state   => Task::STATE_QUEUED})
      if @task.save
        flash[:notice] = 'Vm was successfully created.'
        start_now = params[:start_now]
        if (start_now)
          if @vm.get_action_list.include?(VmTask::ACTION_START_VM)
            @task = VmTask.new({ :user    => @user,
                               :vm_id   => @vm.id,
                               :action  => VmTask::ACTION_START_VM,
                               :state   => Task::STATE_QUEUED})
            if @task.save
              flash[:notice] = flash[:notice] + ' VM Start action queued.'
            else
              flash[:notice] = flash[:notice] + ' Error in inserting Start task.'
            end
          else
            flash[:notice] = flash[:notice] + ' Resources are not available to start VM now.'
          end
        end
      else
        flash[:notice] = 'Error in inserting task.'
      end
      redirect_to :controller => 'resources', :action => 'show', :id => @vm.vm_resource_pool.id
    else
      render :action => 'new'
    end
  end

  def edit
  end

  def update
    #needs restart if certain fields are changed (since those will only take effect the next startup)
    needs_restart = false
    unless @vm.get_pending_state == Vm::STATE_STOPPED
      Vm::NEEDS_RESTART_FIELDS.each do |field|
        unless @vm[field].to_s == params[:vm][field]
          needs_restart = true
          break
        end
      end
      current_storage_ids = @vm.storage_volume_ids.sort
      new_storage_ids = params[:vm][:storage_volume_ids]
      new_storage_ids = [] unless new_storage_ids
      new_storage_ids = new_storage_ids.sort.collect {|x| x.to_i }
      needs_restart = true unless current_storage_ids == new_storage_ids
    end
    params[:vm][:needs_restart] = 1 if needs_restart
    if @vm.update_attributes(params[:vm])
      flash[:notice] = 'Vm was successfully updated.'
      redirect_to :action => 'show', :id => @vm
    else
      render :action => 'edit'
    end
  end

  def destroy
    vm_resource_pool = @vm.vm_resource_pool_id
    if ((@vm.state == Vm::STATE_STOPPED and @vm.get_pending_state == Vm::STATE_STOPPED) or
        (@vm.state == Vm::STATE_PENDING and @vm.get_pending_state == Vm::STATE_PENDING))
      @vm.destroy
      if vm_resource_pool
        redirect_to :controller => 'resources', :action => 'show', :id => vm_resource_pool
      else
        redirect_to :controller => 'resources', :controller => 'dashboard'
      end
    else
      flash[:notice] = "Vm must be stopped to destroy it."
      redirect_to :controller => 'vm', :action => 'show', :id => params[:id]
    end
  end

  def vm_action
    if @vm.get_action_list.include?(params[:vm_action])
      @task = VmTask.new({ :user    => get_login_user,
                         :vm_id   => params[:id],
                         :action  => params[:vm_action],
                         :state   => Task::STATE_QUEUED})
      if @task.save
        flash[:notice] = "#{params[:vm_action]} was successfully queued."
      else
        flash[:notice] = "Error in inserting task for #{params[:vm_action]}."
      end
    else
      flash[:notice] = "#{params[:vm_action]} is an invalid action."
    end
    redirect_to :controller => 'vm', :action => 'show', :id => params[:id]
  end

  def cancel_queued_tasks
    @vm.get_queued_tasks.each { |task| task.cancel}
    flash[:notice] = "queued tasks canceled."
    redirect_to :controller => 'vm', :action => 'show', :id => params[:id]
  end

  protected
  def pre_new
    # if no vm_resource_pool is passed in, find (or auto-create) it based on hardware_pool_id
    unless params[:vm_resource_pool_id]
      unless params[:hardware_pool_id]
        flash[:notice] = "VM Resource Pool or Hardware Pool is required."
        redirect_to :controller => 'dashboard'
      end
      @hardware_pool = HardwarePool.find(params[:hardware_pool_id])
      @user = get_login_user
      vm_resource_pool = @hardware_pool.sub_vm_resource_pools.select {|pool| pool.name == @user}.first
      if vm_resource_pool
        params[:vm_resource_pool_id] = vm_resource_pool.id
      else
        @vm_resource_pool = VmResourcePool.new({:name => vm_resource_pool})
        @vm_resource_pool.tmp_parent = @hardware_pool
        @vm_resource_pool_name = @user
      end
    end

    # random MAC
    mac = [ 0x00, 0x16, 0x3e, rand(0x7f), rand(0xff), rand(0xff) ]
    # random uuid
    uuid = ["%02x" * 4, "%02x" * 2, "%02x" * 2, "%02x" * 2, "%02x" * 6].join("-") % 
      Array.new(16) {|x| rand(0xff) }
    newargs = { 
      :vm_resource_pool_id => params[:vm_resource_pool_id],
      :vnic_mac_addr => mac.collect {|x| "%02x" % x}.join(":"),
      :uuid => uuid
    }
    @vm = Vm.new( newargs )
    unless params[:vm_resource_pool_id]
      @vm.vm_resource_pool = @vm_resource_pool
    end
    @perm_obj = @vm.vm_resource_pool
    @redir_controller = 'resources'
    @current_pool_id=@perm_obj.id
  end
  def pre_create
    params[:vm][:state] = Vm::STATE_PENDING
    vm_resource_pool_name = params[:vm_resource_pool_name]
    hardware_pool_id = params[:hardware_pool_id]
    if vm_resource_pool_name and hardware_pool_id
      vm_resource_pool = VmResourcePool.new({:name => vm_resource_pool_name})
      vm_resource_pool.create_with_parent(hardware_pool_id)
      params[:vm][:vm_resource_pool_id] = vm_resource_pool.id
    end
    #set boot device to network for first boot (install)
    params[:vm][:boot_device] = Vm::BOOT_DEV_NETWORK unless params[:vm][:boot_device]
    @vm = Vm.new(params[:vm])
    @perm_obj = @vm.vm_resource_pool
    @redir_controller = 'resources'
    @current_pool_id=@perm_obj.id
  end
  def pre_show
    @vm = Vm.find(params[:id])
    @perm_obj = @vm.vm_resource_pool
    @current_pool_id=@perm_obj.id
  end
  def pre_edit
    @vm = Vm.find(params[:id])
    @perm_obj = @vm.vm_resource_pool
    @redir_obj = @vm
    @current_pool_id=@perm_obj.id
  end
  def pre_vm_action
    pre_edit
    authorize_user
  end
end
