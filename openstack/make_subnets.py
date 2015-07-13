#!/usr/bin/python
# Title         make-subnets.py
# Description   Create subnets on OpenStack
# Author        I-Ming Chen <imchen@red5studios.com>
# Date          2015-05-14
# Version       0.0.1   
# Usage         ./make_subnets.py
#               ./make_subnets.py --provider OpenStack --networkid vpc-123456 --zone sa-east-1a --cidrblock 160 --cidrlist './path/to/json' --profile prod-sa-east-1 [--dryrun] [--verbose]
# Notes         Requires Python-OpenStack CLI installed
#============================================================================        

import sys
import argparse
import subprocess
import shlex
import readline
import json
import re
import time

DRYRUN="0" #NYI
CONFIRMATION="no"

def parse_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", help="Select provider (AWS/OpenStack)", nargs='?')
    parser.add_argument("--networkid", help="OpenStack Network ID", nargs='?')
    parser.add_argument("--zone", help="Availability Zone", nargs='?')
    parser.add_argument("--cidrblock", help="Subnet CIDR Block (x in 10.x.y.z/16)", nargs='?')
    parser.add_argument("--cidrlist", help="CIDR/Name list (JSON)")
    parser.add_argument("--profile", help="AWS CLI Profile", nargs='?')
    parser.add_argument("--throttle", help="Throttle calls to OpenStack by this timer", action="store_true")
    parser.add_argument("--dryrun", help="output without doing any real calls", action="store_true")
    parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
    args = parser.parse_args()
    if args.dryrun:
        print "Make Subnets: Dryrun Mode On"
    if args.verbose:
        print "Make Subnets: Verbose Mode On"
    return args

def parse_cidr_list(json_file):
    json_data = open(json_file)
    data = json.load(json_data)
    json_data.close()
    return data

def interactive(args):
    global CONFIRMATION
    args.provider = raw_input("Select provider (AWS/OpenStack): ")
    args.networkid = raw_input("Enter network ID: ")
    args.zone = raw_input("Enter availability zone: ")
    args.cidrblock = raw_input("Enter regional VPC subnet (x in 10.x.y.z): ")
    args.cidrlist = raw_input("Enter CIDR list (include path): ")
    args.profile = raw_input("Enter AWS CLI profile name: ")
    cidr_list = parse_cidr_list(args.cidrlist)
    for cidr in cidr_list.keys():
        cidr = re.sub('[x]', args.cidrblock, cidr)
        print "aws ec2 create-subnet --vpc-id %s --availability-zone %s --cidr-block %s --profile %s" % (args.networkid, args.zone, cidr, args.profile)
    CONFIRMATION = raw_input("Is this what you want to build? [YES/NO] ")

def main(args):
    # TODO: Determine if we have aws cli installed

    print "### OpenStack Subnet Creator! ###"
    global CONFIRMATION

    # Check if interactive version or otherwise
    if not args.profile:
        interactive()
    else:
        CONFIRMATION="YES"

    try:
        cidr_list
    except NameError:
        cidr_list = parse_cidr_list(args.cidrlist)

    if (CONFIRMATION == "YES" or CONFIRMATION == "yes" or CONFIRMATION == "Y" or CONFIRMATION == "y"):
        print "Creating networks and attaching subnets to each!"
        for cidr, sn_name in cidr_list.items():
            cidr = re.sub('[x]', args.cidrblock, cidr)
            #neutron net-create [--tenant-id TENANT_ID] [--name NETWORK_NAME] NETWORK_ID_OR_NAME
            #neutron subnet-create [--tenant-id TENANT_ID] [--name SUBNET_NAME] NETWORK_ID_OR_NAME CIDR

            # TODO: Consider removing this net part; make user define it in config
            network_name = "net-" + sn_name
            print "neutron net-create %s -f json" % (network_name)
            command = "neutron net-create %s -f json" % (network_name)
            process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
            output = process.communicate()[0] # Optional output
            trash, output = output.split("\n", 1)
            network_output = json.loads(output)
            network_id = 0
            key_found = 0
            for eachdict in network_output:
                for key,value in eachdict.iteritems():
                    if key_found == 1:
                        network_id = value
                        key_found = 0
                    if value == "id":
                        key_found = 1
            print "Network ID: " + str(network_id)
            # Delay for OpenStack request
            time.sleep(1)

            # TODO: Consider removing this subnet part; make user define it in config
            sn_name = "subnet-" + sn_name
            #print "neutron subnet-create --name %s  %s %s" % (sn_name, network_id, cidr)
            ##command = "neutron subnet-create --name %s %s %s" % (sn_name, network_id, cidr)

            # This is for adding additional hosts for hardware VPN connections
            # TODO: Consider detecting dynamic number of host routes to add and injecting them into command if requested
            # TODO: We should probably require explicit start and end CIDR addresses because there are exceptions to the rule
            # e.g. inside-app starts at 10.x.4.0 but ends at 10.x.7.254 instead of 10.x.4.254
            # You know, we DO know the size of the block because the CIDR is well defined in the config
            ipaddress,mask = cidr.split("/",1)
            a,b,c,d = ipaddress.split(".",4)
            subnet_nexthop1 = a + "." + args.cidrblock + "." + c + "." + "254"
            subnet_nexthop2 = a + "." + args.cidrblock + "." + c + "." + "254"
            print "neutron subnet-create --name %s --host-route destination=10.1.0.0/16,nexthop=%s --host-route destination=10.2.0.0/16,nexthop=%s %s %s" \
                  % (sn_name, subnet_nexthop1, subnet_nexthop2, network_id, cidr)
            command = "neutron subnet-create --name %s --host-route destination=10.1.0.0/16,nexthop=%s --host-route destination=10.2.0.0/16,nexthop=%s %s %s" \
                       % (sn_name, subnet_nexthop1, subnet_nexthop2, network_id, cidr)
            process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
#            output = process.communicate()[0] # Optional output
#            subnet_output = json.loads(output)

            #OpenStack outputs different stuff
#            subnet_id = subnet_output["subnet"]["id"]
            # Delay for OpenStack request
            time.sleep(1)
        print "### Done creating stuff! ###"
        return
    else:
        print "### Okay, canceling. ###"
        sys.exit(1) #Failure

if __name__ == '__main__':
    args = parse_options()
    print args

    if len(sys.argv) == 1:
        main(args)
    elif len(sys.argv) == 11:
        main(args)
    else:
        print "ERROR: Wrong number of arguments."
        sys.exit(1)

    sys.exit()
