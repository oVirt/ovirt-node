#
# Copyright (C) 2008 Red Hat, Inc.
# Written by Steve Linabery <slinabery@redhat.com>
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

class LoginController < ActionController::Base

  before_filter :is_logged_in, :except => :login
  def login
    session[:user] = (ENV["RAILS_ENV"] == "production") ?
    user_from_principal(request.env["HTTP_X_FORWARDED_USER"]) :
      "ovirtadmin"
    redirect_to :controller => "dashboard"
  end

  def user_from_principal(principal)
    principal.split('@')[0]
  end

end
