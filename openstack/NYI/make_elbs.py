#!/usr/bin/python
# Title         make-elbs.py
# Description   Create Elastic Load Balancers on AWS
# Author        I-Ming Chen <imchen@red5studios.com>
# Date          2014-09-27
# Version       0.0.1
# Usage         ./make_elbs.py
#               ./make_elbs.py --zone sa-east-1a --elblist './path/to/json' --profile prod-sa-east-1 [--dryrun] [--verbose]
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

def parse_options():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zone", help="Availability Zone", nargs='?')
    parser.add_argument("--elblist", help="ELB list (JSON)")
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
    args.zone = raw_input("Enter availability zone: ")
    args.elblist = raw_input("Enter ELB list (include path): ")
    args.profile = raw_input("Enter AWS CLI profile name: ")
    CONFIRMATION = raw_input("Is this what you want to build? [YES/NO] ")

def main(args):
    # Detector not debugged yet
    # Determine if we have aws cli installed

    print "### AWS Elastic Load Balancer Creator! ###"
    global CONFIRMATION

    # Check if interactive version or otherwise
    if not args.profile:
        interactive(args)
    else:
        CONFIRMATION="YES"

    elb_list = parse_cidr_list(args.elblist)
    if not elb_list:
        print "ERROR: No ELB JSON list? WAT DO?"
        return

    # Map out subnets
    print "Mapping out subnets for this VPC..."
    command = "aws ec2 describe-subnets --profile %s" % (args.profile)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output = process.communicate()[0] # Optional output
    sn_output = json.loads(output)
    subnet_map = {}
    for subnets in sn_output["Subnets"]:
        subnet_map.update({subnets["Tags"][0]["Value"]: subnets["SubnetId"]})

    # Map out security groups
    print "Mapping out security groups for this VPC..."
    command = "aws ec2 describe-security-groups --profile %s" % (args.profile)
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    output = process.communicate()[0] # Optional output
    sg_output = json.loads(output)
    securitygroup_map = {}
    for securitygroups in sg_output["SecurityGroups"]:
        securitygroup_map.update({securitygroups["GroupName"]: securitygroups["GroupId"]})


    if (CONFIRMATION == "YES" or CONFIRMATION == "yes" or CONFIRMATION == "Y" or CONFIRMATION == "y"):
        print "Creating AWS ELBs!"
        for loadbalancer in elb_list["LoadBalancers"]:
            elb_name = loadbalancer["LBName"]
            sn_name = loadbalancer["Subnets"]
            sg_name = loadbalancer["SecurityGroups"]

            for sn_name_candidate, sn_id_candidate in subnet_map.items():
                if sn_name_candidate == sn_name:
                    sn_id = sn_id_candidate

            for sg_name_candidate, sg_id_candidate in securitygroup_map.items():
                if sg_name_candidate == sg_name:
                    sg_id = sg_id_candidate

            # Parse listener(s)
            listener_string = ""
            number_of_listeners = 0
            for listener in loadbalancer["Listeners"]:
                listener_string = "Protocol=" + str(listener["Protocol"]) + ","
                listener_string = listener_string + "LoadBalancerPort=" + str(listener["LoadBalancerPort"]) + ","
                listener_string = listener_string + "InstanceProtocol=" + str(listener["InstanceProtocol"]) + ","
                listener_string = listener_string + "InstancePort=" + str(listener["InstancePort"])
                if listener["Protocol"] == "HTTPS":
                    listener_string = listener_string + ",SSLCertificateId=" + str(listener["SSLCertificateId"])

                # Do ELBs right here? You call yourself a programmer?
                if number_of_listeners == 0:
                    # Parse health check
                    healthcheck_string = ""
                    for healthcheck in loadbalancer["HealthCheck"]:
                        healthcheck_string = "Target=" + str(healthcheck["Target"]) + ","
                        healthcheck_string = healthcheck_string + "Timeout=" + str(healthcheck["Timeout"]) + ","
                        healthcheck_string = healthcheck_string + "Interval=" + str(healthcheck["Interval"]) + ","
                        healthcheck_string = healthcheck_string + "UnhealthyThreshold=" + str(healthcheck["UnhealthyThreshold"]) + ","
                        healthcheck_string = healthcheck_string + "HealthyThreshold=" + str(healthcheck["HealthyThreshold"])

                    print "aws elb create-load-balancer --load-balancer-name '%s' --subnets %s --security-groups %s --listeners %s --profile %s" \
                          % (elb_name, sn_id, sg_id, listener_string, args.profile)
                    command = "aws elb create-load-balancer --load-balancer-name '%s' --subnets %s --security-groups %s --listeners %s --profile %s" \
                              % (elb_name, sn_id, sg_id, listener_string, args.profile)
                    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                    output = process.communicate()[0] # Optional output

                    print "aws elb configure-health-check --load-balancer-name '%s' --health-check %s --profile %s" \
                          % (elb_name, healthcheck_string, args.profile)
                    command = "aws elb configure-health-check --load-balancer-name '%s' --health-check %s --profile %s" \
                              % (elb_name, healthcheck_string, args.profile)
                    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                    output = process.communicate()[0] # Optional output
                elif number_of_listeners > 0:
                    print "  ELB %s already exists. Adding listener only:" % (elb_name)
                    print "aws elb create-load-balancer-listeners --load-balancer-name '%s' --listeners %s --profile %s" \
                          % (elb_name, listener_string, args.profile)
                    command = "aws elb create-load-balancer-listeners --load-balancer-name '%s' --listeners %s --profile %s" \
                              % (elb_name, listener_string, args.profile)
                    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                    output = process.communicate()[0] # Optional output
                number_of_listeners += 1

    else:
        print "### Okay, canceling. ###"
        sys.exit(1) #Failure

if __name__ == '__main__':
    args = parse_options()

    if len(sys.argv) == 1:
        main(args)
    elif len(sys.argv) == 7:
        main(args)
    else:
        print "ERROR: Wrong number of arguments."
        sys.exit(1)

    sys.exit()
