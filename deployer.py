import sys, re
import xmlrpclib
import xml.dom.minidom
import XenAPI
from pprint import pprint
from API.web.logger import logger
from API.xen_sdk.xen_sdk import *
v = 'Value'

# Set hosts like {hostip:poolname}
hosts = {'10.200.100.184': 'xenserver0', '10.200.100.185': 'xenserver1', '': '', '': ''}
name = 'AVprobe'
username = 'root'
password = 'incapsula'
cpu = int(1)
ram = int(1)
disk_size =int(11)
number_of_nets = int(2)
first_net = 'eth0'
second_net = 'eth1'


for host, poolname in hosts.iteritems():
    url = 'http://' + host
    print url
    createVM = CreateVM(url=url, username=username, password=password, poolname=poolname, vmname=name, \
                        number_of_nets=number_of_nets, first_net=first_net, second_net=second_net, new_mem=ram, \
                        new_cpu=cpu, disk_size=disk_size)
    createVM.main()




