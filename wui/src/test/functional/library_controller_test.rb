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
