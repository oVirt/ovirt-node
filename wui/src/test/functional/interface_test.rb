#
# Copyright (C) 2008 Red Hat, Inc.
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

if File.exists? File.dirname(__FILE__) + '/../selenium.rb'

 require File.dirname(__FILE__) + '/../test_helper'
 require File.dirname(__FILE__) + '/../selenium'

 class InterfaceTest < Test::Unit::TestCase
         def setup
            @browser = Selenium::SeleniumDriver.new("192.168.50.1", 4444,
                           "*firefox /usr/lib64/firefox-3.0.1/firefox",
                           "http://192.168.50.2/ovirt/", 15000)
            @browser.start
         end

         def test_ovirt
            @browser.open("http://192.168.50.2/ovirt/")
            assert_equal("Dashboard", @browser.get_title())
	    @browser.close
         end

         def teardown
            @browser.stop
         end
 end

end
