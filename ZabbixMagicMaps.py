from pyzabbix import ZabbixAPI, ZabbixAPIException
from ZabbixUtils import *
import csv
import os
import datetime
import calendar

zabbixuser = 'user'
zabbixpassword= 'password'

trigger1 = 'High ICMP ping response time'
trigger2 = 'High ICMP ping loss'
trigger3 = 'Unavailable by ICMP ping'
trigger1color = 'FF6F00'
trigger2color = 'FF6F00'
trigger3color = 'DD0000'

zapi = ZabbixAPI("https://zabbix.etexgroup.com", user=zabbixuser, password=zabbixpassword)
print('Enter the hostgroup for which you want to make a map, format, exact syntax needed')
my_hostgroup = input('')

my_hostgroup_obj = get_hostgroup_id(zapi,my_hostgroup)
hosts = get_hosts_from_hostgroup(zapi,my_hostgroup)
host_element_id_mapping = []
for index, host in enumerate(hosts[0]['hosts']):
    hostid = host['hostid']
    elementid = index + 2
    host_element_id_mapping.append((hostid, elementid))
#print(host_element_id_mapping)

map_elements = []
dummy_element = {"selementid": "1",
                                      "elements": [],
                                      "elementtype": "4",
                                      "iconid_off": "2",
                                      "x": 500,
                                      "y": 500,
                                      'label': 'Remove this after all links are corrected',
                                      'label_location': '-1'
                                     }


map_elements.append(dummy_element)
links = []
for host in host_element_id_mapping:
    map_element = {}
    map_element['selementid'] = host[1]
    map_element['elements'] = []
    element = {}
    element['hostid'] = host[0]
    map_element['elements'].append(element)
    map_element['elementtype'] = "0"
    map_element['iconid_off'] = '156'
    map_elements.append(map_element)
    #TODO ADD correct icons for switch,firewall AP

    link = {}
    link['selementid1'] = '1'
    link['selementid2'] = host[1]
    link['color'] = "00CC00"
    hostname = get_hostname_from_hostid(zapi,host[0])
    label = "{" + hostname + ":icmppingsec.avg(5m)}\r\n{" + hostname + ":icmppingloss.avg(5m)}"
    link['label'] = label

    link['linktriggers'] = []
    linktrigger1 = {}
    linktrigger1['triggerid'] = get_trigger_id(zapi,host,trigger1)
    linktrigger1['drawtype'] = '0'
    linktrigger1['color'] = 'FF6F00'
    link['linktriggers'].append(linktrigger1)

    linktrigger2 = {}
    linktrigger2['triggerid'] = get_trigger_id(zapi,host,trigger2)
    linktrigger2['drawtype'] = '0'
    linktrigger2['color'] = 'FF6F00'
    link['linktriggers'].append(linktrigger2)

    linktrigger3 = {}
    linktrigger3['triggerid'] = get_trigger_id(zapi,host,trigger3)
    linktrigger3['drawtype'] = '0'
    linktrigger3['color'] = 'DD0000'
    link['linktriggers'].append(linktrigger3)

    links.append(link)
#print(links)

new_map = zapi.map.create(name=my_hostgroup,
                          width="1920",
                          height="1080",
                          selements=map_elements,
                          links=links
                          )
