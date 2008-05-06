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

class NicController < ApplicationController
  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :controller => 'dashboard' }

  def show
    set_perms(@perm_obj)
    unless @can_view
      flash[:notice] = 'You do not have permission to view this NIC: redirecting to top level'
      redirect_to :controller => 'pool', :action => 'list'
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

  private
  #filter methods
  def pre_new
    flash[:notice] = 'Network Interfaces may not be edited via the web UI'
    redirect_to :controller => 'host', :action => 'show', :id => params[:host_id]
  end
  def pre_create
    flash[:notice] = 'Network Interfaces may not be edited via the web UI'
    redirect_to :controller => 'dashboard'
  end
  def pre_edit
    @nic = Nic.find(params[:id])
    flash[:notice] = 'Network Interfaces may not be edited via the web UI'
    redirect_to :action=> 'show', :id => @nic
  end
  def pre_show
    @nic = Nic.find(params[:id])
    @perm_obj = @nic.host.hardware_pool
  end

end
