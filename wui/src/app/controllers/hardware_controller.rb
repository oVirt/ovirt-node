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

  #before_filter :pre_json, :only => [:json]

  def show
    set_perms(@perm_obj)
    unless @can_view
      flash[:notice] = 'You do not have permission to view this hardware pool: redirecting to top level'
      redirect_to :controller => "dashboard"
    end
  end
  
  def json
    id = params[:id]
    if id
      @pool = HardwarePool.find(id)
      set_perms(@pool)
      unless @can_view
        flash[:notice] = 'You do not have permission to view this hardware pool: redirecting to top level'
        redirect_to :controller => "dashboard"
        return
      end
    end
    if @pool
      pools = @pool.children
      open_list = []
    else
      pools = Pool.list_for_user(get_login_user,Permission::PRIV_VIEW)
      current_id = params[:current_id]
      if current_id
        current_pool = Pool.find(current_id)
        open_list = current_pool.self_and_ancestors
      else
        open_list = []
      end
    end
    render :json => pool_hash(pools, open_list).to_json
  end
  def pool_hash(pools, open_list)
    pools.collect do |pool|
      hash = {}
      hash[:id] = pool.id
      hash[:type] = pool[:type]
      hash[:text] = pool.name
      hash[:name] = pool.name
      hash[:hasChildren] = pool.hasChildren
      found = false
      open_list.each do |open_pool|
        if pool.id == open_pool.id
          new_open_list = open_list[(open_list.index(open_pool)+1)..-1]
          unless new_open_list.empty?
            hash[:children] = pool_hash(pool.children, new_open_list)
          end
          break
        end
      end
      hash
    end
  end

  def show_vms
    show
  end

  def show_users
    show
  end

  def show_hosts
    show
  end

  def show_storage
    show
  end

  def new
    @pools = @pool.self_and_like_siblings
  end

  def create
    if @pool.create_with_parent(@parent)
      flash[:notice] = 'Hardware Pool successfully created'
      redirect_to  :action => 'show', :id => @pool
    else
      render :action => "new"
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
  end
  def pre_json
    pre_show
  end
end
