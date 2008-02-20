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

class LibraryController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def list
    @user = get_login_user
    @vm_libraries = VmLibrary.list_for_user(@user)
    @vms = Set.new
    @vm_libraries.each { |vm_library| @vms += vm_library.vms}
    @vms = @vms.entries
    @action_values = [["Suspend", VmTask::ACTION_SUSPEND_VM],
                      ["Resume", VmTask::ACTION_RESUME_VM],
                      ["Save", VmTask::ACTION_SAVE_VM],
                      ["Restore", VmTask::ACTION_RESTORE_VM]]
  end

  def show
    set_perms(@perm_obj)
    @is_hwpool_admin = @vm_library.host_collection.is_admin(@user)
    @action_values = [["Suspend", VmTask::ACTION_SUSPEND_VM],
                      ["Resume", VmTask::ACTION_RESUME_VM],
                      ["Save", VmTask::ACTION_SAVE_VM],
                      ["Restore", VmTask::ACTION_RESTORE_VM]]
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this VM library: redirecting to top level'
      redirect_to :action => 'list'
    end
  end

  def new
  end

  def create
    if @vm_library.save
      flash[:notice] = 'VM Library was successfully created.'
      redirect_to :controller => 'collection', :action => 'show', :id => @vm_library.host_collection
    else
      render :action => 'new'
    end
  end

  def edit
  end

  def update
    if @vm_library.update_attributes(params[:vm_library])
      flash[:notice] = 'VM Library was successfully updated.'
      redirect_to :action => 'show', :id => @vm_library
    else
      render :action => 'edit'
    end
  end

  def destroy
    host_collection_id = @vm_library.host_collection_id
    @vm_library.destroy
    redirect_to :controller => 'collection', :action => 'show', :id => host_collection_id
  end

  def vm_actions
    @vm_library = VmLibrary.find(params[:vm_library_id])
    set_perms(@vm_library)
    unless @is_admin
      flash[:notice] = 'You do not have permission to perform VM actions for this VM library '
      redirect_to :action => 'show', :id => @vm_library
    else
      params[:vm_actions].each do |name, param|
        print "param: ", name, ", ", param, "\n"
      end
      if params[:vm_actions][:vms]
        vms = params[:vm_actions][:vms]
        if params[:vm_actions][VmTask::ACTION_START_VM]
          flash[:notice] = "Starting Machines #{vms.join(',')}."
        elsif params[:vm_actions][VmTask::ACTION_SHUTDOWN_VM]
          flash[:notice] = "Stopping Machines #{vms.join(',')}."
        elsif params[:vm_actions][:other_actions]
          case params[:vm_actions][:other_actions]
          when VmTask::ACTION_SHUTDOWN_VM then flash[:notice] = "Stopping Machines #{vms.join(',')}."
          when VmTask::ACTION_START_VM then flash[:notice] = "Starting Machines #{vms.join(',')}."
          when VmTask::ACTION_SUSPEND_VM then flash[:notice] = "Suspending Machines #{vms.join(',')}."
          when VmTask::ACTION_RESUME_VM then flash[:notice] = "Resuming Machines #{vms.join(',')}."
          when VmTask::ACTION_SAVE_VM then flash[:notice] = "Saving Machines #{vms.join(',')}."
          when VmTask::ACTION_RESTORE_VM then flash[:notice] = "Restoring Machines #{vms.join(',')}."
          when "destroy" then flash[:notice] = "Destroying Machines #{vms.join(',')}."
          else
            flash[:notice] = 'No Action Chosen.'
          end
        else
          flash[:notice] = 'No Action Chosen.'
        end
      else
        flash[:notice] = 'No Virtual Machines Selected.'
      end
      if params[:vm_actions][:vm_library_id]
        redirect_to :action => 'show', :id => params[:vm_actions][:vm_library_id]
      else
        redirect_to :action => 'list'
      end
    end
  end

  protected
  def pre_new
    @vm_library = VmLibrary.new( { :host_collection_id => params[:host_collection_id] } )
    @perm_obj = @vm_library.host_collection
    @redir_controller = 'collection'
  end
  def pre_create
    @vm_library = VmLibrary.new(params[:vm_library])
    @perm_obj = @vm_library.host_collection
    @redir_controller = 'collection'
  end
  def pre_show
    @vm_library = VmLibrary.find(params[:id])
    @perm_obj = @vm_library
  end
  def pre_edit
    @vm_library = VmLibrary.find(params[:id])
    @perm_obj = @vm_library.host_collection
    @redir_obj = @vm_library
  end

end
