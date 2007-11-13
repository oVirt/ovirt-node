require File.dirname(__FILE__) + '/../test_helper'
require 'quota_controller'

# Re-raise errors caught by the controller.
class QuotaController; def rescue_action(e) raise e end; end

class QuotaControllerTest < Test::Unit::TestCase
  fixtures :user_quotas

  def setup
    @controller = QuotaController.new
    @request    = ActionController::TestRequest.new
    @response   = ActionController::TestResponse.new

    @first_id = user_quotas(:first).id
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

    assert_not_nil assigns(:user_quotas)
  end

  def test_show
    get :show, :id => @first_id

    assert_response :success
    assert_template 'show'

    assert_not_nil assigns(:user_quota)
    assert assigns(:user_quota).valid?
  end

  def test_new
    get :new

    assert_response :success
    assert_template 'new'

    assert_not_nil assigns(:user_quota)
  end

  def test_create
    num_user_quotas = UserQuota.count

    post :create, :user_quota => {}

    assert_response :redirect
    assert_redirected_to :action => 'list'

    assert_equal num_user_quotas + 1, UserQuota.count
  end

  def test_edit
    get :edit, :id => @first_id

    assert_response :success
    assert_template 'edit'

    assert_not_nil assigns(:user_quota)
    assert assigns(:user_quota).valid?
  end

  def test_update
    post :update, :id => @first_id
    assert_response :redirect
    assert_redirected_to :action => 'show', :id => @first_id
  end

  def test_destroy
    assert_nothing_raised {
      UserQuota.find(@first_id)
    }

    post :destroy, :id => @first_id
    assert_response :redirect
    assert_redirected_to :action => 'list'

    assert_raise(ActiveRecord::RecordNotFound) {
      UserQuota.find(@first_id)
    }
  end
end
