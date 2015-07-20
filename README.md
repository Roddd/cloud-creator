README
======
This tool is designed to create the core virtual cloud settings such as network setup, network rules, etc.

The OpenStack version is still a work-in-progress. The OpenStack scripts are still in flux because their python scripts are being deprecated in favor of an all-encompassing OpenStack common script (much like Amazon's AWS python script) instead of distinct projects. Ideally for our OpenStack scripts, we should import the libraries and call those functions instead of calling the distinct project scripts.

Much of the features in both AWS and OpenStack scripts are still not yet implemented.

Network/Subnet
--------------
This takes in a JSON file like:

{
  "1.x.3.4": "subnet-name"
}

where x is defined when you give it as an input at the command line.

Flavor
------
This is only for OpenStack if you have full admin control. This takes in a JSON file like:

{
  "flavors": [
    {
      "name": "t2.micro",
      "memory": "1024",
      "disk": "8",
      "vcpu": "1"
    }
  ]
}

Elastic Load Balancer
---------------------
This takes in a JSON file like this:

{
  "LoadBalancers": [
  {
    "LBName": "external-webapp-vpc01",
    "Subnets": "subnet-something",
    "SecurityGroups": "base",
    "Listeners": [
    {
      "Protocol": "HTTP",
      "LoadBalancerPort": "80",
      "InstanceProtocol": "HTTP",
      "InstancePort": "80"
    } ],
    "HealthCheck": [
    {
      "Target": "TCP:80",
      "Timeout": "5",
      "Interval": "30",
      "UnhealthyThreshold": "2",
      "HealthyThreshold": "2"
    } ]
  } ]
}

Security Groups/Network ACL
---------------------------
This takes in YAML file like this:

subnets:
  network: &network "10.1.0.0/16"###

  ## Alias for subnet
  subnet-name: &subnet-name "10.1.0.0/24"

sec-groups:
  base:
    description: "Base groups for every node"
    tcp:
      inbound:
        22: [*subnet-name]
      outbound:
        22: ["0.0.0.0/0"]
  anothergroup:
    description: "Hi, I am a description"
    tcp:
      inbound:
        22: ["base", "10.254.1.1/32"]
