require File.dirname(__FILE__) + '/../test_helper'
require 'quotas_controller'

# Re-raise errors caught by the controller.
class QuotasController; def rescue_action(e) raise e end; end

class QuotasControllerTest < Test::Unit::TestCase
  def setup
    @controller = QuotasController.new
    @request    = ActionController::TestRequest.new
    @response   = ActionController::TestResponse.new
  end

  # Replace this with your real tests.
  def test_truth
    assert true
  end
end
