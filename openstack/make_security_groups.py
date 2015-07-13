#!/usr/bin/python
# Title         make_security_groups.py
# Description   Create security groups and rules on OpenStack
# Author        I-Ming Chen <imchen@red5studios.com>
# Date          2015-05-14
# Version       0.0.2
# Usage         ./make_security_groups.py
#               ./make_security_groups.py --provider OpenStack --networkid vpc-123456 --config ../path/to/file.yml --profile prod-sa-east-1 [--dryrun] [--verbose]
# Notes         Requires python OpenStack CLI installed
#               Work has started on making this script more generic by requiring the --provider switch
#============================================================================        

import re
import sys
import subprocess
import shlex
import argparse
import readline
import yaml
import json
import time

GROUP_NAMES = {}
DRYRUN="0" #NYI
CONFIRMATION="no"

class GroupDoesNotExist(Exception):
    pass

def parse_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", help="Provider (AWS/OpenStack)")
    parser.add_argument("--networkid", help="Network ID")
    parser.add_argument("--config", help="Yaml config of security group rules")
    parser.add_argument("--profile", help="AWS CLI Profile")
    parser.add_argument("--disable-acl", action="store_true", help="Disable acl output")
    parser.add_argument("--dryrun", action="store_true", help="Dry run")
    parser.add_argument("--verbose", action="store_true", help="Verbose mode")
    parser.add_argument("--delay", action="store_true", help"Add a delay between calls to OpenStack")
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
    # nova version
    #print "nova secgroup-create %s '%s'" % (sg_name, description)
    #command = "nova secgroup-create %s '%s'" % (sg_name, description)
    # neutron version
    print "neutron security-group-create %s --description '%s' -f json" % (sg_name, description)
    command = "neutron security-group-create %s --description '%s' -f json" % (sg_name, description)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    # OpenStack sticks in one line before the JSON output so we're trashing that first line
    trash, output = output.split("\n", 1)
    sg_output = json.loads(output)
    # OpenStack's default output is a table. We've changed it to JSON but the format is still different than AWS's
    # Here we are searching the JSON output for the security group ID
    key_found = 0
    sg_id = 0
    for eachdict in sg_output:
        for key,value in eachdict.iteritems():
            if key_found == 1:
                sg_id = value
                key_found = 0
            if value == "id":
                key_found = 1
    # Everytime we make a security group, add the name and security group ID to the global GROUP_NAMES, a quick
    # look up table
    GROUP_NAMES.update({ sg_name: sg_id })

    # Remove default outbound rule
    # This still exists in OpenStack, however, OpenStack creates 2 rules -- one for IPv4 and one for IPv6
    #remove_default_egress_rule(sg_id, profile)

    # Sleep timer in case queries are too fast -- This needs to be made into a configurable option
    #time.sleep(2)
    return sg_id

def remove_default_egress_rule(sg_id, profile):
    #aws ec2 revoke-security-group-egress --group-id sg-903004f8 --protocol -1 --port -1 --cidr 0.0.0.0/0
    print "aws ec2 revoke-security-group-egress --group-id %s --protocol -1 --port -1 --cidr 0.0.0.0/0 --profile %s" % (sg_id, profile)
    command = "aws ec2 revoke-security-group-egress --group-id %s --protocol -1 --port -1 --cidr 0.0.0.0/0 --profile %s" % (sg_id, profile)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output = process.communicate()[0]

