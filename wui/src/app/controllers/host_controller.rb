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

class HostController < ApplicationController
  def index
    list
    render :action => 'list'
  end

  before_filter :pre_action, :only => [:host_action, :enable, :disable, :clear_vms]

  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def show
    set_perms(@perm_obj)
    unless @can_view
      flash[:notice] = 'You do not have permission to view this host: redirecting to top level'
      #perm errors for ajax should be done differently
      redirect_to :controller => 'dashboard', :action => 'list'
    end
    render :layout => 'selection'    
  end

  # retrieves data used by snapshot graphs
  def snapshot_graph
  end

  def addhost
    @hardware_pool = Pool.find(params[:hardware_pool_id])
    render :layout => 'popup'    
  end

  def new
  end

  def create
  end

  def edit
  end

  def update
  end

  def destroy
  end

  def host_action
    action = params[:action_type]
    if["disable", "enable", "clear_vms"].include?(action)
      self.send(action)
    else
      @json_hash[:alert]="invalid operation #{action}"
      @json_hash[:success]=false
      render :json => @json_hash
    end
  end

  def disable
    set_disabled(1)
  end
  def enable
    set_disabled(0)
  end

  def set_disabled(value)
    operation = value == 1 ? "diabled" : "enabled"
    begin
      @host.is_disabled = value
      @host.save!
      @json_hash[:alert]="Host was successfully #{operation}"
      @json_hash[:success]=true
    rescue
      @json_hash[:alert]="Error setting host to #{operation}"
      @json_hash[:success]=false
    end
    render :json => @json_hash
  end

  def clear_vms
    begin
      Host.transaction do
        task = HostTask.new({ :user    => get_login_user,
                              :host_id   => @host.id,
                              :action  => HostTask::ACTION_CLEAR_VMS,
                              :state   => Task::STATE_QUEUED})
        task.save!
        @host.is_disabled = true
        @host.save!
      end
      @json_hash[:alert]="Clear VMs action was successfully queued."
      @json_hash[:success]=true
    rescue
      @json_hash[:alert]="Error in queueing Clear VMs action."
      @json_hash[:success]=false
    end
    render :json => @json_hash
  end


  private
  #filter methods
  def pre_new
    flash[:notice] = 'Hosts may not be edited via the web UI'
    redirect_to :controller => 'hardware', :action => 'show', :id => params[:hardware_pool_id]
  end
  def pre_create
    flash[:notice] = 'Hosts may not be edited via the web UI'
    redirect_to :controller => 'dashboard'
  end
  def pre_edit
    @host = Host.find(params[:id])
    flash[:notice] = 'Hosts may not be edited via the web UI'
    redirect_to :action=> 'show', :id => @host
  end
  def pre_action
    @host = Host.find(params[:id])
    @perm_obj = @host.hardware_pool
    @json_hash = { :object => :host }
    authorize_admin
  end
  def pre_show
    @host = Host.find(params[:id])
    @perm_obj = @host.hardware_pool
    @current_pool_id=@perm_obj.id
  end


end
