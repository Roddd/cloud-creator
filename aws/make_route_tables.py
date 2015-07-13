#!/usr/bin/python
# Title         make-route-tables
# Description   Create route tables on AWS
# Author        I-Ming Chen <imchen@red5studios.com>
# Date          2014-09-21
# Version       0.0.1   
# Usage         ./make-route-tables.sh
#               ./make-route-tables.sh --vpcid vpc-123456 --igwid igw-654321 --profile prod-sa-east-1 [--dryrun] [--verbose]
# Notes         Requires AWS CLI installed
#============================================================================        

import sys
import subprocess
import argparse
import readline
import shlex
import json
import re

LIST_OF_INSIDE = { "0.0/24": "", "3.0/24": "", "4.0/22": "", "8.0/24": "", "9.0/24": "", "10.0/24": "", "11.0/24": "", "12.0/24": "" }
LIST_OF_OUTSIDE = { "128.0/20": "", "144.0/24": "", "145.0/24": "", "146.0/24": "", "255.0/24": "" }
LIST_OF_MYSQL = { "1.0/24": "" }
LIST_OF_ROUTE_TABLES = { "Outside Routing Table": LIST_OF_OUTSIDE, "MySQL Routing Table": LIST_OF_MYSQL }
DRYRUN="0" #NYI
CONFIRMATION="no"

#Output should look like:
#aws ec2 create-route-table --vpc-id $VPCID --profile $PROFILE

def parse_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vpcid", help="AWS VPC ID")
    parser.add_argument("--igwid", help="Internet Gateway ID")
    parser.add_argument("--profile", help="AWS CLI Profile")
    parser.add_argument("--dryrun", action="store_true", help="Dry run")
    parser.add_argument("--verbose", action="store_true", help="Verbose mode")
    args = parser.parse_args()
    if args.dryrun:
        print "Make Subnets: Dryrun Mode On"
    if args.verbose:
        print "Make Subnets: Verbose Mode On"
    return args

# Not used yet
def parse_cidr_list(json_file):
    json_data = open(json_file)
    data = json.load(json_data)
    json_data.close()
    return data

def interactive(args):
    global CONFIRMATION
    args.vpcid = raw_input("Enter VPC-ID: ")
    args.igwid = raw_input("Enter Internet Gateway ID: ")
    args.profile = raw_input("Enter AWS CLI profile name: ")
    for i in LIST_OF_ROUTE_TABLES:
        print "aws ec2 create-route-table --vpc-id %s --profile %s" % (args.vpcid, args.profile)
    CONFIRMATION = raw_input("Is this what you want to build? [YES/NO] ")