# Only for AWS
def tag_sg(sg_name, sg_id, profile):
    print "aws ec2 create-tags --resources %s --tags Key=Name,Value=%s --profile %s" % (sg_id, sg_name, profile)
    command = "aws ec2 create-tags --resources %s --tags Key=Name,Value=%s --profile %s" % (sg_id, sg_name, profile)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output = process.communicate()[0] #Use this to verify it was successful

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
                    port_range_from, port_range_to, cidr_or_source_switch, cidr_or_source = parse_rules(rules, i, profile)
                    # Add rules to the security group
                    # nova version
                    #nova secgroup-add-rule SECURITY_GROUP_NAME_OR_ID tcp 22 22 0.0.0.0/0
                    #nova secgroup-add-group-rule --ip_proto tcp --from_port 22 --to_port 22 SECURITY_GROUP_NAME SOURCE_GROUP_NAME
                    #nova secgroup-add-rule SECURITY_GROUP_NAME_OR_ID icmp -1 -1 0.0.0.0/0
                    #if cidr_or_source_switch == "cidr":
                        #print "nova secgroup-add-rule %s %s %s %s %s" \
                        #      % (sg_id, protocol, port_range_from, port_range_to, cidr_or_source)
                        #command = "nova secgroup-add-rule %s %s %s %s %s" \
                        #          % (sg_id, protocol, port_range_from, port_range_to, cidr_or_source)
                        #process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                        #output = process.communicate()[0]
                    #else:
                        #print "nova secgroup-add-group-rule %s %s %s %s %s" \
                        #      % (sg_id, cidr_or_source, protocol, port_range_from, port_range_to)
                        #command = "nova secgroup-add-group-rule %s %s %s %s %s" \
                        #           % (sg_id, cidr_or_source, protocol, port_range_from, port_range_to)
                        #process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                        #output = process.communicate()[0]

                    # neutron version
                    #neutron security-group-rule-create SECURITY_GROUP_NAME_OR_ID --direction ingress --protocol tcp --port-range-min 22 --port-range-max 22 --remote-ip-prefix 0.0.0.0/0
                    #neutron security-group-rule-create SECURITY_GROUP_NAME_OR_ID --direction ingress --protocol tcp --port-range-min 22 --port-range-max 22 --remote-group-id inside-core
                    if (protocol == "icmp"):
                        print "neutron security-group-rule-create %s --direction ingress --protocol %s %s" \
                               % (sg_id, protocol, cidr_or_source)
                        command = "neutron security-group-rule-create %s --direction ingress --protocol %s %s" \
                                  % (sg_id, protocol, cidr_or_source)
                        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                        output = process.communicate()[0]
                    elif (protocol == -1):
                        protocol = "tcp"
                        print "neutron security-group-rule-create %s --direction ingress --protocol %s --port-range-min %s --port-range-max %s %s" \
                              % (sg_id, protocol, port_range_from, port_range_to, cidr_or_source)
                        command = "neutron security-group-rule-create %s --direction ingress --protocol %s --port-range-min %s --port-range-max %s %s" \
                                  % (sg_id, protocol, port_range_from, port_range_to, cidr_or_source)
                        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                        output = process.communicate()[0]
                    else:
                        print "neutron security-group-rule-create %s --direction ingress --protocol %s --port-range-min %s --port-range-max %s %s" \
                              % (sg_id, protocol, port_range_from, port_range_to, cidr_or_source)
                        command = "neutron security-group-rule-create %s --direction ingress --protocol %s --port-range-min %s --port-range-max %s %s" \
                                  % (sg_id, protocol, port_range_from, port_range_to, cidr_or_source)
                        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                        output = process.communicate()[0]

                    # Sleep timer in case queries are too fast
                    #time.sleep(3)
        if outbound_rules:
            for rules, list_of_cidrs in outbound_rules.items():
                for i in list_of_cidrs:
                    port_range_from, port_range_to, cidr_or_source_switch, cidr_or_source = parse_rules(rules, i, profile)
                    # Add rules to the security group
                    #neutron security-group-rule-create SECURITY_GROUP_NAME_OR_ID --direction egress --protocol tcp --port-range-min 22 --port-range-max 22 --remote-ip-prefix 0.0.0.0/0
                    if (protocol == -1 or protocol == "icmp"):
                        protocol = "icmp"
                        print "neutron security-group-rule-create %s --direction egress --protocol %s %s" \
                               % (sg_id, protocol, cidr_or_source)
                        command = "neutron security-group-rule-create %s --direction egress --protocol %s %s" \
                                  % (sg_id, protocol, cidr_or_source)
                        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                        output = process.communicate()[0]
                    else:
                        print "neutron security-group-rule-create %s --direction egress --protocol %s --port-range-min %s --port-range-max %s %s" \
                              % (sg_id, protocol, port_range_from, port_range_to, cidr_or_source)
                        command = "neutron security-group-rule-create %s --direction egress --protocol %s --port-range-min %s --port-range-max %s %s" \
                                  % (sg_id, protocol, port_range_from, port_range_to, cidr_or_source)
                        process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                        output = process.communicate()[0]
                    #Stupid nova secgroup below
                    #if cidr_or_source_switch == "cidr":
                    #    print "nova secgroup-add-rule %s %s %s %s %s" \
                    #          % (sg_id, protocol, port_range_from, port_range_to, cidr_or_source)
                    #    command = "nova secgroup-add-rule %s %s %s %s %s" \
                    #              % (sg_id, protocol, port_range_from, port_range_to, cidr_or_source)
                    #    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                    #output = process.communicate()[0]
                    #else:
                    #    print "nova secgroup-add-group-rule %s %s %s %s %s" \
                    #          % (sg_id, cidr_or_source, protocol, port_range_from, port_range_to)
                    #    command = "nova secgroup-add-group-rule %s %s %s %s %s" \
                    #               % (sg_id, cidr_or_source, protocol, port_range_from, port_range_to)
                    #    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)

                    # Sleep timer in case queries are too fast
                    #time.sleep(3)

