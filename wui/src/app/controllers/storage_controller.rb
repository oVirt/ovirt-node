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

  before_filter :pre_pool_admin, :only => [:attach_to_pool, :remove_from_pool]

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
        flash[:notice] = 'You do not have permission to view this storage pool list: redirecting to top level'
        redirect_to :controller => 'dashboard'
      else
        conditions = "hardware_pool_id is null"
        conditions += " or hardware_pool_id=#{pool.superpool_id}" if pool.superpool
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
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this storage pool: redirecting to top level'
      redirect_to :controller => 'dashboard'
    end
  end

  def show_volume
    @storage_volume = StorageVolume.find(params[:id])
    set_perms(@storage_volume.storage_pool.hardware_pool)
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this storage volume: redirecting to top level'
      redirect_to :controller => 'dashboard'
    end
  end

  def new
    @storage_pools = @storage_pool.hardware_pool.storage_volumes
  end

  def create
    if @storage_pool.save
      storage_url = url_for(:controller => "storage", :action => "show", :id => @storage_pool)
      flash[:notice] = '<a class="show" href="%s">%s</a> was successfully created.' % [ storage_url ,@storage_pool.ip_addr]
      redirect_to :controller => @storage_pool.hardware_pool.get_controller, :action => 'show', :id => @storage_pool.hardware_pool_id
    else
      render :action => 'new'
    end
  end

  def edit
  end

  def update
    if @storage_pool.update_attributes(params[:storage_pool])
      storage_url = url_for(:controller => "storage", :action => "show", :id => @storage_pool)
      flash[:notice] = '<a class="show" href="%s">%s</a> was successfully updated.' % [ storage_url ,@storage_pool.ip_addr]
      redirect_to :action => 'show', :id => @storage_pool
    else
      render :action => 'edit'
    end
  end

  def destroy
    pool = @storage_pool.hardware_pool
    @storage_pool.destroy
    redirect_to :controller => pool.get_controller, :action => 'show', :id => pool
  end

  def attach_to_pool
    pool = HardwarePool.find(params[:hardware_pool_id])
    storage_url = url_for(:controller => "storage", :action => "show", :id => @storage_pool)
    pool_url = url_for(:controller => pool.get_controller, :action => "show", :id => pool)
    @storage_pool.hardware_pool_id = pool.id
    if @storage_pool.save
      flash[:notice] = '<a class="show" href="%s">%s</a> is attached to <a href="%s">%s</a>.' %  [ storage_url ,@storage_pool.ip_addr, pool_url, pool.name ]
      redirect_to :controller => pool.get_controller, :action => 'show', :id => pool
    else
      flash[:notice] = 'Problem attaching <a class="show" href="%s">%s</a> to <a href="%s">%s</a>.' %  [ storage_url ,@storage_pool.ip_addr, host_url, host.hostname ]
      redirect_to :controller => pool.get_controller, :action => 'show', :id => pool
    end
  end

  def remove_from_pool
    pool = HardwarePool.find(params[:hardware_pool_id])
    storage_url = url_for(:controller => "storage", :action => "show", :id => @storage_pool)
    pool_url = url_for(:controller => pool.get_controller, :action => "show", :id => pool)
    if @storage_pool.hardware_pools.include?(pool)
      if @storage_pool.hardware_pools.delete(pool)
        flash[:notice] = '<a class="show" href="%s">%s</a> is removed from <a href="%s">%s</a>.' %[ storage_url ,@storage_pool.ip_addr, host_url, host.hostname ]
        redirect_to :controller => pool.get_controller, :action => 'show', :id => host
      else
        flash[:notice] = 'Problem attaching <a class="show" href="%s">%s</a> to <a href="%s">%s</a>.' % [ storage_url ,@storage_pool.ip_addr, pool_url, pool.name ]
        redirect_to :controller => pool.get_controller, :action => 'show', :id => host
      end
    else
      flash[:notice] = '<a class="show" href="%s">%s</a> is not attached to <a href="%s">%s</a>.' % [ storage_url ,@storage_pool.ip_addr, pool_url, pool.name ]
      redirect_to :controller => pool.get_controller, :action => 'show', :id => host
    end
  end

  def pre_new
    @storage_pool = StoragePool.new({ :hardware_pool_id => params[:hardware_pool_id],
                                      :port => 3260})
    @perm_obj = @storage_pool.hardware_pool
    @redir_controller = @storage_pool.hardware_pool.get_controller
  end
  def pre_create
    @storage_pool = StoragePool.new(params[:storage_pool])
    @perm_obj = @storage_pool.hardware_pool
    @redir_controller = @storage_pool.hardware_pool.get_controller
  end
  def pre_edit
    @storage_pool = StoragePool.find(params[:id])
    @perm_obj = @storage_pool.hardware_pool
    @redir_obj = @storage_pool
  end
  def pre_pool_admin
    pre_edit
    authorize_admin
  end

end
