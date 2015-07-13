#!/usr/bin/python
# Title         make-internet-gateway.py
# Description   Create VPC on AWS
# Author        I-Ming Chen <imchen@red5studios.com>
# Date          2014-09-22
# Version       0.0.1   
# Usage         ./make-internet-gateway.py
#               ./make-internet-gateway.py --vpcid vpc-123456 --profile prod-sa-east-1 [--dryrun] [--verbose]
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
    parser.add_argument("--vpcid", help="AWS VPC ID", nargs='?')
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
    args.vpcid = raw_input("Enter AWS VPC ID: ")
    args.profile = raw_input("Enter AWS CLI profile name: ")
    print "aws ec2 create-internet-gateway --profile %s" % (args.profile)
    CONFIRMATION = raw_input("Is this what you want to build? [YES/NO] ")

def main(args):
    # Detector not debugged yet
    # Determine if we have aws cli installed

    print "### AWS Internet Gateway Creator! ###"
    global CONFIRMATION

    # Check if interactive version or otherwise
    if not args.profile:
        interactive(args)
    else:
        CONFIRMATION="YES"

    if (CONFIRMATION == "YES" or CONFIRMATION == "yes" or CONFIRMATION == "Y" or CONFIRMATION == "y"):
        print "Creating AWS Internet Gateway!"
        print "aws ec2 create-internet-gateway --profile %s" % (args.profile)
        command = "aws ec2 create-internet-gateway --profile %s" % (args.profile)
        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
        output = process.communicate()[0] # Optional output
        igw_output = json.loads(output)
        igw_id = igw_output["InternetGateway"]["InternetGatewayId"]

        print "Attaching Internet Gateway to VPC!"
        print "aws ec2 attach-internet-gateway --internet-gateway-id %s --vpc-id %s --profile %s" % (igw_id, args.vpcid, args.profile)
        command = "aws ec2 attach-internet-gateway --internet-gateway-id %s --vpc-id %s --profile %s" % (igw_id, args.vpcid, args.profile)
        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
        output = process.communicate()[0] # Optional output

        print "### Done creating AWS Internet Gateway! ###"
        return igw_id
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
