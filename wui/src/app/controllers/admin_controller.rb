class AdminController < ApplicationController
  def index
    @host_pages, @hosts = paginate :hosts, :per_page => 10
    @storage_volume_pages, @storage_volumes = paginate :storage_volumes, :per_page => 10
    @user_quota_pages, @user_quotas = paginate :user_quotas, :per_page => 10
  end
end
