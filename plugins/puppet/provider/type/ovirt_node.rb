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

Puppet::Type.newtype(:ovirt_node) do

    ensurable

    newparam(:address, :namevar => true) do
        desc "The address of the engine"
    end

    newparam(:nfsdomain) do
        desc "The NFSv4 domain for the node"
    end

    newparam(:iscsi_initiator) do
        desc "The iSCSI Initiator Name"
    end

    newparam(:kdump) do
        desc "kdump configuration"
    end

    newparam(:ssh) do
        desc "Enable SSH authentication"
        newvalues(:True, :true, :False, :false)
        defaultto :False

        munge do |value|
            case value
            when :true
                :True
            when :false
                :False
            else
                super
            end
        end
    end

    newparam(:rsyslog) do
        desc "RSyslog server"
    end

    newparam(:netconsole) do
        desc "Netconsole server"
    end

    newparam(:monitoring) do
        desc "Monitoring server"
    end
end
