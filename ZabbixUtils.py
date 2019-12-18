from pyzabbix import ZabbixAPI, ZabbixAPIException
import csv
import os
import datetime
import calendar
from openpyxl import Workbook
from openpyxl import load_workbook

def check_make_hostgroup(zapi,hostgroup):
    hostgroup_lookup = zapi.hostgroup.get(filter={"name": hostgroup})
    if not hostgroup_lookup:
        # make hostgroup
        zapi.hostgroup.create(name=hostgroup)
        new_hostgroup = zapi.hostgroup.get(filter={"name": hostgroup})
        return new_hostgroup
    else:
        return hostgroup_lookup

def check_if_host_exists(zapi,hostname):
    hostname_lookup = zapi.host.get(filter={"host": hostname})
    if not hostname_lookup:
        return True
    else:
        #print(hostname + ' already exists in Zabbix')
        return False

def get_host_id(zapi,hostname):
    hostname_lookup = zapi.host.get(filter={"host": hostname})
    #print(hostname_lookup)
    if not hostname_lookup:
        return False
    else:
        return hostname_lookup[0]['hostid']

def get_host_id_from_ip(zapi,ip):
    ip_lookup = zapi.hostinterface.get(filter={"ip": ip})
    if not ip_lookup:
        return False
    else:
        return ip_lookup[0]['hostid']

def get_ip_from_host_id(zapi,hostid):
    ip_lookup = zapi.hostinterface.get(filter={"hostid": hostid})
    if not ip_lookup:
        return False
    else:
        return ip_lookup[0]['ip']

def check_if_ip_exists(zapi,ip):
    ip_lookup = zapi.hostinterface.get(filter={"ip": ip})
    if not ip_lookup:
        print('IP is nog vrij')
        return True
    else:
        print('IP already in use')
        hostid = ip_lookup[0]['hostid']
        host_obj = zapi.host.get(filter={"hostid": hostid})
        existing_host = host_obj[0]['host']
        print('IP' + ip + ' is already assigned to host: ' + existing_host + "...")
        print('please double check in Zabbix if correct')
        return False

def make_new_host(zapi,hostname,ip,country_groupid,sitecode_groupid,host_group_id):
    new_host = zapi.host.create(host=hostname,
                                groups=[{
                                    "groupid": country_groupid
                                },{
                                    "groupid": sitecode_groupid
                                },{
                                    "groupid": host_group_id
                                }],
                                interfaces=[{
                                    'main': '1',
                                    'type': '2',
                                    'useip': '1',
                                    'ip': ip,
                                    'dns': '',
                                    'port': '161',
                                    'bulk': '1'
                                }]
                                )
    return new_host

def get_template_id(zapi,template_name):
    template_id_lookup = zapi.template.get(filter={"host": template_name})
    template_id = template_id_lookup[0]['templateid']
    return template_id

def get_hostgroup_id(zapi,hostgroup_name):
    hostgroup_id_lookup = zapi.hostgroup.get(filter={"name": hostgroup_name})
    hostgroup_id = hostgroup_id_lookup[0]['groupid']
    return hostgroup_id

def renderCsvToDict(filename):
    dir_path = os.path.dirname(os.path.realpath(__file__)) + '\\Input'
    file_path = os.path.join(dir_path, filename)
    reader = csv.DictReader(open(file_path))
    device_list = []

    print('importing device parameters from csv file, can take some time....')
    for device in reader:
        #print(device['name'] + ' imported')
        new_device = {
            'name': device['name'],
            'ip': device['ip'],
            'host_group': device['name'][:2] + "/" + device['name'][:5],
            'country': device['name'][:2],
            'type': device['type'],
            'host_group_id': get_hostgroup_id('Discovered hosts')
        }
        device_list.append(new_device)
    return device_list

def change_host_ip(zapi,hostname, ip):
    host_id = get_host_id(hostname)
    hostinterface = zapi.hostinterface.get(filter={"hostid": host_id})
    interface_id = hostinterface[0]['interfaceid']
    hostinterface = zapi.hostinterface.update({"interfaceid":interface_id, "ip":ip})
    return hostinterface

