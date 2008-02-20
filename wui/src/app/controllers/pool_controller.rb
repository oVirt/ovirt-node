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

class PoolController < AbstractPoolController
  def index
    list
    render :action => 'list'
  end

  #FIXME: this method isn't really needed anymore
  def list
    @user = get_login_user
    @default_pool = MotorPool.find(:first)
    set_perms(@default_pool)
    @organizational_pools = OrganizationalPool.list_for_user(@user)
    @hosts = Set.new
    @storage_pools = Set.new
    @organizational_pools.each do |pool|
      @hosts += pool.hosts
      @storage_pools += pool.storage_pools
    end
    @hosts = @hosts.entries
    @storage_pools = @storage_pools.entries
  end


  def new
    @organizational_pools = OrganizationalPool.find(:all)
  end

  def create
    if @organizational_pool.save
      flash[:notice] = 'HardwarePool was successfully created.'
      redirect_to :action => 'show', :id => @organizational_pool
    else
      render :action => 'new'
    end
  end

  def edit
    @other_pools = OrganizationalPool.find(:all, :conditions => [ "id != ?", params[:id] ])
  end

  def update
    if @organizational_pool.update_attributes(params[:organizational_pool])
      flash[:notice] = 'Hardware Pool was successfully updated.'
      redirect_to :action => 'show', :id => @organizational_pool
    else
      render :action => 'edit'
    end
  end

  # pool must be have no subpools empty to delete
  def destroy
    superpool = @organizational_pool.superpool
    if not(superpool)
      flash[:notice] = "You can't delete the top level HW pool."
      redirect_to :action => 'show', :id => @organizational_pool
    elsif not(@organizational_pool.network_maps.empty?)
      flash[:notice] = "You can't delete a pool without first deleting its Network Maps."
      redirect_to :action => 'show', :id => @organizational_pool
    else
      @organizational_pool.move_contents_and_destroy
      redirect_to :controller => "dashboard"
    end
  end

  private
  #filter methods
  def pre_new
    @organizational_pool = OrganizationalPool.new( { :superpool_id => params[:superpool_id] } )
    @perm_obj = @organizational_pool.superpool
  end
  def pre_create
    @organizational_pool = OrganizationalPool.create(params[:organizational_pool])
    @perm_obj = @organizational_pool.superpool
  end
  def pre_edit
    @organizational_pool = OrganizationalPool.find(params[:id])
    @perm_obj = @organizational_pool
  end
  def pre_show
    @organizational_pool = OrganizationalPool.find(params[:id])
    @perm_obj = @organizational_pool
  end
end
