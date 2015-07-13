#!/usr/bin/python
# Title         make-network-acls.py
# Description   Create network ACLs on AWS
# Author        I-Ming Chen <imchen@red5studios.com>
# Date          2014-09-22
# Version       0.0.1   
# Usage         ./make-network-acls.py
#               ./make-network-acls.py --vpcid vpc-123456 --config ../path/to/file.yml --cidrlist ../path/to/json --profile prod-sa-east-1 [--dryrun] [--verbose]
# Notes         Requires AWS CLI installed
#============================================================================        

import re
import sys
import subprocess
import shlex
import argparse
import readline
import yaml
import json

DRYRUN="0" #NYI
CONFIRMATION="no"

def parse_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vpcid", help="VPC ID")
    parser.add_argument("--config", help="Yaml config of security group rules")
    parser.add_argument("--cidrlist", help="CIDR/Name list (JSON)")
    parser.add_argument("--profile", help="AWS CLI Profile")
    parser.add_argument("--disable-acl", action="store_true", help="Disable acl output")
    parser.add_argument("--dryrun", action="store_true", help="Dry run")
    parser.add_argument("--verbose", action="store_true", help="Verbose mode")
    args = parser.parse_args()
    return args

def parse_config(config):
    content = None
    with file(config, 'r') as fp:
        content = yaml.load(fp)
    return content

def parse_cidr_list(json_file):
    json_data = open(json_file)
    data = json.load(json_data)
    json_data.close()
    return data

def preview_acl(acl_name, rules):
    print "We'll make X ACLs"
    print "We'll make Y Rules"

def create_acl(cidr_list, acl_name, vpcid, profile, joined_dict):
    print "aws ec2 create-network-acl --vpc-id %s --profile %s" % (vpcid, profile)
    command = "aws ec2 create-network-acl --vpc-id %s --profile %s" % (vpcid, profile)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    network_acl = json.loads(output)
    network_acl_id = network_acl["NetworkAcl"]["NetworkAclId"]

    acl_name_check = acl_name.split("-")
    del acl_name_check[1]
    for subnets, cidr_names in cidr_list.items():
        if acl_name_check == cidr_names.split("-"):
            # Subnet now needs to match the joined dictionary
            # Chop off the first 2 parts of the string which is "10.x" or where x is the regional subnet
            # Basically comparing the tail end of the CIDR block: "1.0/24" vs "1.0/24"
            for key, value in joined_dict.items():
                candidate = key.split(".")
                del candidate[0:2]
                subnet_master = subnets.split(".")
                del subnet_master[0:2]
                if subnet_master == candidate:
                    network_acl_association_id = value
                    # Reassociate Network ACLs with correct subnets since we just created the ACLs
                    # aws ec2 replace-network-acl-association --association-id aclassoc-e5b95c8c --network-acl-id acl-5fb85d36
                    print "aws ec2 replace-network-acl-association --association-id %s --network-acl-id %s --profile %s" % (network_acl_association_id, network_acl_id, profile)
                    command = "aws ec2 replace-network-acl-association --association-id %s --network-acl-id %s --profile %s" % (network_acl_association_id, network_acl_id, profile)
                    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                    output = process.communicate()[0]
                    # We put the re-association deep inside the loop in the event that multiple subnets need to be reassigned to an ACL

    return network_acl_id

def tag_acl(acl_name, network_acl_id, profile):
    print "aws ec2 create-tags --resources %s --tags Key=Name,Value=%s --profile %s" % (network_acl_id, acl_name, profile)
    command = "aws ec2 create-tags --resources %s --tags Key=Name,Value=%s --profile %s" % (network_acl_id, acl_name, profile)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output = process.communicate()[0] #Use this to verify it was successful

