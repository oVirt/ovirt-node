require 'pp'
require 'rubygems'
require 'activeresource'

module OVirt
    class Base < ActiveResource::Base ; end

    class HardwarePool < Base
        def self.find_by_path(path)
            find(:first, :params => { :path => path })
        end

        def self.default_pool
            find(:first, :params => { :path => "/default" })
        end
    end

    class StoragePool < Base
        def iscsi?
            attributes["type"] == "IscsiStoragePool"
        end

        def nfs?
            attributes["type"] == "NfsStoragePool"
        end

        def label
            if iscsi?
                "#{ip_addr}:#{port}:#{target}"
            elsif nfs?
                "#{ip_addr}:#{export_path}"
            else
                raise "Unknown type #{attributes["type"]}"
            end
        end
    end

    class IscsiStoragePool < StoragePool
        def initialize(attributes = {})
            super(attributes.update( "type" => "IscsiStoragePool" ))
        end
    end

    class NfsStoragePool < StoragePool
        def initialize(attributes = {})
            super(attributes.update( "type" => "NfsStoragePool" ))
        end
    end

    class Host < Base
        def self.find_by_uuid(uuid)
            find(:first, :params => { :uuid => uuid })
        end

        def self.find_by_hostname(hostname)
            find(:first, :params => { :hostname => hostname })
        end

        def hardware_pool
            HardwarePool.find(hardware_pool_id)
        end
    end
end
