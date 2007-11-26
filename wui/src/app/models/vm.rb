class Vm < ActiveRecord::Base
  belongs_to :user
  belongs_to :host
  has_many :tasks, :dependent => :destroy
  has_and_belongs_to_many :storage_volumes

  STATE_CREATING  = "creating"
  STATE_DELETING  = "deleting"
  STATE_MIGRATING = "migrating"
  STATE_PAUSED    = "paused"
  STATE_PAUSING   = "pausing"
  STATE_PENDING   = "pending"
  STATE_RUNNING   = "running"
  STATE_STARTED   = "started"
  STATE_STARTING  = "starting"
  STATE_STOPPED   = "stopped"
  STATE_STOPPING  = "stopping"
  STATE_UNKNOWN   = "unknown"
  STATE_UNPAUSING = "unpausing"
  STATE_SAVED     = "saved"

end
