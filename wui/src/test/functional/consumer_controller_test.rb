require File.dirname(__FILE__) + '/../test_helper'
require 'consumer_controller'

# Re-raise errors caught by the controller.
class ConsumerController; def rescue_action(e) raise e end; end

class ConsumerControllerTest < Test::Unit::TestCase
  def setup
    @controller = ConsumerController.new
    @request    = ActionController::TestRequest.new
    @response   = ActionController::TestResponse.new
  end

  # Replace this with your real tests.
  def test_truth
    assert true
  end
end
