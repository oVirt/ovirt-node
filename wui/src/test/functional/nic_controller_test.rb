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

require File.dirname(__FILE__) + '/../test_helper'
require 'nic_controller'

# Re-raise errors caught by the controller.
class NicController; def rescue_action(e) raise e end; end

class NicControllerTest < Test::Unit::TestCase
  fixtures :nics

  def setup
    @controller = NicController.new
    @request    = ActionController::TestRequest.new
    @response   = ActionController::TestResponse.new

    @first_id = nics(:one).id
  end

  def test_show
    get :show, :id => @first_id

    assert_response :success
    assert_template 'show'

    assert_not_nil assigns(:nic)
    assert assigns(:nic).valid?
  end

  def test_new
    get :new, :host_id => 1

    assert_response :redirect
    assert_redirected_to :controller => 'host', :action => 'show', :id => 1

  end

  def test_create
    num_nics = Nic.count

    post :create, :nic => {}

    assert_response :redirect
    assert_redirected_to :controller => 'dashboard'

    assert_equal num_nics, Nic.count
  end

  def test_edit
    get :edit, :id => @first_id

    assert_response :redirect
    assert_redirected_to :action => 'show', :id => @first_id

    assert_not_nil assigns(:nic)
    assert assigns(:nic).valid?
  end

  def test_update
    post :update, :id => @first_id
    assert_response :redirect
    assert_redirected_to :action => 'show', :id => @first_id
  end

  def test_destroy
    assert_nothing_raised {
      Nic.find(@first_id)
    }

    post :destroy, :id => @first_id
    assert_response :redirect
    assert_redirected_to :action => 'show', :id => @first_id

    assert_nothing_raised {
      Nic.find(@first_id)
    }
  end
end
