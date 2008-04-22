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

  def list
    @attach_to_pool=params[:attach_to_pool]
    if @attach_to_pool
      pool = HardwarePool.find(@attach_to_pool)
      set_perms(pool)
      unless @can_monitor
        flash[:notice] = 'You do not have permission to view this host list: redirecting to top level'
        redirect_to :controller => 'dashboard', :action => 'list'
      else
        conditions = "hardware_pool_id is null"
        conditions += " or hardware_pool_id=#{pool.parent_id}" if pool.parent
        @hosts = Host.find(:all, :conditions => conditions)
      end
    else
      # no permissions here yet -- do we disable raw host list?
      @hosts = Host.find(:all)
    end
  end

  def show
    set_perms(@perm_obj)
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this host: redirecting to top level'
      redirect_to :controller => 'dashboard', :action => 'list'
    end
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
    @host = Host.find(params[:id])
    set_perms(@host.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this host'
      redirect_to :action => 'show', :id => @host
    else
      @host.is_disabled = 1
      if @host.save
        flash[:notice] = '<a class="show" href="%s">%s</a> was disabled.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
      else
        flash[:notice] = 'Disable failed for <a class="show" href="%s">%s</a>.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
      end
      redirect_to :action => 'show', :id => @host
    end
  end

  def enable
    @host = Host.find(params[:id])
    set_perms(@host.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this host'
      redirect_to :action => 'show', :id => @host
    else
      @host.is_disabled = 0
      if @host.save
        flash[:notice] = '<a class="show" href="%s">%s</a> was enabled.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
      else
        flash[:notice] = 'Enable failed for <a class="show" href="%s">%s</a>.' % [ url_for(:controller => "host", :action => "show", :id => @host), @host.hostname ]
      end
      redirect_to :action => 'show', :id => @host
    end
  end

  def attach_to_pool
    @host = Host.find(params[:id])
    set_perms(@host.hardware_pool)
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this host'
      redirect_to :action => 'show', :id => @host
    else
      pool = HardwarePool.find(params[:hardware_pool_id])
      host_url = url_for(:controller => "host", :action => "show", :id => @host)
      pool_url = url_for(:controller => pool.get_controller, :action => "show", :id => pool)
      @host.hardware_pool_id = pool.id
      if @host.save
        flash[:notice] = '<a class="show" href="%s">%s</a> is attached to <a href="%s">%s</a>.' %  [ host_url ,@host.hostname, pool_url, pool.name ]
        redirect_to :controller => pool.get_controller, :action => 'show', :id => pool
      else
        flash[:notice] = 'Problem attaching <a class="show" href="%s">%s</a> to <a href="%s">%s</a>.' %  [ host_url ,@host.hostname, host_url, host.hostname ]
        redirect_to :controller => pool.get_controller, :action => 'show', :id => pool
      end
    end
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
  end


end
