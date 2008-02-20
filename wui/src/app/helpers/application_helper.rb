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

# Methods added to this helper will be available to all templates in the application.

require 'rubygems'
gem 'rails'
require 'erb'

module ApplicationHelper

  def text_field_with_label(label, obj, meth) 
    %{ 
      <div class="i"><label for="#{obj}_#{meth}">#{_(label)}</label>
      #{text_field obj, meth}</div>
     }
  end

  def select_with_label(label, obj, meth, coll, opts={}) 
    %{ 
      <div class="i"><label for="#{obj}_#{meth}">#{_(label)}</label>
      #{select obj, meth, coll, opts}</div>
     }
  end

  def hidden_field_with_label(label, obj, meth, display) 
    %{ 
      <div class="i"><label for="#{obj}_#{meth}">#{_(label)}</label>
      #{hidden_field obj, meth}<span class="hidden">#{display}</span></div>
     }
  end

  def check_box_tag_with_label(label, name, value = "1", checked = false) 
    %{ 
      <div class="i"><label for="#{name}">#{_(label)}</label>
      #{check_box_tag name, value, checked}</div>
     }
  end

  def timeout_flash(name)
    %{
    <script type="text/javascript">
    // <![CDATA[
          var closeFlash = function() {$('#{name}').setStyle({'display':'none'})};
          setTimeout(closeFlash, 1000 * 45);
    // ]]>
    </script>
    }
  end

  def focus(field_name)
    %{
    <script type="text/javascript">
    // <![CDATA[
      Field.activate('#{field_name}');
    // ]]>
    </script>
    }
  end

  # this should probably be in the model instead
  def hardware_pool_type_to_controller(type)
    case type.to_s
      when "NetworkMap"
        return 'network_map'
      when "HostCollection"
        return 'collection'
      when "OrganizationalPool"
        return 'pool'
      else
        return 'dashboard'
    end
  end

end