def main(args):
    # Detector not debugged yet
    # Determine if we have aws cli installed

    print "### AWS Route Table Creator! ###"
    global CONFIRMATION

    # Check if interactive version or otherwise
    if not args.profile:
        interactive(args)
    else:
        CONFIRMATION="YES"

    # Find internet gateway ID for later
    # Used for adding routes to routing tables
    if not args.igwid:
        command = "aws ec2 describe-internet-gateways --profile %s" % (args.profile)
        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
        output = process.communicate()[0]
        igw_data = json.loads(output)
        args.igwid = igw_data["InternetGateways"][0]["InternetGatewayId"]

    # Find subnets and put it in a dictionary
    # This for later when we want to associate subnets to a routing table
    command = "aws ec2 describe-subnets --profile %s" % (args.profile)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    subnets_data = json.loads(output)
    subnets_map = {}

    counter = 0
    for i in subnets_data["Subnets"]:
        cidrblock_from_json = subnets_data["Subnets"][counter]["CidrBlock"]
        subnetid_from_json = subnets_data["Subnets"][counter]["SubnetId"]
        subnets_map.update({cidrblock_from_json: subnetid_from_json})
        counter += 1

    # Now we pre-sort the subnets into appropriate groups for later
    for i, j in subnets_map.items():
        # You need to make it cycle through ALL the lists
        # This code can be further collapsed cuz it's pretty fucking awful
        for cidr in LIST_OF_INSIDE.keys():
            chomped_i = i.split(".")
            del chomped_i[0:2]
            if cidr.split(".") == chomped_i:
                LIST_OF_INSIDE[cidr] = j; # update existing entry
        for cidr in LIST_OF_OUTSIDE.keys():
            chomped_i = i.split(".")
            del chomped_i[0:2]
            if cidr.split(".") == chomped_i:
                LIST_OF_OUTSIDE[cidr] = j; # update existing entry
        for cidr in LIST_OF_MYSQL.keys():
            chomped_i = i.split(".")
            del chomped_i[0:2]
            if cidr.split(".") == chomped_i:
                LIST_OF_MYSQL[cidr] = j; # update existing entry

    # Verify existing route tables and find the Main Table
    # I believe one is created by default when a VPC is created and it is set to Main Table by default
    main_route_table_id = ""
    command = "aws ec2 describe-route-tables --profile %s" % (args.profile)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    route_tables = json.loads(output)
    for t in route_tables["RouteTables"]:
        for route_table_entry in t["Associations"]:
            if route_table_entry["Main"] == True:
                main_route_table_id = route_table_entry["RouteTableId"]

    if (CONFIRMATION == "YES" or CONFIRMATION == "yes" or CONFIRMATION == "Y" or CONFIRMATION == "y"):
        print "Creating Route Table!"
        # 1 Create Route Table
        # 2 Tag Route Table
        # 3 Add Route to Route Table
        # 4 Add Subnet to Route Table
        # Special case -- One Route Table already exists and it's the Main Table. We'll use it and then do all the other tables
        if main_route_table_id:
            print "Found a Main route table. Using it."
            print "aws ec2 create-tags --resources %s --tags 'Key=Name,Value=Inside Routing Table' --profile %s" % (main_route_table_id, args.profile)
            command = "aws ec2 create-tags --resources %s --tags 'Key=Name,Value=Inside Routing Table' --profile %s" % (main_route_table_id, args.profile)
            process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
            output = process.communicate()[0]
            # Now we associate the subnets to the routing tables
            for cidr, subnet_id in LIST_OF_INSIDE.items():
                print "aws ec2 associate-route-table --route-table-id %s --subnet-id %s --profile %s" % (main_route_table_id, subnet_id, args.profile)
                command = "aws ec2 associate-route-table --route-table-id %s --subnet-id %s --profile %s" % (main_route_table_id, subnet_id, args.profile)
                process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                output = process.communicate()[0]
        else:
            #create a main route table
            print "What are you doing here? Get off my lawn!"

        for route_table_name, list_of_cidrs in LIST_OF_ROUTE_TABLES.items():
            print "aws ec2 create-route-table --vpc-id %s --profile %s" % (args.vpcid, args.profile)
            command = "aws ec2 create-route-table --vpc-id %s --profile %s" % (args.vpcid, args.profile)
            process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
            output = process.communicate()[0]
            route_table = json.loads(output)
            route_table_id = route_table["RouteTable"]["RouteTableId"]

            command = "aws ec2 create-tags --resources %s --tags 'Key=Name,Value=%s' --profile %s" % (route_table_id, route_table_name, args.profile)
            process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
            output = process.communicate()[0]

            # Special case -- Outside Routing Table needs this route to the IGW created
            if route_table_name == "Outside Routing Table":
                print "aws ec2 create-route --route-table-id %s --destination-cidr-block 0.0.0.0/0 --gateway-id %s --profile %s" \
                      % (route_table_id, args.igwid, args.profile)
                command = "aws ec2 create-route --route-table-id %s --destination-cidr-block 0.0.0.0/0 --gateway-id %s --profile %s" \
                          % (route_table_id, args.igwid, args.profile)
                process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                output = process.communicate()[0]

            # Now we associate the subnets to the routing tables
            for cidr, subnet_id in list_of_cidrs.items():
                print "aws ec2 associate-route-table --route-table-id %s --subnet-id %s --profile %s" % (route_table_id, subnet_id, args.profile)
                command = "aws ec2 associate-route-table --route-table-id %s --subnet-id %s --profile %s" % (route_table_id, subnet_id, args.profile)
                process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                output = process.communicate()[0]

        print "### Done creating Route Table! ###"
        return
    else:
        print "### Okay, canceling. ###"
        sys.exit(1) #Failure

if __name__ == '__main__':
    # Get settings
    args = parse_options()

    if len(sys.argv) == 1:
        main(args)
    elif len(sys.argv) == 7:
        main(args)
    else:
        print "ERROR: Wrong number of arguments."
        sys.exit(1)
    sys.exit()
