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
  verify :method => :post, :only => [ :destroy, :create ],
         :redirect_to => { :controller => 'dashboard' }

  def redirect_to_parent
    redirect_to :controller => @permission.pool.get_controller, :action => 'show', :id => @permission.pool_id
  end

  def show
    @permission = Permission.find(params[:id])
    set_perms(@permission.pool)
    # admin permission required to view permissions
    unless @can_view_perms
      flash[:notice] = 'You do not have permission to view this permission record'
      redirect_to_parent
    end
  end

  def new
    @permission = Permission.new( { :pool_id => params[:pool_id]})
    @perms = @permission.pool.permissions
    @pool = Pool.find(params[:pool_id])
    filter = @pool.permissions.collect{ |permission| permission.uid }
    @users = Account.names(filter)
    set_perms(@permission.pool)
    # admin permission required to view permissions
    unless @can_set_perms
      flash[:notice] = 'You do not have permission to create this permission record'
      redirect_to_parent
    end
    render :layout => 'popup'    
  end

  def create
    @permission = Permission.new(params[:permission])
    set_perms(@permission.pool)
    unless @can_set_perms
      # FIXME: need to handle proper error messages w/ ajax
      flash[:notice] = 'You do not have permission to create this permission record'
      redirect_to_parent
    else
      begin
        @permission.save_with_new_children
        render :json => { :object => "permission", :success => true,
                :alert => "created User Permissions for  #{@permission.uid}." }
      rescue
        render :json => { :object => "permission", :success => false,
                          :alert => "Error adding user: #{$!}" }
      end
    end
  end

  #FIXME: we need permissions checks. user must have permission. We also need to fail
  # for pools that aren't currently empty
  def update_roles
    role = params[:user_role]
    permission_ids_str = params[:permission_ids]
    permission_ids = permission_ids_str.split(",").collect {|x| x.to_i}

    begin
      Permission.transaction do
        permissions = Permission.find(:all, :conditions => "id in (#{permission_ids.join(', ')})")
        permissions.each do |permission|
          permission.update_role(role) if permission.is_primary?
        end
      end
      render :json => { :object => "permission", :success => true, 
        :alert => "User roles were successfully updated." }
    rescue
      render :json => { :object => "permission", :success => false, 
        :alert => "Error updating user roles: #{$!}" }
    end
  end

  #FIXME: we need permissions checks. user must have permission. We also need to fail
  # for pools that aren't currently empty
  def delete
    permission_ids_str = params[:permission_ids]
    permission_ids = permission_ids_str.split(",").collect {|x| x.to_i}

    begin
      Permission.transaction do
        permissions = Permission.find(:all, :conditions => "id in (#{permission_ids.join(', ')})")
        permissions.each do |permission|
          permission.destroy if permission.is_primary?
        end
      end
      render :json => { :object => "permission", :success => true, 
        :alert => "User roles were successfully deleted." }
    rescue
      render :json => { :object => "permission", :success => false, 
        :alert => "Error deleting user roles." }
    end
  end

  def destroy
    @permission = Permission.find(params[:id])
    set_perms(@permission.pool)
    unless @can_set_perms
      flash[:notice] = 'You do not have permission to delete this permission record'
      redirect_to_parent
    else
      pool =  @permission.pool
      if @permission.destroy
        if pool
          flash[:notice] = "<strong>#{@permission.uid}</strong> permissions were revoked successfully"
          redirect_to :controller => pool.get_controller, :action => 'show', :id => pool.id
        else
          redirect_to :controller => 'dashboard', :action => 'list'
        end
      end
    end
  end
end
