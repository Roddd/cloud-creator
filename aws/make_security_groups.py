#!/usr/bin/python
# Title         make-security-groups.py
# Description   Create network ACLs on AWS
# Author        I-Ming Chen <imchen@red5studios.com>
# Date          2014-09-26
# Version       0.0.1   
# Usage         ./make-security-groups.py
#               ./make-security-groups.py --vpcid vpc-123456 --config ../path/to/file.yml --profile prod-sa-east-1 [--dryrun] [--verbose]
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

GROUP_NAMES = {}
DRYRUN="0" #NYI
CONFIRMATION="no"

class GroupDoesNotExist(Exception):
    pass

def parse_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vpcid", help="VPC ID")
    parser.add_argument("--config", help="Yaml config of security group rules")
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

def preview_acl(acl_name, rules):
    print "We'll make X ACLs"
    print "We'll make Y Rules"

def create_sg(sg_name, rules, vpcid, profile):
    description = rules.pop("description", "")
    print "aws ec2 create-security-group --group-name %s --description '%s' --vpc-id %s --profile %s" % (sg_name, description, vpcid, profile)
    command = "aws ec2 create-security-group --group-name %s --description '%s' --vpc-id %s --profile %s" % (sg_name, description, vpcid, profile)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    sg_output = json.loads(output)
    sg_id = sg_output["GroupId"]
    # Everytime we make a security group, add the name and security group ID to the global GROUP_NAMES
    GROUP_NAMES.update({ sg_name: sg_id })
    # Remove default outbound rule
    remove_default_egress_rule(sg_id, profile)
    return sg_id

def remove_default_egress_rule(sg_id, profile):
    #aws ec2 revoke-security-group-egress --group-id sg-903004f8 --protocol -1 --port -1 --cidr 0.0.0.0/0
    print "aws ec2 revoke-security-group-egress --group-id %s --protocol -1 --port -1 --cidr 0.0.0.0/0 --profile %s" % (sg_id, profile)
    command = "aws ec2 revoke-security-group-egress --group-id %s --protocol -1 --port -1 --cidr 0.0.0.0/0 --profile %s" % (sg_id, profile)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output = process.communicate()[0]

def tag_sg(sg_name, sg_id, profile):
    print "aws ec2 create-tags --resources %s --tags Key=Name,Value=%s --profile %s" % (sg_id, sg_name, profile)
    command = "aws ec2 create-tags --resources %s --tags Key=Name,Value=%s --profile %s" % (sg_id, sg_name, profile)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output = process.communicate()[0] #Use this to verify it was successful

# The original idea was for this function to be atomic (one rule creation per call)
# However, adapting Nick's code means this is not possible since his for loop iterates through a set of rules before moving on
def create_sg_entry_set(sg_name, all_rules, profile):
    for name, id in GROUP_NAMES.items():
        if name == sg_name:
            sg_id = id
    # Process rules
    print "Creating set for " + str(sg_name) + ":"
    for protocol, all_rules_set in all_rules.iteritems():
        inbound_rules = all_rules_set.get("inbound", "")
        outbound_rules = all_rules_set.get("outbound", "")
        if inbound_rules:
            for rules, list_of_cidrs in inbound_rules.items():
                for i in list_of_cidrs:
                    port_range, cidr_or_source = parse_rules(rules, i, profile)
                    # Add rules to the security group
                    #aws ec2 authorize-security-group-ingress --group-id sg-903004f8 --protocol tcp --port 22-25 --cidr 203.0.113.0/24
                    #aws ec2 authorize-security-group-ingress --group-id sg-954fb4f0 --protocol tcp --port 3306 --source-group sg-954fb4f0 --profile prod-sa-east-1
                    print "aws ec2 authorize-security-group-ingress --group-id %s --protocol %s --port %s %s --profile %s" \
                          % (sg_id, protocol, port_range, cidr_or_source, profile)
                    command = "aws ec2 authorize-security-group-ingress --group-id %s --protocol %s --port %s %s --profile %s" \
                              % (sg_id, protocol, port_range, cidr_or_source, profile)
                    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                    output = process.communicate()[0]
        if outbound_rules:
            for rules, list_of_cidrs in outbound_rules.items():
                for i in list_of_cidrs:
                    port_range, cidr_or_source = parse_rules(rules, i, profile)
                    # Add rules to the security group
                    #aws ec2 authorize-security-group-egress --group-id sg-903004f8 --protocol tcp --port 22-25 --cidr 203.0.113.0/24
                    #aws ec2 authorize-security-group-egress --group-id sg-954fb4f0 --protocol tcp --port 3306 --source-group sg-954fb4f0 --profile prod-sa-east-1
                    print "aws ec2 authorize-security-group-egress --group-id %s --protocol %s --port %s %s --profile %s" \
                          % (sg_id, protocol, port_range, cidr_or_source, profile)
                    command = "aws ec2 authorize-security-group-egress --group-id %s --protocol %s --port %s %s --profile %s" \
                              % (sg_id, protocol, port_range, cidr_or_source, profile)
                    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                    output = process.communicate()[0]

