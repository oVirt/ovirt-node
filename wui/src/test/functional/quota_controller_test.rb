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
require 'quota_controller'

# Re-raise errors caught by the controller.
class QuotaController; def rescue_action(e) raise e end; end

class QuotaControllerTest < Test::Unit::TestCase
  fixtures :quotas

  def setup
    @controller = QuotaController.new
    @request    = ActionController::TestRequest.new
    @response   = ActionController::TestResponse.new

    @first_id = quotas(:one).id
  end

  def test_show
    get :show, :id => @first_id

    assert_response :success
    assert_template 'show'

    assert_not_nil assigns(:quota)
    assert assigns(:quota).valid?
  end

  def test_new
    get :new, :pool_id => 1

    assert_response :success
    assert_template 'new'

    assert_not_nil assigns(:quota)
  end

  def test_create
    num_quotas = Quota.count

    post :create, :quota => { :pool_id => 8 }

    assert_response :success

    assert_equal num_quotas + 1, Quota.count
  end

  def test_edit
    get :edit, :id => @first_id

    assert_response :success
    assert_template 'edit'

    assert_not_nil assigns(:quota)
    assert assigns(:quota).valid?
  end

  def test_update
    post :update, :id => @first_id
    assert_response :success
  end

  def test_destroy
    pool = nil
    assert_nothing_raised {
      quota = Quota.find(@first_id)
      pool = quota.pool
    }

    post :destroy, :id => @first_id
    assert_response :success

    assert_raise(ActiveRecord::RecordNotFound) {
      Quota.find(@first_id)
    }
  end
end
