#!/usr/bin/python
# Title         make_flavors.py
# Description   Create flavors on OpenStack
# Author        I-Ming Chen <imchen@red5studios.com>
# Date          2015-05-13
# Version       0.0.1   
# Usage         ./make_flavors.py
#               ./make_flavors.py --networkid vpc-123456 --flavorlist './path/to/json' --profile prod-sa-east-1 [--dryrun] [--verbose]
# Notes         Requires Python OpenStack CLI installed
#               Many of the fields are still placeholders. I imagine network ID and profile to not be used because
#               authentication is usually done with the OpenStackrc file. However, this may not be the case for
#               automated system process. It may just require the user/pass, auth host, and tenant ID.
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
    parser.add_argument("--networkid", help="OpenStack Network ID", nargs='?')
    parser.add_argument("--flavorlist", help="Flavor list (JSON)")
    parser.add_argument("--profile", help="Profile", nargs='?')
    parser.add_argument("--dryrun", help="Output without doing any real calls", action="store_true")
    parser.add_argument("--verbose", help="Increase output verbosity", action="store_true")
    args = parser.parse_args()
    if args.dryrun:
        print "Make Subnets: Dryrun Mode On"
    if args.verbose:
        print "Make Subnets: Verbose Mode On"
    return args

def parse_flavor_list(json_file):
    json_data = open(json_file)
    data = json.load(json_data)
    json_data.close()
    return data

def interactive(args):
    global CONFIRMATION
    args.networkid = raw_input("Enter network ID: ")
    args.flavorlist = raw_input("Enter CIDR list (include path): ")
    args.profile = raw_input("Enter CLI profile name: ")
    flavor_list = parse_flavor_list(args.flavorlist)
    for flavor in flavor_list.keys():
        #TODO: Make this work for interactive
        #TODO: Consider listing all prior flavors and asking if we want to clear them
        print flavor
        #print flavor['name']
        #print flavor['memory']
        #print flavor['disk']
        #print flavor['vcpu']
        #cidr = re.sub('[x]', args.cidrblock, cidr)
        #print "aws ec2 create-subnet --vpc-id %s --availability-zone %s --cidr-block %s --profile %s" % (args.networkid, args.zone, cidr, args.profile)
    CONFIRMATION = raw_input("Is this what you want to build? [YES/NO] ")

def main(args):
    # Detector not debugged yet
    # Determine if we have python-openstack installed

    print "### OpenStack Server Flavor Creator! ###"
    global CONFIRMATION

    # Check if interactive version or otherwise
    if not args.profile:
        interactive()
    else:
        CONFIRMATION="YES"

    try:
        flavor_list
    except NameError:
        flavor_list = parse_flavor_list(args.flavorlist)

    if (CONFIRMATION == "YES" or CONFIRMATION == "yes" or CONFIRMATION == "Y" or CONFIRMATION == "y"):
        print "Creating server flavors"
        #TODO: Consider listing all prior flavors and asking if we want to clear them
        for key,flavors in flavor_list.items():
            for flavor in flavors:
                # Ex: nova flavor-create c3.large auto 4096 16 2
                print "nova flavor-create %s auto %s %s %s" % (flavor['name'], flavor['memory'], flavor['disk'], flavor['vcpu'])
                command = "nova flavor-create %s auto %s %s %s" % (flavor['name'], flavor['memory'], flavor['disk'], flavor['vcpu'])
                process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                #output = process.communicate()[0] # Optional output
                #TODO: Capture output. Retry again if failure. Retry X times.
        print "### Done creating stuff! ###"
        return
    else:
        print "### Okay, canceling. ###"
        sys.exit(1) # Exiting

if __name__ == '__main__':
    args = parse_options()
    print args

    if len(sys.argv) == 1:
        main(args)
    elif len(sys.argv) == 7:
        main(args)
    else:
        print "ERROR: Wrong number of arguments."
        sys.exit(1)

    sys.exit()
