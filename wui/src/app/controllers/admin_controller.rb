class AdminController < ApplicationController
  scaffold :host
  scaffold :storage_volume
  scaffold :user_quota
  scaffold :vm

end