def check_if_host_ip_correct(zapi,hostname, ip_fmg):
    if check_if_host_exists(hostname) == False:       #als de host al bestaat doe verder
        host_id = get_host_id(hostname)
        ip_zabbix = get_ip_from_host_id(host_id)
        if ip_zabbix == ip_fmg:
            print('zabbix en fmg IP gelijk voor ' + hostname)
            return False
        else:
            return True             #dus zabbix IP is verschillend en we moeten dit wijzigen
        #print(ip_zabbix)
        #print(ip_fmg)
    return

def get_problems(zapi,host_group,month,year):
    print('Getting data from Zabbix...')
    problems = []
    time_from = datetime.datetime(year, month, 1, 0, 0).timestamp()
    last_day_of_month = calendar.monthrange(year, month)[1]
    time_till = datetime.datetime(year, month, last_day_of_month, 23, 59).timestamp()

    imported_hosts = zapi.hostgroup.get(selectHosts=host_group,
                                        filter={"name": host_group})
    # print(imported_hosts)

    for imported_host in imported_hosts[0]['hosts']:  # this gets all the hosts and host IDs and puts it in hosts
        #print(imported_host)
        problem = {}
        hostid = imported_host['hostid']
        problem['hostid'] = hostid

        host_obj = zapi.host.get(filter={"hostid": problem['hostid']})
        hostname = host_obj[0]['host']
        problem["hostname"] = hostname

        trigger = {}
        trigger_obj = zapi.trigger.get(hostids=hostid,
                                       filter={'description': 'Unavailable by ICMP ping'})
        triggerid = trigger_obj[0]['triggerid']
        trigger['triggerid'] = triggerid
        triggername = trigger_obj[0]['description']
        trigger['triggername'] = triggername

        events = []
        event_objs = zapi.event.get(objectids=triggerid,  # = trigger ID van CN001 icmp
                                    time_from=time_from,
                                    time_till=time_till,
                                    sortfield=["clock", "eventid"],
                                    # value= "1"
                                    # countOutput= 'True'
                                    )
        for event_obj in event_objs:
            if event_obj['value'] == '1':
                event = {}
                r_eventid = event_obj['r_eventid']
                eventid = event_obj['eventid']
                r_event = zapi.event.get(eventids=r_eventid)
                r_event = r_event[0]
                event_counter = int(event_obj['clock'])
                r_event_counter = int(r_event['clock'])
                duration = str(r_event_counter - event_counter)
                event["duration"] = duration
                event["start_time"] = event_counter
                event["end_time"] = r_event_counter
                event["eventid"] = eventid
                output = problem["hostname"] + " had an event: " + event['eventid'] + " that had duration: " + duration
                events.append(event)

        trigger['events'] = events
        problem['trigger'] = trigger
        problems.append(problem)
    return problems


def make_report(problems, hostgroup, month, year):
    print('Making report...')

    workbook = load_workbook(filename="filter_header.xlsx")
    sheet = workbook.active
    row = 2
    for problem in problems:
        if problem['trigger']['events']:
            for event in problem['trigger']['events']:
                sheet["A" + str(row)] = problem['hostname']
                sheet["B" + str(row)] = problem['trigger']['triggername']
                sheet["C" + str(row)] = event['duration']
                sheet["D" + str(row)] = event['start_time']
                sheet["E" + str(row)] = event['end_time']
                row +=1
    filename = 'Report_' + hostgroup[:3] + '_' + hostgroup[4:] + '_' + month + '_' + year + '.xlsx'
    dir_path = os.path.dirname(os.path.realpath(__file__)) + '\\Output\\Reports'
    file_path = os.path.join(dir_path, filename)
    workbook.save(filename=file_path)

def get_hosts_from_hostgroup(zapi,hostgroup):
    hosts = zapi.hostgroup.get(selectHosts=hostgroup,
                       filter={"name": hostgroup})
    return hosts

def get_hostname_from_hostid(zapi,hostid):
    hostname_lookup = zapi.host.get(filter={"hostid": hostid})
    hostname = hostname_lookup[0]['host']
    return hostname

def get_trigger_id(zapi,hostid,triggername):
    trigger_obj = zapi.trigger.get(hostids=hostid,
                                   filter={'description': triggername})
    trigger_id = trigger_obj[0]['triggerid']
    return trigger_id

def check_if_member_of_hostgroup(zapi,hostname,hostgroup):
    x = zapi.host.get(filter={"host": hostname},
                      selectGroups=hostgroup)
    hostgroup_id = get_hostgroup_id(zapi,hostgroup)
    return x
