#!/usr/bin/python
# Title         make-subnets.py
# Description   Create subnets on AWS
# Author        I-Ming Chen <imchen@red5studios.com>
# Date          2014-09-21
# Version       0.0.1   
# Usage         ./make-subnets.py
#               ./make-subnets.py --vpcid vpc-123456 --zone sa-east-1a --cidrblock 160 --cidrlist './path/to/json' --profile prod-sa-east-1 [--dryrun] [--verbose]
# Notes         Requires AWS CLI installed
#============================================================================        

import sys
import argparse
import subprocess
import shlex
import readline
import json
import re

DRYRUN="0" #NYI
CONFIRMATION="no"

#Output should look like:
#aws ec2 create-subnet --vpc-id vpc-4a74c92f --availability-zone sa-east-1a --cidr-block 10.160.0.0/24 --profile prod-sa-east-1

def parse_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vpcid", help="AWS VPC ID", nargs='?')
    parser.add_argument("--zone", help="Availability Zone", nargs='?')
    parser.add_argument("--cidrblock", help="Subnet CIDR Block (x in 10.x.y.z/16)", nargs='?')
    parser.add_argument("--cidrlist", help="CIDR/Name list (JSON)")
    parser.add_argument("--profile", help="AWS CLI Profile", nargs='?')
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
    args.vpcid = raw_input("Enter VPC-ID: ")
    args.zone = raw_input("Enter availability zone: ")
    args.cidrblock = raw_input("Enter regional VPC subnet (x in 10.x.y.z): ")
    args.cidrlist = raw_input("Enter CIDR list (include path): "
    args.profile = raw_input("Enter AWS CLI profile name: ")
    cidr_list = parse_cidr_list(args.cidrlist)
    for cidr in cidr_list.keys():
        cidr = re.sub('[x]', args.cidrblock, cidr)
        print "aws ec2 create-subnet --vpc-id %s --availability-zone %s --cidr-block %s --profile %s" % (args.vpcid, args.zone, cidr, args.profile)
    CONFIRMATION = raw_input("Is this what you want to build? [YES/NO] ")

def main(args):
    # Detector not debugged yet
    # Determine if we have aws cli installed

    print "### AWS Subnet Creator! ###"
    global CONFIRMATION

    # Check if interactive version or otherwise
    if not args.profile:
        interactive()
    else:
        CONFIRMATION="YES"

    if not cidr_list:
        cidr_list = parse_cidr_list(args.cidrlist)

    if (CONFIRMATION == "YES" or CONFIRMATION == "yes" or CONFIRMATION == "Y" or CONFIRMATION == "y"):
        print "Creating AWS subnets!"
        for cidr, sn_name in cidr_list.items():
            cidr = re.sub('[x]', args.cidrblock, cidr)
            print "aws ec2 create-subnet --vpc-id %s --availability-zone %s --cidr-block %s --profile %s" % (args.vpcid, args.zone, cidr, args.profile)
            command = "aws ec2 create-subnet --vpc-id %s --availability-zone %s --cidr-block %s --profile %s" % (args.vpcid, args.zone, cidr, args.profile)
            process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
            output = process.communicate()[0] # Optional output
            subnet_output = json.loads(output)
            subnet_id = subnet_output["Subnet"]["SubnetId"]

            print "aws ec2 create-tags --resources %s --tags 'Key=Name,Value=%s' --profile %s" % (subnet_id, sn_name, args.profile)
            command = "aws ec2 create-tags --resources %s --tags 'Key=Name,Value=%s' --profile %s" % (subnet_id, sn_name, args.profile)
            process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
            output = process.communicate()[0] #Use this to verify it was successful
        print "### Done creating AWS subnets! ###"
        return
    else:
        print "### Okay, canceling. ###"
        sys.exit(1) #Failure

if __name__ == '__main__':
    args = parse_options()

    if len(sys.argv) == 1:
        main(args)
    elif len(sys.argv) == 11:
        main(args)
    else:
        print "ERROR: Wrong number of arguments."
        sys.exit(1)

    sys.exit()
