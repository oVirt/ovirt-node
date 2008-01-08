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

    @first_id = permissions(:first).id
  end

  def test_index
    get :index
    assert_response :success
    assert_template 'list'
  end

  def test_list
    get :list

    assert_response :success
    assert_template 'list'

    assert_not_nil assigns(:permissions)
  end

  def test_show
    get :show, :id => @first_id

    assert_response :success
    assert_template 'show'

    assert_not_nil assigns(:permission)
    assert assigns(:permission).valid?
  end

  def test_new
    get :new

    assert_response :success
    assert_template 'new'

    assert_not_nil assigns(:permission)
  end

  def test_create
    num_permissions = Permission.count

    post :create, :permission => {}

    assert_response :redirect
    assert_redirected_to :action => 'list'

    assert_equal num_permissions + 1, Permission.count
  end

  def test_edit
    get :edit, :id => @first_id

    assert_response :success
    assert_template 'edit'

    assert_not_nil assigns(:permission)
    assert assigns(:permission).valid?
  end

  def test_update
    post :update, :id => @first_id
    assert_response :redirect
    assert_redirected_to :action => 'show', :id => @first_id
  end

  def test_destroy
    assert_nothing_raised {
      Permission.find(@first_id)
    }

    post :destroy, :id => @first_id
    assert_response :redirect
    assert_redirected_to :action => 'list'

    assert_raise(ActiveRecord::RecordNotFound) {
      Permission.find(@first_id)
    }
  end
end
