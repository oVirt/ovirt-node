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

class PermissionController < ApplicationController
  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def redirect_to_parent
    redirect_to :controller => @permission.pool.get_controller, :action => 'show', :id => @permission.pool_id
  end

  def show
    @permission = Permission.find(params[:id])
    set_perms(@permission.pool)
    # admin permission required to view permissions
    unless @is_admin
      flash[:notice] = 'You do not have permission to view this permission record'
      redirect_to_parent
    end
  end

  def new
    @permission = Permission.new( { :pool_id => params[:pool_id]})
    @perms = @permission.pool.permissions
    set_perms(@permission.pool)
    # admin permission required to view permissions
    unless @can_delegate
      flash[:notice] = 'You do not have permission to create this permission record'
      redirect_to_parent
    end
  end

  def create
    @permission = Permission.new(params[:permission])
    set_perms(@permission.pool)
    unless @can_delegate
      flash[:notice] = 'You do not have permission to create this permission record'
      redirect_to_parent
    else
      if @permission.save
        flash[:notice] = 'Permission was successfully created.'
        redirect_to_parent
      else
        render :action => 'new'
      end
    end
  end

  def destroy
    @permission = Permission.find(params[:id])
    set_perms(@permission.pool)
    unless @can_delegate
      flash[:notice] = 'You do not have permission to delete this permission record'
      redirect_to_parent
    else
      pool =  @permission.pool
      if @permission.destroy
        if pool
          flash[:notice] = "<strong>#{@permission.user}</strong> permissions were revoked successfully"
          redirect_to :controller => pool.get_controller, :action => 'show', :id => pool
        else
          redirect_to :controller => 'dashboard', :action => 'list'
        end
      end
    end
  end
end
