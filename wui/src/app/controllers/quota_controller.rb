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

  def redirect_to_parent
    redirect_to :controller => @quota.pool.get_controller, :action => 'show', :id => @quota.pool
  end

  def show
    @quota = Quota.find(params[:id])
    set_perms(@quota.pool)

    unless @can_view
      flash[:notice] = 'You do not have permission to view this quota: redirecting to top level'
      redirect_to_parent
    end
                      
  end

  def new
  end

  def create
    if @quota.save
      flash[:notice] = 'Quota was successfully created.'
      redirect_to_parent
    else
      render :action => 'new'
    end
  end

  def edit
  end

  def update
    if @quota.update_attributes(params[:quota])
      flash[:notice] = 'Quota was successfully updated.'
      redirect_to_parent
    else
      render :action => 'edit'
    end
  end

  def destroy
    pool = @quota.pool
    unless @quota.destroy
      flash[:notice] = 'destroying quota failed '
    end
    if pool
      redirect_to :controller => pool.get_controller, :action => 'show', :id => pool
    else
      redirect_to :controller => 'dashboard', :action => 'list'
    end
  end

  protected
  def pre_new
    @quota = Quota.new( { :pool_id => params[:pool_id]})
    @perm_obj = @quota.pool
    @redir_controller = @perm_obj.get_controller
  end
  def pre_create
    @quota = Quota.new(params[:quota])
    @perm_obj = @quota.pool
    @redir_controller = @perm_obj.get_controller
  end
  def pre_show
    @quota = Quota.find(params[:id])
    @perm_obj = @quota
  end
  def pre_edit
    @quota = Quota.find(params[:id])
    @perm_obj = @quota.pool
    @redir_controller = @perm_obj.get_controller
  end

end
