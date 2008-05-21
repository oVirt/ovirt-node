# 
# Copyright (C) 2008 Red Hat, Inc.
# Written by Darryl L. Pierce <dpierce@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.

# +Account+ represents a single user's account from the LDAP server.
#
class Account < ActiveLdap::Base
  ldap_mapping :dn_attribute => 'cn', :scope => :one, :prefix => 'cn=users,cn=accounts'

  @@users = nil

  # +query+ returns the set of all accounts that contain the given search value.
  #
  # This API requires that a previous connection be made using 
  # +LDAPConnection.connect+.
  #
  def Account.query(value)

    @@users ||= Account.find(:all, value)

    if block_given?
      @@users.each { |user| yield(user) }
    end

    @@users    
  end

  # Retrieves the list of users from LDAP and returns a hash of
  # their uids, indexed by their common name in the form:
  # +username (uid) => uid+
  #
  # if a filter is passed in, those user ids are filtered out
  # of the returned list.
  #
  def Account.names(filter = [])
    result = {}

    Account.query('*') do |user|
      unless filter.include? user.uid
	key = "#{user.cn} (#{user.uid})"
	result[key] = user.uid
      end
    end

    result.sort
  end

end
