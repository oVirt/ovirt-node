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

  def disable
    set_disabled(1)
  end
  def enable
    set_disabled(0)
  end

  def set_disabled(value)
    operation = value == 1 ? "diabled" : "enabled"
    @host = Host.find(params[:id])
    set_perms(@host.hardware_pool)
    unless @can_modify
      alert= 'You do not have permission to edit this host'
      success=false
    else
      begin
        @host.is_disabled = value
        @host.save
        alert="Host was successfully #{operation}"
        success=true
      rescue
        alert="Error setting host to #{operation}"
        success=false
      end
    end
    render :json => { :object => "host", :success => success, :alert => alert }
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
  def pre_show
    @host = Host.find(params[:id])
    @perm_obj = @host.hardware_pool
    @current_pool_id=@perm_obj.id
  end


end
