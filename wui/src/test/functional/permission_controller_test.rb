 
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

require File.dirname(__FILE__) + '/../test_helper'
require 'permission_controller'

# Re-raise errors caught by the controller.
class PermissionController; def rescue_action(e) raise e end; end

class PermissionControllerTest < Test::Unit::TestCase
  fixtures :permissions

  def setup
    @controller = PermissionController.new
    @request    = ActionController::TestRequest.new
    @response   = ActionController::TestResponse.new

    @first_id = permissions(:one).id
  end

  def test_show
    get :show, :id => @first_id

    assert_response :success
    assert_template 'show'

    assert_not_nil assigns(:permission)
    assert assigns(:permission).valid?
  end

  def test_new
    get :new, :pool_id => 1

    assert_response :success
    assert_template 'new'

    assert_not_nil assigns(:permission)
  end

  def test_create
    num_permissions = Permission.count

    post :create, :permission => { :user_role => 'Administrator', :uid => 'admin', :pool_id => 2}

    assert_response :success

    assert_equal num_permissions + 1, Permission.count
  end

  def test_destroy
    assert_nothing_raised {
      Permission.find(@first_id)
    }

    post :destroy, :id => @first_id
    assert_response :redirect
    assert_redirected_to :controller => 'hardware', :action => 'show', :id => 1


    assert_raise(ActiveRecord::RecordNotFound) {
      Permission.find(@first_id)
    }
  end
end
