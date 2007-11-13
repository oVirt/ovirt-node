require File.dirname(__FILE__) + '/../test_helper'
require 'storage_controller'

# Re-raise errors caught by the controller.
class StorageController; def rescue_action(e) raise e end; end

class StorageControllerTest < Test::Unit::TestCase
  fixtures :storage_volumes

  def setup
    @controller = StorageController.new
    @request    = ActionController::TestRequest.new
    @response   = ActionController::TestResponse.new

    @first_id = storage_volumes(:first).id
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

    assert_not_nil assigns(:storage_volumes)
  end

  def test_show
    get :show, :id => @first_id

    assert_response :success
    assert_template 'show'

    assert_not_nil assigns(:storage_volume)
    assert assigns(:storage_volume).valid?
  end

  def test_new
    get :new

    assert_response :success
    assert_template 'new'

    assert_not_nil assigns(:storage_volume)
  end

  def test_create
    num_storage_volumes = StorageVolume.count

    post :create, :storage_volume => {}

    assert_response :redirect
    assert_redirected_to :action => 'list'

    assert_equal num_storage_volumes + 1, StorageVolume.count
  end

  def test_edit
    get :edit, :id => @first_id

    assert_response :success
    assert_template 'edit'

    assert_not_nil assigns(:storage_volume)
    assert assigns(:storage_volume).valid?
  end

  def test_update
    post :update, :id => @first_id
    assert_response :redirect
    assert_redirected_to :action => 'show', :id => @first_id
  end

  def test_destroy
    assert_nothing_raised {
      StorageVolume.find(@first_id)
    }

    post :destroy, :id => @first_id
    assert_response :redirect
    assert_redirected_to :action => 'list'

    assert_raise(ActiveRecord::RecordNotFound) {
      StorageVolume.find(@first_id)
    }
  end
end
