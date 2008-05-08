# 
# Copyright (C) 2008 Red Hat, Inc.
# Written by Scott Seago <sseago@redhat.com>
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

require 'util/ovirt'

class Host < ActiveRecord::Base
  belongs_to :hardware_pool
  has_many :nics, :dependent => :destroy
  has_many :vms, :dependent => :nullify

  KVM_HYPERVISOR_TYPE = "KVM"
  HYPERVISOR_TYPES = [KVM_HYPERVISOR_TYPE]
  def memory_in_mb
    kb_to_mb(memory)
  end
  def memory_in_mb=(mem)
    self[:memory]=(mb_to_kb(mem))
  end
  def is_disabled_str
    if is_disabled.nil? or is_disabled == 0
      "No"
    else
      "Yes"
    end
  end
end
