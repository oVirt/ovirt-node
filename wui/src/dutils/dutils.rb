require 'rubygems'
require 'kerberos'
include Kerberos
require 'active_record'
require 'erb'

ENV['KRB5CCNAME'] = '/usr/share/ovirt-wui/ovirt-cc'

def database_connect
  $dbconfig = YAML::load(ERB.new(IO.read('/usr/share/ovirt-wui/config/database.yml')).result)
  $develdb = $dbconfig['development']
  ActiveRecord::Base.establish_connection(
                                          :adapter  => $develdb['adapter'],
                                          :host     => $develdb['host'],
                                          :username => $develdb['username'],
                                          :password => $develdb['password'],
                                          :database => $develdb['database']
                                          )
end

def get_credentials
  begin
    krb5 = Krb5.new
    default_realm = krb5.get_default_realm
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

