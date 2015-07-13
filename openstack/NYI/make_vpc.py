#!/usr/bin/python
# Title         make-tenent.py
# Description   Create a tenent on OpenStack
# Author        I-Ming Chen <imchen@red5studios.com>
# Date          2014-12-03
# Version       0.0.1   
# Usage         ./make-tenent.py
#               ./make-tenent.py --cidrblock 160 --profile prod-sa-east-1 [--dryrun] [--verbose]
# Notes         Requires AWS CLI installed
#============================================================================        

import sys
import argparse
import subprocess
import shlex
import readline
import json

DRYRUN="0" #NYI
CONFIRMATION="no"

#Output should look like:
#aws ec2 create-vpc --cidr-block 10.0.0.0/16

def parse_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cidrblock", help="Subnet CIDR Block (x in 10.x.y.z/16)", nargs='?')
    parser.add_argument("--profile", help="OpenStack CLI Profile", nargs='?')
    parser.add_argument("--dryrun", help="output without doing any real calls", action="store_true")
    parser.add_argument("--verbose", help="increase output verbosity", action="store_true")
    args = parser.parse_args()

    if args.dryrun:
        print "Make Tenent: Dryrun Mode On"
    if args.verbose:
        print "Make Tenent: Verbose Mode On"

    return args

def interactive(args):
    global CONFIRMATION
    args.cidrblock = raw_input("Enter regional tenent subnet (x in 10.x.y.z/16): ")
    args.profile = raw_input("Enter OpenStack CLI profile name: ")
    print "aws ec2 create-vpc --cidr-block 10.%s.0.0/16 --profile %s" % (args.cidrblock, args.profile)
    CONFIRMATION = raw_input("Is this what you want to build? [YES/NO] ")

def main(args):
    # Detector not debugged yet
    # Determine if we have aws cli installed

    print "### OpenStack Tenent Creator! ###"
    global CONFIRMATION

    # Check if interactive version or otherwise
    if not args.profile:
        interactive(args)
    else:
        CONFIRMATION="YES"

    if (CONFIRMATION == "YES" or CONFIRMATION == "yes" or CONFIRMATION == "Y" or CONFIRMATION == "y"):
        print "Creating OpenStack Tenent!"
        print "aws ec2 create-vpc --cidr-block 10.%s.0.0/16 --profile %s" % (args.cidrblock, args.profile)
        command = "aws ec2 create-vpc --cidr-block 10.%s.0.0/16 --profile %s" % (args.cidrblock, args.profile)
        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
        output = process.communicate()[0] # Optional output
        vpc_output = json.loads(output)
        vpcid = vpc_output["Vpc"]["VpcId"]
        print "### Done creating AWS VPC! ###"
        return vpcid
    else:
        print "### Okay, canceling. ###"
        sys.exit(1) #Failure

if __name__ == '__main__':
    args = parse_options()

    if len(sys.argv) == 1:
        main(args)
    elif len(sys.argv) == 5:
        main(args)
    else:
        print "ERROR: Wrong number of arguments."
        sys.exit(1)

    sys.exit()
