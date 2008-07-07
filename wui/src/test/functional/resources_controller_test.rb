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

class ResourcesControllerTest < ActionController::TestCase
  def test_index
    get :index
    assert_response :success
    assert_not_nil assigns(:vm_resource_pools)
  end

  def test_new
    get :new, :parent_id => 1
    assert_response :success
  end

  def test_create
    assert_difference('VmResourcePool.count') do
      post :create, :vm_resource_pool => { :name => 'foo_resource_pool' }, :parent_id => 1
    end

    assert_response :success
  end

  def test_show
    get :show, :id => 2
    assert_response :success
  end

  def test_get
    get :edit, :id => 2
    assert_response :success
  end

  def test_update
    put :update, :id => 2, :vm_resource_pool => { }
    assert_response :redirect
    assert_redirected_to :action => 'list'
  end

  def test_destroy
    pool = nil
    assert_nothing_raised {
        pool = VmResourcePool.find(2).parent.id
    }

    post :destroy, :id => 2
    assert_response :success

    assert_raise(ActiveRecord::RecordNotFound) {
      VmResourcePool.find(2)
    }
  end
end