# The original idea was for this function to be atomic (one rule creation per call)
# However, adapting Nick's code means this is not possible since his for loop iterates through a set of rules before moving on
def create_acl_entry_set(acl_name, network_acl_id, rules, profile):
    # Process rules
    start_rule_numbers = {
        "icmp": 200,
        "tcp": 500,
        "udp": 600,
        "all": 100
    }
    print "Creating set for " + str(acl_name) + ":"
    for protocol, acl in rules.iteritems():
        if "inbound" in acl:
            rule_num = start_rule_numbers[protocol]
            rule_action = "allow"
            traffic_flow = "ingress"

            rules = acl.get("inbound")
            for rule_hash in rules:
                for rule, cidr in sorted(rule_hash.iteritems()):
                    # Find port ranges
                    if (re.search("-",str(rule))):
                        ports = str(rule).split("-")
                        port_start = ports[0]
                        port_end = ports[1]
                        port_range = "--port-range From=%s,To=%s" % (port_start, port_end)
                    else:
                        port_start = rule
                        port_end = rule
                        port_range = "--port-range From=%s,To=%s" % (port_start, port_end)
                    cidr_block = cidr
                    if protocol == "icmp":
                        if rule == "all":
                            port_range = "--icmp-type-code Type=-1,Code=-1"
                    # aws ec2 create-network-acl-entry --network-acl-id acl-5fb85d36 --rule-number 100 --protocol udp \
                    # --rule-action allow --ingress --cidr-block 0.0.0.0/0 --port-range From=53,To=53
                    print "aws ec2 create-network-acl-entry --network-acl-id %s --rule-number %s --protocol %s --rule-action %s --%s --cidr-block %s %s --profile %s" \
                           % (network_acl_id, rule_num, protocol, rule_action, traffic_flow, cidr_block, port_range, profile)
                    command = "aws ec2 create-network-acl-entry --network-acl-id %s --rule-number %s --protocol %s \
                              --rule-action %s --%s --cidr-block %s %s --profile %s" \
                              % (network_acl_id, rule_num, protocol, rule_action, traffic_flow, cidr_block, port_range, profile)
                    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                    output = process.communicate()[0]
                    rule_num += 1

        if "outbound" in acl:
            rule_num = start_rule_numbers[protocol]
            rule_action = "allow"
            traffic_flow = "egress"

            rules = acl.get("outbound")
            for rule_hash in rules:
                for rule, cidr in sorted(rule_hash.iteritems()):
                    # Find port ranges
                    if (re.search("-",str(rule))):
                        ports = str(rule).split("-")
                        port_start = ports[0]
                        port_end = ports[1]
                    else:
                        port_start = rule
                        port_end = rule
                    cidr_block = cidr
                    if protocol == "icmp":
                        if rule == "all":
                            port_range = "--icmp-type-code Type=-1,Code=-1"
                    print "aws ec2 create-network-acl-entry --network-acl-id %s --rule-number %s --protocol %s --rule-action %s --%s --cidr-block %s %s --profile %s" \
                           % (network_acl_id, rule_num, protocol, rule_action, traffic_flow, cidr_block, port_range, profile)
                    command = "aws ec2 create-network-acl-entry --network-acl-id %s --rule-number %s --protocol %s \
                              --rule-action %s --%s --cidr-block %s --port-range From=%s,To=%s --profile %s" \
                              % (network_acl_id, rule_num, protocol, rule_action, traffic_flow, cidr_block, port_start, port_end, profile)
                    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                    output = process.communicate()[0]
                    rule_num += 1

def interactive(args):
    global CONFIRMATION
    args.vpcid = raw_input("Enter VPC-ID: ")
    args.config = raw_input("Enter config YML file (include path): ") 
    args.profile = raw_input("Enter AWS CLI profile name: ")
    #for acl_name, rules in config.get("network-acls").iteritems():
    print "I plan to preview something here with preview_acl()"
    CONFIRMATION = raw_input("Is this what you want to build? [YES/NO] ")

def main(args):
    # Detector not debugged yet
    # Determine if we have aws cli installed

    print "====================="
    print "AWS Network ACL Creator!"
    global CONFIRMATION

    # Check if interactive version or otherwise
    if not args.profile:
        interactive(args)
    else:
        CONFIRMATION="YES"

    config = parse_config(args.config)
    cidr_list = parse_cidr_list(args.cidrlist)

    # Subnets default to the primary ACL when created. We will need to reassociate them.
    # In order to do that we must map subnets (CIDR) to the network association ID so we can bind them to the correct network ACL
    # Let's map out subnet CIDR and IDs first
    command = "aws ec2 describe-subnets --profile %s" % (args.profile)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    subnets_struct = json.loads(output)
    subnets_dict = {}
    for subnets_entry in subnets_struct["Subnets"]:
        subnets_dict.update({subnets_entry["SubnetId"]:subnets_entry["CidrBlock"]})

    # Let's map out the network ACLs and how they are associated with subnets next
    command = "aws ec2 describe-network-acls --profile %s" % (args.profile)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    network_acl_struct = json.loads(output)
    network_acl_dict = {}
    for associations in network_acl_struct["NetworkAcls"]:
        for subnets_assocs in associations["Associations"]:
            network_acl_dict.update({subnets_assocs["SubnetId"]:subnets_assocs["NetworkAclAssociationId"]})

    joined_dict = {}
    for subnets_key, subnets_value in subnets_dict.items():
        for network_acl_key, network_acl_value in network_acl_dict.items():
            if subnets_key == network_acl_key:
                joined_dict.update({subnets_value:network_acl_value})

    if (CONFIRMATION == "YES" or CONFIRMATION == "yes" or CONFIRMATION == "Y" or CONFIRMATION == "y"):
        print "Creating network ACLs!"
        for acl_name, rules in config.get("network-acls").iteritems():
            network_acl_id = create_acl(cidr_list, acl_name, args.vpcid, args.profile, joined_dict)
            tag_acl(acl_name, network_acl_id, args.profile)
            create_acl_entry_set(acl_name, network_acl_id, rules, args.profile)
        print "### Done creating network ACLs! ###"
        return
    else:
        print "Okay, canceling."
        sys.exit(1) #Failure

if __name__ == '__main__':
    # Get settings
    args = parse_options()

    # Verify correct number of arguments before running
    if len(sys.argv) == 1:
        main(args)
    elif len(sys.argv) == 9:
        main(args)
    else:
        print "ERROR: Wrong number of arguments."
        sys.exit(1)
    sys.exit()
