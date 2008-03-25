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

def gb_to_kb(val_in_gigs)
  return nil if nil_or_empty(val_in_gigs)
  return val_in_gigs.to_i * 1024 * 1024
end
 
def kb_to_gb(val_in_kb)
  return nil if nil_or_empty(val_in_kb)
  return val_in_kb.to_i / 1024 / 1024
end
def mb_to_kb(val_in_mb)
  return nil if nil_or_empty(val_in_mb)
  return val_in_mb.to_i * 1024
end
 
def kb_to_mb(val_in_kb)
  return nil if nil_or_empty(val_in_kb)
  return val_in_kb.to_i / 1024
end

def nil_or_empty(val)
  if val.nil? or (val.kind_of?(String) and val.empty?)
    return true
  else
    return false
  end
end
