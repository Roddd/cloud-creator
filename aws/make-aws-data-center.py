#!/usr/bin/python
# Title         make-aws-data-center.py
# Description   Create a data center on AWS
# Author        I-Ming Chen <imchen@red5studios.com>
# Date          2014-09-26
# Version       0.0.3
# Usage         ./make-aws-data-center.py
#               ./make-aws-data-center.py --zone sa-east-1a --cidrblock 160 --config './path/to/yaml' --cidrlist './path/to/json1'
#                                         --elblist '.path/to/json2' --profile prod-sa-east-1 [--dryrun] [--verbose]
# Notes         Requires Python 2.7, AWS CLI installed
#============================================================================        

import sys
import argparse
import subprocess
import shlex
import readline
from make_vpc import main as making_vpc
from make_internet_gateway import main as making_internet_gateway
from make_subnets import main as making_subnets
from make_route_tables import main as making_route_tables
from make_security_groups import main as making_security_groups
from make_network_acls import main as making_network_acls
from make_elbs import main as making_elbs

DRYRUN="0" #NYI
CONFIRMATION="no"

def parse_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zone", help="Availability Zone", nargs='?')
    parser.add_argument("--cidrblock", help="Subnet CIDR Block (x in 10.x.y.z/16)", nargs='?')
    parser.add_argument("--config", help="Config YAML for security groups and ACLs", nargs='?')
    parser.add_argument("--cidrlist", help="Config JSON listing CIDRs and names", nargs='?')
    parser.add_argument("--elblist", help="Config JSON listing ELBs", nargs='?')
    parser.add_argument("--profile", help="AWS CLI Profile", nargs='?')
    parser.add_argument("--dryrun", help="output without doing any real calls", action="store_true")
    parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
    args = parser.parse_args()
    if args.dryrun:
        print "Make Subnets: Dryrun Mode On"
    if args.verbose:
        print "Make Subnets: Verbose Mode On"
    return args

def interactive(args):
    global CONFIRMATION
    args.zone = raw_input("Enter availability zone (e.g. us-west-1a): ")
    args.cidrblock = raw_input("Enter regional VPC subnet (x in 10.x.y.z/16): ")
    args.config = raw_input("Enter security config YAML file (include path): ")
    args.cidrlist = raw_input("Enter CIDR config JSON file (include path): ")
    args.elblist = raw_input("Enter ELB config JSON file (include path): ")
    args.profile = raw_input("Enter your AWS CLI profile name: ")
    print "AWS Data Center in %s in the 10.%s.0.0/16 subnet" % (args.zone, args.cidrblock)
    CONFIRMATION = raw_input("Is this what you want to build? [YES/NO] ")

def main(args):
    # Detector not debugged yet
    # Determine if we have aws cli installed

    print "====================="
    print "AWS Data Center Creator!"
    global CONFIRMATION

    # Check if interactive version or otherwise
    if not args.profile:
        interactive(args)
    else:
        CONFIRMATION="YES"

    if (CONFIRMATION == "YES" or CONFIRMATION == "yes" or CONFIRMATION == "Y" or CONFIRMATION == "y"):
        print "Starting process. Go get coffee. This takes around 35 minutes..."

        # Call all the actors here
        args.vpcid = making_vpc(args)
        args.igwid = making_internet_gateway(args)
        making_subnets(args)
        making_route_tables(args)
        making_security_groups(args)
        making_network_acls(args)
        making_elbs(args)

        print "### Hey, everybody! We're going to get laid! ###"
        print "====================="
        sys.exit(0) #Success
    else:
        print "Okay, canceling."
        print "====================="
        sys.exit(1) #Failure

    sys.exit()

if __name__ == '__main__':
    args = parse_options()

    if len(sys.argv) == 1:
        main(args)
    elif len(sys.argv) == 11:
        main(args)
    else:
        print "ERROR: Wrong number of arguments."
        sys.exit(1)
