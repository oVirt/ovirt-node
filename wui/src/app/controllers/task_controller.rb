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

class TaskController < ApplicationController
  # GETs should be safe (see http://www.w3.org/2001/tag/doc/whenToUseGet.html)
  verify :method => :post, :only => [ :destroy, :create, :update ],
         :redirect_to => { :action => :list }

  def show
    @task = Task.find(params[:id])
    set_perms(@task.vm.vm_library)
    unless @can_monitor
      flash[:notice] = 'You do not have permission to view this task: redirecting to top level'
      redirect_to :controller => 'library', :action => 'list'
    end

  end

  def set_perms(perm_obj)
    @user = get_login_user
    @is_admin = perm_obj.is_admin(@user)
    @can_monitor = perm_obj.can_monitor(@user)
    @can_delegate = perm_obj.can_delegate(@user)
  end

end
