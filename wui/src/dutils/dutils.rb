# Copyright (C) 2008 Red Hat, Inc.
# Written by Chris Lalancette <clalance@redhat.com>
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

require 'active_record_env'
require 'krb5_auth'
include Krb5Auth

ENV['KRB5CCNAME'] = '/usr/share/ovirt-wui/ovirt-cc'

def get_credentials
  krb5 = Krb5.new
  default_realm = krb5.get_default_realm
  princ = 'libvirt/' + Socket::gethostname + '@' + default_realm

  now = Time.now
  renew = true
  begin
    krb5.list_cache(ENV['KRB5CCNAME']).each do |cred|
      endobj = Time.at(cred.endtime)
      if cred.client == princ and ((endobj.to_i - now.to_i) > 3600)
        # OK, we found our principal, and it expires more than an hour from
        # now; we don't need to renew credentials
        renew = false
        break
      end
    end
  rescue
    # in this case, there may not be a cache; just try to renew anyway
  end

  if renew
    begin
      krb5.get_init_creds_keytab('libvirt/' + Socket::gethostname + '@' + default_realm, '/usr/share/ovirt-wui/ovirt.keytab')
      krb5.cache(ENV['KRB5CCNAME'])
    rescue
      # well, if we run into an error here, there's not much we can do.  Just
      # print a warning, and blindly go on in the hopes that this was some sort
      # of temporary error
      puts "Error caching credentials; attempting to continue..."
      return
    end
  end
end
