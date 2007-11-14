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

    @first_id = nics(:first).id
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

    assert_not_nil assigns(:nics)
  end

  def test_show
    get :show, :id => @first_id

    assert_response :success
    assert_template 'show'

    assert_not_nil assigns(:nic)
    assert assigns(:nic).valid?
  end

  def test_new
    get :new

    assert_response :success
    assert_template 'new'

    assert_not_nil assigns(:nic)
  end

  def test_create
    num_nics = Nic.count

    post :create, :nic => {}

    assert_response :redirect
    assert_redirected_to :action => 'list'

    assert_equal num_nics + 1, Nic.count
  end

  def test_edit
    get :edit, :id => @first_id

    assert_response :success
    assert_template 'edit'

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
    assert_redirected_to :action => 'list'

    assert_raise(ActiveRecord::RecordNotFound) {
      Nic.find(@first_id)
    }
  end
end