def parse_rules(ports, cidr, profile):
    # Parse port range
    # If all ports...
    if ports == "all":
        port_range = -1
    # If single port...
    elif type(ports) == int:
        port_range = ports
    # If range of ports...
    else:
        try:
            port_start, port_end = ports.split("-")
        except ValueError, e:
            raise InvalidRangeError, "Error when trying to parse range: %s" % (ports)
        port_range = ports
    # Parse CIDR block
    # If the CIDR string has a dash, it's probably a reference to another security group and not a valid CIDR block
    if (re.search("-",str(cidr))):
        try:
            sg_id = find_group(cidr, profile)
        except GroupDoesNotExist, e:
            print "WARNING: Attempted use of non-existent group: ", e
        cidr_or_source_string = "--source-group %s" % (sg_id)
    else:
        cidr_or_source_string = "--cidr %s" % (cidr)
    return port_range, cidr_or_source_string


# Search in the config YML for security group name
def find_group(group_name, profile):
    for group, sg_id in GROUP_NAMES.items():
        if group == group_name:
            return sg_id
    raise GroupDoesNotExist("Group %s does not exist" % group_name)


# vv We may not need this at all? vv
# Search AWS for security group name 
#def get_all_sec_groups(profile):
    # Check if we've done this so we don't do it again
    # If the list of names is empty, fill up the list
    # We'll check AWS as well for any premade security groups
#    if not GROUP_NAMES:
#        print "aws ec2 describe-security-groups --profile %s" % (profile)
#        command = "aws ec2 describe-security-groups --profile %s" % (profile)
#        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
#        output = process.communicate()[0]
#        all_sec_groups = json.loads(output)
#        all_sec_groups_names = all_sec_groups["SecurityGroups"]
#        for sec_group in all_sec_groups_names:
#            GROUP_NAMES.append(sec_group["GroupName"])

def interactive(args):
    global CONFIRMATION
    args.vpcid = raw_input("Enter AWS VPC ID: ")
    args.config = raw_input("Enter config YML file (include path): ") 
    args.profile = raw_input("Enter AWS CLI profile name: ")
    #for acl_name, rules in config.get("network-acls").iteritems():
    print "I plan to preview something here with preview_acl()"
    CONFIRMATION = raw_input("Is this what you want to build? [YES/NO] ")

def main(args):
    # Detector not debugged yet
    # Determine if we have aws cli installed

    print "### AWS Security Group Creator! ###"
    global CONFIRMATION

    # Check if interactive version or otherwise
    if not args.profile:
        interactive(args)
    else:
        CONFIRMATION="YES"

    config = parse_config(args.config)

    if (CONFIRMATION == "YES" or CONFIRMATION == "yes" or CONFIRMATION == "Y" or CONFIRMATION == "y"):
        print "Creating security groups!"

        for sg_name, rules in config.get("sec-groups").iteritems():
            sg_id = create_sg(sg_name, rules, args.vpcid, args.profile)
            tag_sg(sg_name, sg_id, args.profile)
        # This is to ensure all groups are created before we add any self-referencing rules
        for sg_name, rules in config.get("sec-groups").iteritems():
            create_sg_entry_set(sg_name, rules, args.profile)

        print "### Done creating network ACLs! ###"
        return
    else:
        print "### Okay, canceling. ###"
        sys.exit(1) #Failure

if __name__ == '__main__':
    # Get settings
    args = parse_options()

    # Verify correct number of arguments before running
    if len(sys.argv) == 1:
        main(args)
    elif len(sys.argv) == 7:
        main(args)
    else:
        print "ERROR: Wrong number of arguments."
        sys.exit(1)
    sys.exit()
