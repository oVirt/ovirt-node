(*
Module: Resolv
  Parses /etc/resolv.conf

Author: Raphael Pinson <raphink@gmail.com>

About: Reference
  This lens tries to keep as close as possible to `man resolv.conf` where possible.

About: Licence
  This file is licensed under the LGPLv2+, like the rest of Augeas.

About: Lens Usage

About: Configuration files
  This lens applies to /etc/resolv.conf. See <filter>.
*)

module Resolv =
autoload xfm

(************************************************************************
 * Group:                 USEFUL PRIMITIVES
 *************************************************************************)

(* View: comment *)
let comment = Utill.comment_generic /[ \t]*[;#][ \t]*/ "# "

(* View: empty *)
let empty = Utill.empty


(************************************************************************
 * Group:                 MAIN OPTIONS
 *************************************************************************)

(* View: netmask
A network mask for IP addresses *)
let netmask = [ label "netmask" . Utill.del_str "/" . store Rx.ip ]

(* View: ipaddr 
An IP address or range with an optional mask *) 
let ipaddr = [label "ipaddr" . store Rx.ip . netmask?]


(* View: nameserver
     A nameserver entry *)
let nameserver = Buildd.key_value_line 
                    "nameserver" Sep.space (store Rx.ip)

(* View: domain *)
let domain = Buildd.key_value_line
                    "domain" Sep.space (store Rx.word)

(* View: search *)
let search = Buildd.key_value_line
                    "search" Sep.space
                    (Buildd.opt_list 
                           [label "domain" . store Rx.word]
                            Sep.space)

(* View: sortlist *)
let sortlist = Buildd.key_value_line
                    "sortlist" Sep.space
                    (Buildd.opt_list
                           ipaddr
                           Sep.space) 

(************************************************************************
 * Group:                 SPECIAL OPTIONS
 *************************************************************************)

(* View: ip6_dotint
     ip6-dotint option, which supports negation *)
let ip6_dotint = 
  let negate = [ del "no-" "no-" . label "negate" ]
    in [ negate? . key "ip6-dotint" ]

(* View: options 
     Options values *)
let options =
      let options_entry = Buildd.key_value ("ndots"|"timeout"|"attempts") 
                                          (Utill.del_str ":") (store Rx.integer)
                        | Buildd.flag ("debug"|"rotate"|"no-check-names"
                                     |"inet6"|"ip6-bytestring"|"edns0")
                        | ip6_dotint

            in Buildd.key_value_line
                    "options" Sep.space
                    (Buildd.opt_list
                           options_entry
                           Sep.space)

(* View: entry *)
let entry = nameserver
          | domain
          | search
          | sortlist
          | options

(* View: lns *)
let lns = ( empty | comment | entry )*

(* Variable: filter *)
let filter = (incl "/etc/resolv.conf")
    . Utill.stdexcl

let xfm = transform lns filter

