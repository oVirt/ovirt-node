require File.dirname(__FILE__) + '/../test_helper'
require 'pool_controller'

# Re-raise errors caught by the controller.
class PoolController; def rescue_action(e) raise e end; end

class PoolControllerTest < Test::Unit::TestCase
  fixtures :hardware_resource_groups

  def setup
    @controller = PoolController.new
    @request    = ActionController::TestRequest.new
    @response   = ActionController::TestResponse.new

    @first_id = hardware_resource_groups(:first).id
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

    assert_not_nil assigns(:hardware_resource_groups)
  end

  def test_show
    get :show, :id => @first_id

    assert_response :success
    assert_template 'show'

    assert_not_nil assigns(:hardware_resource_group)
    assert assigns(:hardware_resource_group).valid?
  end

  def test_new
    get :new

    assert_response :success
    assert_template 'new'

    assert_not_nil assigns(:hardware_resource_group)
  end

  def test_create
    num_hardware_resource_groups = HardwareResourceGroup.count

    post :create, :hardware_resource_group => {}

    assert_response :redirect
    assert_redirected_to :action => 'list'

    assert_equal num_hardware_resource_groups + 1, HardwareResourceGroup.count
  end

  def test_edit
    get :edit, :id => @first_id

    assert_response :success
    assert_template 'edit'

    assert_not_nil assigns(:hardware_resource_group)
    assert assigns(:hardware_resource_group).valid?
  end

  def test_update
    post :update, :id => @first_id
    assert_response :redirect
    assert_redirected_to :action => 'show', :id => @first_id
  end

  def test_destroy
    assert_nothing_raised {
      HardwareResourceGroup.find(@first_id)
    }

    post :destroy, :id => @first_id
    assert_response :redirect
    assert_redirected_to :action => 'list'

    assert_raise(ActiveRecord::RecordNotFound) {
      HardwareResourceGroup.find(@first_id)
    }
  end
end
