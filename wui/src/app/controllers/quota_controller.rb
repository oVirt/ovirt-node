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

class QuotaController < ApplicationController
  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def set_perms
    @user = get_login_user
    if @quota.host_collection
      @Is_admin = @quota.host_collection.is_admin(@user)
      @can_monitor = @quota.host_collection.can_monitor(@user)
      @can_delegate = @quota.host_collection.can_delegate(@user)
    elsif @quota.vm_library
      @is_admin = @quota.vm_library.is_admin(@user)
      @can_monitor = @quota.vm_library.can_monitor(@user)
      @can_delegate = @quota.vm_library.can_delegate(@user)
    else
      @is_admin = false
      @can_monitor = false
      @can_delegate = false
    end
  end

  def redirect_to_parent
    if @quota.host_collection
      redirect_to :controller => 'pool', :action => 'show', :id => @quota.host_collection
    elsif @quota.vm_library
      redirect_to :controller => 'library', :action => 'show', :id => @quota.vm_library
    else
      redirect_to :controller => 'library', :action => 'list'
    end
  end

  def show
    @quota = Quota.find(params[:id])
    set_perms

    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this quota: redirecting to top level'
      redirect_to_parent
    end
                      
  end

  def new
    @quota = Quota.new( { :host_collection_id => params[:host_collection_id],
                          :vm_library_id => params[:vm_library_id]})
    set_perms
    unless @is_admin
      flash[:notice] = 'You do not have permission to create a quota '
      redirect_to_parent
    end
  end

  def create
    @quota = Quota.new(params[:quota])
    set_perms
    unless @is_admin
      flash[:notice] = 'You do not have permission to create a quota '
      redirect_to_parent
    else
      if @quota.save
        flash[:notice] = 'Quota was successfully created.'
        redirect_to_parent
      else
        render :action => 'new'
      end
    end
  end

  def edit
    @quota = Quota.find(params[:id])
    set_perms
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this quota '
      redirect_to_parent
    end
  end

  def update
    @quota = Quota.find(params[:id])
    set_perms
    unless @is_admin
      flash[:notice] = 'You do not have permission to edit this quota '
      redirect_to_parent
    else
      if @quota.update_attributes(params[:quota])
        flash[:notice] = 'Quota was successfully updated.'
        redirect_to_parent
      else
        render :action => 'edit'
      end
    end
  end

  def destroy
    @quota = Quota.find(params[:id])
    set_perms
    unless @is_admin
      flash[:notice] = 'You do not have permission to delete this quota '
      redirect_to_parent
    else
      pool_id = @quota.host_collection_id
      vm_library_id = @quota.vm_library_id
      unless @quota.destroy
        flash[:notice] = 'destroying quota failed '
      end
      if pool_id
        redirect_to :controller => 'pool', :action => 'show', :id => pool_id
      elsif vm_library_id
        redirect_to :controller => 'library', :action => 'show', :id => vm_library_id
      else
        redirect_to :controller => 'library', :action => 'list'
      end
    end
  end

end
