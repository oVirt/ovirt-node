require File.dirname(__FILE__) + '/../test_helper'
require 'vm_controller'

# Re-raise errors caught by the controller.
class VmController; def rescue_action(e) raise e end; end

class VmControllerTest < Test::Unit::TestCase
  fixtures :vms

  def setup
    @controller = VmController.new
    @request    = ActionController::TestRequest.new
    @response   = ActionController::TestResponse.new

    @first_id = vms(:first).id
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

    assert_not_nil assigns(:vms)
  end

  def test_show
    get :show, :id => @first_id

    assert_response :success
    assert_template 'show'

    assert_not_nil assigns(:vm)
    assert assigns(:vm).valid?
  end

  def test_new
    get :new

    assert_response :success
    assert_template 'new'

    assert_not_nil assigns(:vm)
  end

  def test_create
    num_vms = Vm.count

    post :create, :vm => {}

    assert_response :redirect
    assert_redirected_to :action => 'list'

    assert_equal num_vms + 1, Vm.count
  end

  def test_edit
    get :edit, :id => @first_id

    assert_response :success
    assert_template 'edit'

    assert_not_nil assigns(:vm)
    assert assigns(:vm).valid?
  end

  def test_update
    post :update, :id => @first_id
    assert_response :redirect
    assert_redirected_to :action => 'show', :id => @first_id
  end

  def test_destroy
    assert_nothing_raised {
      Vm.find(@first_id)
    }

    post :destroy, :id => @first_id
    assert_response :redirect
    assert_redirected_to :action => 'list'

    assert_raise(ActiveRecord::RecordNotFound) {
      Vm.find(@first_id)
    }
  end
end
