#!/usr/bin/ruby

require 'socket'
require 'rubygems'
require 'kerberos'
include Kerberos

def kadmin_local(command)
  # FIXME: we really should implement the ruby-kerberos bindings to do the
  # same thing as kadmin.local
  # FIXME: we should check the return value from the system() call and throw
  # an exception.
  # FIXME: we need to return the output back to the caller here
  system("/usr/kerberos/sbin/kadmin.local -q '" + command + "'")
end

$stdout = File.new('/var/log/ovirt-wui/host-keyadd.log', 'a')
$stderr = File.new('/var/log/ovirt-wui/host-keyadd.log', 'a')

server = TCPServer.new(6666)

pid = fork do
  loop do
    Thread.start(server.accept) do |s|
      cmd = s.read(4)
      if cmd.length != 4 or cmd != "KERB"
        s.write("FAILED")
      else
        remote = Socket.unpack_sockaddr_in(s.getpeername)
        remote_name = Socket.getnameinfo(s.getpeername)
        
        krb5 = Krb5.new
        default_realm = krb5.get_default_realm
        
        libvirt_princ = 'libvirt/' + remote_name[0] + '@' + default_realm
        
        outname = '/usr/share/ipa/html/' + remote[1] + '-libvirt.tab'
        
        kadmin_local('addprinc -randkey ' + libvirt_princ)
        kadmin_local('ktadd -k ' + outname + ' ' + libvirt_princ)
        File.chmod(0644, outname)
        s.write('SUCCESS')
      end
      s.close
    end
  end
end

Process.detach(pid)
