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

# Filters added to this controller apply to all controllers in the application.
# Likewise, all the methods added will be available for all controllers.

class ApplicationController < ActionController::Base
  # Pick a unique cookie name to distinguish our session data from others'
  session :session_key => '_ovirt_session_id'
  init_gettext "ovirt"
  layout 'redux'

  before_filter :pre_new, :only => [:new]
  before_filter :pre_create, :only => [:create]
  before_filter :pre_edit, :only => [:edit, :update, :destroy]
  before_filter :pre_show, :only => [:show, :show_vms, :show_users, 
                                     :show_hosts, :show_storage]
  before_filter :authorize_admin, :only => [:new, :create, :edit, :update, :destroy]

  def get_login_user
    user_from_principal(request.env["HTTP_X_FORWARDED_USER"])
  end
  
  def user_from_principal(principal)
    principal.split('@')[0]
  end

  def set_perms(hwpool)
    @user = get_login_user
    @can_view = hwpool.can_view(@user)
    @can_control_vms = hwpool.can_control_vms(@user)
    @can_modify = hwpool.can_modify(@user)
    @can_view_perms = hwpool.can_view_perms(@user)
    @can_set_perms = hwpool.can_set_perms(@user)
  end

  protected
  # permissions checking

  def pre_new
  end
  def pre_create
  end
  def pre_edit
  end
  def pre_show
  end

  def authorize_user
    authorize_action(false)
  end
  def authorize_admin
    authorize_action(true)
  end
  def authorize_action(is_modify_action)
    if @perm_obj
      set_perms(@perm_obj)
      unless (is_modify_action ? @can_modify : @can_control_vms)
        @redir_obj = @perm_obj unless @redir_obj
        flash[:notice] = 'You do not have permission to create or modify this item '
        if @json_hash
          @json_hash[:success] = false
          @json_hash[:alert] = flash[:notice]
          render :json => @json_hash
        elsif @redir_controller
          redirect_to :controller => @redir_controller, :action => 'show', :id => @redir_obj
        else
          redirect_to :action => 'show', :id => @redir_obj
        end
        false
      end
    end
  end

  # don't define find_opts for array inputs
  def json_list(full_items, attributes, arg_list=[], find_opts={})
    page = params[:page].to_i
    paginate_opts = {:page => page, 
                     :order => "#{params[:sortname]} #{params[:sortorder]}", 
                     :per_page => params[:rp]}
    arg_list << find_opts.merge(paginate_opts)
    item_list = full_items.paginate(*arg_list)
    json_hash = {}
    json_hash[:page] = page
    json_hash[:total] = item_list.total_entries
    json_hash[:rows] = item_list.collect do |item|
      item_hash = {}
      item_hash[:id] = item.id
      item_hash[:cell] = attributes.collect do |attr| 
        if attr.is_a? Array
          value = item
          attr.each { |attr_item| value = value.send(attr_item)}
          value
        else
          item.send(attr)
        end
      end
      item_hash
    end
    render :json => json_hash.to_json
  end



end
