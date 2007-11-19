class ConsumerController < ApplicationController
  def index
    @user = User.find(:first, :conditions => [ "ldap_uid = ?", get_login_user])
    if @user
      @quota = @user.user_quota
    else
      @quota = nil
    end
  end

end
