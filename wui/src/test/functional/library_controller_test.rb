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

class LibraryControllerTest < ActionController::TestCase
  def test_should_get_index
    get :index
    assert_response :success
    assert_not_nil assigns(:vm_libraries)
  end

  def test_should_get_new
    get :new
    assert_response :success
  end

  def test_should_create_vm_library
    assert_difference('VmLibrary.count') do
      post :create, :vm_library => { }
    end

    assert_redirected_to vm_library_path(assigns(:vm_library))
  end

  def test_should_show_vm_library
    get :show, :id => 1
    assert_response :success
  end

  def test_should_get_edit
    get :edit, :id => 1
    assert_response :success
  end

  def test_should_update_vm_library
    put :update, :id => 1, :vm_library => { }
    assert_redirected_to vm_library_path(assigns(:vm_library))
  end

  def test_should_destroy_vm_library
    assert_difference('VmLibrary.count', -1) do
      delete :destroy, :id => 1
    end

    assert_redirected_to vm_libraries_path
  end
end
