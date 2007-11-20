require File.dirname(__FILE__) + '/../test_helper'
require 'task_controller'

# Re-raise errors caught by the controller.
class TaskController; def rescue_action(e) raise e end; end

class TaskControllerTest < Test::Unit::TestCase
  fixtures :tasks

  def setup
    @controller = TaskController.new
    @request    = ActionController::TestRequest.new
    @response   = ActionController::TestResponse.new

    @first_id = tasks(:first).id
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

    assert_not_nil assigns(:tasks)
  end

  def test_show
    get :show, :id => @first_id

    assert_response :success
    assert_template 'show'

    assert_not_nil assigns(:task)
    assert assigns(:task).valid?
  end

  def test_new
    get :new

    assert_response :success
    assert_template 'new'

    assert_not_nil assigns(:task)
  end

  def test_create
    num_tasks = Task.count

    post :create, :task => {}

    assert_response :redirect
    assert_redirected_to :action => 'list'

    assert_equal num_tasks + 1, Task.count
  end

  def test_edit
    get :edit, :id => @first_id

    assert_response :success
    assert_template 'edit'

    assert_not_nil assigns(:task)
    assert assigns(:task).valid?
  end

  def test_update
    post :update, :id => @first_id
    assert_response :redirect
    assert_redirected_to :action => 'show', :id => @first_id
  end

  def test_destroy
    assert_nothing_raised {
      Task.find(@first_id)
    }

    post :destroy, :id => @first_id
    assert_response :redirect
    assert_redirected_to :action => 'list'

    assert_raise(ActiveRecord::RecordNotFound) {
      Task.find(@first_id)
    }
  end
end
