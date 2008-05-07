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

# +LDAPConnection+ handles establishing, returning and closing
# connections with an LDAP server.
#
class LDAPConnection

  @@config = YAML::load(File.open("#{RAILS_ROOT}/config/ldap.yml"))

  # Connects the specified LDAP server.
  def self.connect(base = nil, host = nil, port = nil)
    
    base = @@config[ENV['RAILS_ENV']]["base"] if base == nil
    host = @@config[ENV['RAILS_ENV']]["host"] if host == nil
    port = @@config[ENV['RAILS_ENV']]["port"] if port == nil

    ActiveLdap::Base.establish_connection(:host => host,
					  :port => port,
					  :base => base) if LDAPConnection.connected? == false
  end

  # Returns whether a connection already exists to the LDAP server.
  def self.connected?
    return ActiveLdap::Base.connected?
  end

  # Disconnects from the LDAP server.
  def self.disconnect
    ActiveLdap::Base.remove_connection if LDAPConnection.connected?
  end

end
