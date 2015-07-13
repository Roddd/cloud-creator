README
======
TODO:
Make AWS Data Center can create an entire AWS VPC from scratch. It is a set of python scripts that are completely
written into stand alone modules or to be run in a chain (such as with the master calling script).

Requirements
------------
* Python 2.7+
* Python-OpenStack Client

What It Does
------------
TODO:
* Make a Virtual Private Cloud
* Make an Internet Gateway
* Make Routing Tables
* Make Elastic Load Balancers
* Tags all the appropriate resources with a name
* Attaches or associates whatever it is suppose to be with

DONE:
* Make Subnets
* Make Security Groups

ALL OF BELOW IS TODO:
Usage
-----
To run the script, simple call (interactive mode):
```
make-aws-data-center.py
```
Or include all your variables (argument mode):
```
make-aws-data-center.py --zone sa-east-1a --cidrblock 160 --config './path/to/yaml' --cidrlist './path/to/json1' --elblist './path/to/json2' --profile prod-sa-east-1 
```
...where:
* zone = AWS availability zone
* cidrblock = x in 10.x.y.z/16
* config = YAML file containing security group and network ACL definitions and rules
* cidrlist = JSON file containing subnets and their names
* elblist = JSON file containing Elastic Load Balancers and settings
* profile = Your profile for AWS CLI

You can call each module individually in interactive or argument mode.

User Files
----------
You must provide properly formatted YAML and JSON files. If it's wrong or has bad syntax, the program will attempt to run it anyway. So... keep it well maintained.

Two files are included with this project: cidr.default.json and elb.default.json.
cidr.default.json describes the CIDR blocks used and the names associated with each subnet.
elb.default.json describes the ELBs in our own format. Resembles AWS ELB output but not the same.

TO DO
-----
* Implement --dryrun to simulate construction of a VPC
* Implement --verbose to be more verbose; helpful for debugging or understanding failures
* Better error handling when encountering bad data from user provided lists
* Better error handling when AWS reports something is wrong
* Better hand-off from one command to another (we don't check if AWS is done or not in most cases)
* Be able to run the script again and have it skip stuff already made, tell user it's there, and add things that are missing
* Fix code so it doesn't look like I was making it in a hurry (or at least treat objects like an object)

License
-------
Proprietary for Red 5 Studios, (C) 2014.
