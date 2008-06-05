class TreeController < ApplicationController
  
  def fetch_nav
    @pools = Pool.root.full_set_nested(:method => :json_hash_element)
  end
  
  def fetch_json
    render :json => Pool.root.full_set_nested(:method => :json_hash_element).to_json
  end
end
