# ovirt.rb - Copyright (C) 2013 Red Hat, Inc.
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

Facter.add(:operatingsystem) do
    has_weight 100_000_000
    confine :kernel => :linux
    setcode do
        if FileTest.exists?("/etc/system-release")
            txt = File.read("/etc/system-release")
            if txt =~ /^(.*?)\srelease.*/
                $1.gsub(//, '')
            end
        elsif FileTest.exists?("/etc/default/version")
            txt = File.read("/etc/default/version")
            if txt =~ /^PRODUCT='(.*?)'/
                $1.gsub(//, '')
            end
        end
    end
end

Facter.add(:operatingsystemrelease) do
    confine :operatingsystem => %w{oVirt oVirtNodeHypervisor
                                   RedHatEnterpriseVirtualizationHypervisor}
    setcode do
        if FileText.exists?("/etc/system-release")
            txt = File.text("/etc/system-release")
            if txt =~ /.*?release\s(.*?)\s/
                $1
            end
        elsif FileTest.exists?("/etc/default/version")
            txt = File.read("/etc/default/version")
            if txt =~ /^VERSION=(.*)/
                $1
            else
                "unknown"
            end
        end
    end
end
