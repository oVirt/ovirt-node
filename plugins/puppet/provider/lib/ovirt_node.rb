# ovirt_node.rb - Copyright (C) 2013 Red Hat, Inc.
# Written by Ryan Barry <rbarry@redhat.com>
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

require 'fileutils'
require 'filetest'
require 'augeas'

Puppet::Type.type(:ovirt_node).provide(:ovirt) do
    commands :python => "/usr/bin/python"

    def initialize(value={})
        super(value)
        @property_flush = {}
    end

    def update_wrapper(type, value)
        python("-c 'from ovirt.node.config import defaults; model = defaults.#{type}(); model.update(#{value}); tx = model.transaction(); tx()'")
    end

    def instances
        config_vars = %w[hostname ssh_pwauth dns ip_address ip_gateway ip_netmask
                         management_server use_strong_rng]
        if FileTests.exists?("/etc/pki/vdsm/certs/engine_web_ca.pem")
          engine = %x(openssl x509 -in /etc/pki/vdsm/certs/engine_web_ca.pem -noout -issuer).
              match(/CN=CA-(.*?)\.\d+$/)
          if engine?
              vars = {}
#              augtool = %x(augtool print /files/etc/default/ovirt | grep = | awk '{print $1}')
              keys = Hash[keys.split("\n").collect.map { |x| [x, nil] } ]
              keys.each.key do |key|
                  if config_vars.include? "OVIRT_#{key}".downcase
                      Augeas::open do |aug|
                          x = aug.get(key)
                          vars[key.split("/").last.to_sym] = x
                      end
                  end
              end
              new(vars)
          end
        end
    end

    def exists?
        `openssl x509 -in /etc/pki/vdsm/certs/engine_web_ca.pem -noout -issuer`
        .match(/CN=CA-#{@resource[:address]}/) ? true : false
    end

    def address=(engine)
        puts "Do nothing"
        #Waiting to see logic from new VDSM plugin
    end

    def nfsdomain=(domain)
        # The py snippet below will only change the runtime configuratio (NFSv4 domain)
        # To make persistent changes we'll need to use the ovirt.node.config.defaults
        # module, which gives us access to all topics which are covered by Node's logic.
        # ovirt.node.utils.* modules only change the runtime config, but don't persist the
        # changes.
        # See ssh_pwauth for a complete example
        update_wrapper("NFS", domain)
    end

    def iscsi_initiator=(name)
        update_wrapper("iSCSI", name)
    end

    def ssh=(bool)
        # It needs to be ensured that #{bool} is either True or False (so a bool in py syntax)
        value = ""
        if bool
            value = "True"
        else
            value = "False"
        end
        update_wrapper("SSH", value)
    end

    def kdump=(options)
        kdump = options.first
        kdump.each do |type, server|
            if type.downcase == "ssh"
                #It's SSH
                update_wrapper("KDump", "None, #{server}, None")
            elsif type.downcase == "nfs"
                update_wrapper("KDump", "#{server}, None, None")
            end
        end
    end

    def rsyslog=(server)
        server, port = server.split(":")[0]
        port = port ? port : 514
        update_wrapper("Syslog", "#{server}, #{port}")
    end

    def netconsole=(server)
        server, port = server.split(":")[0]
        port = port ? port : 6666
        update_wrapper("Netconsole", "#{server}, #{port}")
    end

    def monitoring=(server)
        server, port = server.split(":")[0]
        port = port ? port : 7634
        update_wrapper("Collectd", "#{server}, #{port}")
    end

    def ntp=(servers)
        update_wrapper("Timeservers", "[#{servers.join(", ")}]")
    end

    def ntp=(servers)
        update_wrapper("Nameservers", "[#{servers.join(", ")}]")
    end

end