# This has been modified to work with OpenStack's port arguments
def parse_rules(ports, cidr, profile):
    # Parse port range
    # If all ports...
    if ports == "all":
        #port_range = -1
        #TODO: Setting to -1 for "all ports" may not work for OpenStack. Please test again.
        #If this is true, perhaps set it from 1 to 65535 for port range. Default ranges can be "all"
        #but no documentation exists on how admins can add this
        port_range_from = -1
        port_range_to = -1
    # If single port...
    elif type(ports) == int:
        port_range_from = ports
        port_range_to = ports
    # If range of ports...
    else:
        try:
            port_start, port_end = ports.split("-")
        except ValueError, e:
            raise InvalidRangeError, "Error when trying to parse range: %s" % (ports)
        port_range_from = port_start
        port_range_to = port_end
    # Parse CIDR block
    # If the CIDR string has a dash, it's probably a reference to another security group and not a valid CIDR block
    # We attach the appropriate switch here, --remote-group-id vs --remote-ip-prefix, before we pass it back
    cidr_or_source_switch = "cidr"
    if (re.search("-",str(cidr))):
        try:
            sg_id = find_group(cidr, profile)
        except GroupDoesNotExist, e:
            print "WARNING: Attempted use of non-existent group: ", e
        # nova version; sg_id is not an "id"... it's the group's name.
        #cidr_or_source_string = "%s" % (sg_id)
        #cidr_or_source_switch = "source"
        # neutron version
        cidr_or_source_string = "--remote-group-id %s" % (sg_id)
    else:
        # nova version
        #cidr_or_source_string = "%s" % (cidr)
        #cidr_or_source_switch = "cidr"
        # neutron version
        cidr_or_source_string = "--remote-ip-prefix %s" % (cidr)
    return port_range_from, port_range_to, cidr_or_source_switch, cidr_or_source_string

# Search in the config YML for security group name
#TODO: Review this for OpenStack. Prefer to use UUID since names can conflict.
def find_group(group_name, profile):
    for group, sg_id in GROUP_NAMES.items():
        if group == group_name:
            #return sg_id
            #For nova -- piece of shit
            return group_name
    raise GroupDoesNotExist("Group %s does not exist" % group_name)


# Search AWS for security group name
#TODO: Fix this for OpenStack. We don't want to create a group if it already exists
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
#TODO: If we find a conflicting name, we should report this problem at the end of the run.

def interactive(args):
    global CONFIRMATION
    args.provider = raw_input("'AWS' or 'OpenStack'?: ")
    args.networkid = raw_input("Enter Tenant ID: ")
    args.config = raw_input("Enter config YML file (include path): ") 
    args.profile = raw_input("Enter OpenStack profile name: (NYI) ")
    #for acl_name, rules in config.get("network-acls").iteritems():
    print "I plan to preview something here with preview_acl(). Maybe."
    CONFIRMATION = raw_input("Is this what you want to build? [YES/NO] ")

def main(args):
    #TODO: Determine if we have python-openstack CLI installed

    print "### OpenStack Security Group Creator! ###"
    global CONFIRMATION

    # Check if interactive version or otherwise
    if not args.profile:
        interactive(args)
    else:
        CONFIRMATION="YES"

    config = parse_config(args.config)

    if (CONFIRMATION == "YES" or CONFIRMATION == "yes" or CONFIRMATION == "Y" or CONFIRMATION == "y" or CONFIRMATION == "Yes"):
        print "Creating security groups!"

        # We create all groups first and then populate with rules
        # This ensures any rules that reference other groups will work
        for sg_name, rules in config.get("sec-groups").iteritems():
            sg_id = create_sg(sg_name, rules, args.networkid, args.profile)
            #if provider == "AWS":
            #    tag_sg(sg_name, sg_id, args.profile)
        for sg_name, rules in config.get("sec-groups").iteritems():
            create_sg_entry_set(sg_name, rules, args.profile)

        print "### Done creating security groups! ###"
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
    elif len(sys.argv) == 9:
        main(args)
    else:
        print "ERROR: Wrong number of arguments."
        sys.exit(1)
    sys.exit()
