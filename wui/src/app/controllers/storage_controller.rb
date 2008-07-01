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

class StorageController < ApplicationController

  before_filter :pre_pool_admin, :only => [:refresh]
  before_filter :pre_new2, :only => [:new2]
  before_filter :pre_json, :only => [:storage_volumes_json]

  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @attach_to_pool=params[:attach_to_pool]
    if @attach_to_pool
      pool = HardwarePool.find(@attach_to_pool)
      set_perms(pool)
      unless @can_view
        flash[:notice] = 'You do not have permission to view this storage pool list: redirecting to top level'
        redirect_to :controller => 'dashboard'
      else
        conditions = "hardware_pool_id is null"
        conditions += " or hardware_pool_id=#{pool.parent_id}" if pool.parent
        @storage_pools = StoragePool.find(:all, :conditions => conditions)
      end
    else
      #no permissions here yet -- do we disable raw volume list
      @storage_pools = StoragePool.find(:all)
    end
  end

  def show
    @storage_pool = StoragePool.find(params[:id])
    set_perms(@storage_pool.hardware_pool)
    unless @can_view
      flash[:notice] = 'You do not have permission to view this storage pool: redirecting to top level'
      redirect_to :controller => 'dashboard'
    end
    render :layout => 'selection'    
  end

  def storage_volumes_json
    @storage_pool = StoragePool.find(params[:id])
    set_perms(@storage_pool.hardware_pool)
    unless @can_view
      flash[:notice] = 'You do not have permission to view this storage pool: redirecting to top level'
      redirect_to :controller => 'dashboard'
    end
    json_list(@storage_pool.storage_volumes, 
              [:display_name, :size_in_gb, :get_type_label])
  end
  def show_volume
    @storage_volume = StorageVolume.find(params[:id])
    set_perms(@storage_volume.storage_pool.hardware_pool)
    unless @can_view
      flash[:notice] = 'You do not have permission to view this storage volume: redirecting to top level'
      redirect_to :controller => 'dashboard'
    end
  end

  def new
  end

  def new2
    @storage_pools = @storage_pool.hardware_pool.storage_volumes
    render :layout => false
  end

  def insert_refresh_task
    @task = StorageTask.new({ :user            => @user,
                              :storage_pool_id => @storage_pool.id,
                              :action          => StorageTask::ACTION_REFRESH_POOL,
                              :state           => Task::STATE_QUEUED})
    @task.save!
  end

  def refresh
    begin
      insert_refresh_task
      storage_url = url_for(:controller => "storage", :action => "show", :id => @storage_pool)
      flash[:notice] = 'Storage pool refresh was successfully scheduled.'
    rescue
      flash[:notice] = 'Error scheduling Storage pool refresh.'
    end
    redirect_to :action => 'show', :id => @storage_pool.id
  end

  def create
    begin
      StoragePool.transaction do
        @storage_pool.save!
        insert_refresh_task
      end
      render :json => { :object => "storage_pool", :success => true, 
                        :alert => "Storage Pool was successfully created." }
    rescue
      # FIXME: need to distinguish pool vs. task save errors (but should mostly be pool)
      render :json => { :object => "storage_pool", :success => false, 
                        :errors => @storage_pool.errors.localize_error_messages.to_a  }
    end
  end

  def edit
    render :layout => 'popup'    
  end

  def update
    begin
      StoragePool.transaction do
        @storage_pool.update_attributes!(params[:storage_pool])
        insert_refresh_task
      end
      render :json => { :object => "storage_pool", :success => true, 
                        :alert => "Storage Pool was successfully modified." }
    rescue
      # FIXME: need to distinguish pool vs. task save errors (but should mostly be pool)
      render :json => { :object => "storage_pool", :success => false, 
                        :errors => @storage_pool.errors.localize_error_messages.to_a  }
    end
  end

  def add_internal
    @hardware_pool = HardwarePool.find(params[:hardware_pool_id])
    @perm_obj = @hardware_pool
    @redir_controller = @perm_obj.get_controller
    authorize_admin
    @storage_pools = @hardware_pool.storage_volumes
    @storage_types = StoragePool::STORAGE_TYPES.keys
  end

  def addstorage
    add_internal
    render :layout => 'popup'    
  end

  def add
    add_internal
    render :layout => false
  end

  def new
    add_internal
    render :layout => false
  end

  #FIXME: we need permissions checks. user must have permission on src pool
  # in addition to the current pool (which is checked). We also need to fail
  # for storage that aren't currently empty
  def delete_pools
    storage_pool_ids_str = params[:storage_pool_ids]
    storage_pool_ids = storage_pool_ids_str.split(",").collect {|x| x.to_i}

    begin
      StoragePool.transaction do
        storage = StoragePool.find(:all, :conditions => "id in (#{storage_pool_ids.join(', ')})")
        storage.each do |storage_pool|
          storage_pool.destroy
        end
      end
      render :json => { :object => "storage_pool", :success => true, 
        :alert => "Storage Pools were successfully deleted." }
    rescue
      render :json => { :object => "storage_pool", :success => true, 
        :alert => "Error deleting storage pools." }
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

  def destroy
    pool = @storage_pool.hardware_pool
    if @storage_pool.destroy
      alert="Storage Pool was successfully deleted."
      success=true
    else
      alert="Failed to delete storage pool."
      success=false
    end
    render :json => { :object => "storage_pool", :success => success, :alert => alert }
  end

  def pre_new
    @hardware_pool = HardwarePool.find(params[:hardware_pool_id])
    @perm_obj = @hardware_pool
    @redir_controller = @perm_obj.get_controller
  end

  def pre_new2
    new_params = { :hardware_pool_id => params[:hardware_pool_id]}
    if (params[:storage_type] == "iSCSI")
      new_params[:port] = 3260
    end
    @storage_pool = StoragePool.factory(params[:storage_type], new_params)
    @perm_obj = @storage_pool.hardware_pool
    @redir_controller = @storage_pool.hardware_pool.get_controller
    authorize_admin
  end
  def pre_create
    @storage_pool = StoragePool.factory(params[:storage_type], params[:storage_pool])
    @perm_obj = @storage_pool.hardware_pool
    @redir_controller = @storage_pool.hardware_pool.get_controller
  end
  def pre_edit
    @storage_pool = StoragePool.find(params[:id])
    @perm_obj = @storage_pool.hardware_pool
    @redir_obj = @storage_pool
  end
  def pre_json
    pre_show
  end
  def pre_pool_admin
    pre_edit
    authorize_admin
  end

end
