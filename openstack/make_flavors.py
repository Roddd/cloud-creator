#!/usr/bin/python
# Title         make_flavors.py
# Description   Create flavors on OpenStack
# Author        I-Ming Chen <imchen@red5studios.com>
# Date          2015-07-26
# Version       0.1.0   
# Usage         ./make_flavors.py
#               ./make_flavors.py --flavorfile './path/to/json' [--dryrun] [--verbose]
# Notes         Requires Python OpenStack CLI installed
#============================================================================        

import sys
import argparse
import subprocess
import shlex
import readline
import json
import time

def parse_options():
    parser = argparse.ArgumentParser(description="Create flavors on OpenStack")
    parser.add_argument("-f", "--flavorfile", help="Flavor list (JSON)")
    #parser.add_argument("--maxretry", help="Maximum retry attempts (default: 3)", default=3, type=int)
    parser.add_argument("-d", "--dryrun", help="Output without doing any real calls", action="store_true")
    #parser.add_argument("-V", "--verbose", help="Increase output verbosity", action="store_true")
    args = parser.parse_args()
    if args.dryrun:
        print "Dryrun Mode On"
    #if args.verbose:
    #    print "Verbose Mode On"
    return args


def parseFlavorList(json_file):
    json_data = open(json_file)
    data = json.load(json_data)
    json_data.close()
    return data


# For interactive mode
def interactive(args):
    args.flavorfile = raw_input("Enter CIDR list (include path): ")
    args.flavorlist = parseFlavorList(args.flavorfile)
    print "-----------------------------------------------"
    print "| Name       | Memory (MB) | vCPU | Disk (GB) |"
    for key,flavors in args.flavorlist.items():
        for flavor in flavors:
            print "-----------------------------------------------"
            print "| " + flavor['name'].ljust(10) + " | " + flavor['memory'].rjust(11) + " | " \
                  + flavor['vcpu'].rjust(4) + " | " + flavor['disk'].rjust(9) + " |"
    print "-----------------------------------------------"
    args.confirm = raw_input("Is this what you want to build? [Yes/No] ").lower()
    if args.confirm == "no":
        sys.exit(0)
    #TODO: List flavors we are overwriting (query nova)
    #TODO: Confirm we want to replace existing flavors 


# Determine if OpenStack Nova installed
def programCheck():
    prog_check = subprocess.call(['which', 'nova'])
    if prog_check == 0:
        print "nova installation detected..."
    else:
        print "nova not found!"
        sys.exit(1)


# The heart of the program
def createFlavors(args):
    print "Creating server flavors..."
    for key,flavors in args.flavorlist.items():
        for flavor in flavors:
            # Ex: nova flavor-create c3.large auto 4096 16 2
            print "nova flavor-create %s auto %s %s %s" % (flavor['name'], flavor['memory'], flavor['disk'], flavor['vcpu'])
            command = "nova flavor-create %s auto %s %s %s" % (flavor['name'], flavor['memory'], flavor['disk'], flavor['vcpu'])
            if args.dryrun != True:
                process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
                #output = process.communicate()[0]
                #TODO: Capture output. Retry again if failure. Retry X times.
    print "Done creating flavors!"


def main(args):
    programCheck()

    # If non-interactive, flavorlist not parsed yet so we read it now
    try:
        args.flavorlist
    except AttributeError:
        args.flavorlist = parseFlavorList(args.flavorfile)

    createFlavors(args)


if __name__ == '__main__':
    args = parse_options()

    # Enable interactive mode
    if len(sys.argv) == 1:
        interactive(args)

    main(args)
    sys.exit()

