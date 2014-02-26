#!/usr/bin/python

import urllib
import os
import sys
import xml.dom.minidom
import re
import base64
import hmac
import hashlib
import httplib
import time
import marvin
import json
import urllib2
import logging

from marvin.cloudstackConnection import cloudConnection
from marvin.cloudstackException import cloudstackAPIException
from marvin.cloudstackAPI import *
from marvin import cloudstackAPI


def getApiKeys(host, username, password, domain):
  if domain == None :
    loginparams = urllib.urlencode({'username': username, 'password': password, 'command': 'login'})
  else:
    loginparams = urllib.urlencode({'username': username, 'password': password, 'domain': domain, 'command': 'login'})
  headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
  connection = httplib.HTTPConnection(host, 8080)
  request = connection.request("POST", "/client/api?login", loginparams, headers);
  resp = connection.getresponse()
  cookies = resp.getheader('Set-cookie')
  matchObj = re.match( r'JSESSIONID=(.*);.*', cookies, re.M|re.I)
  sessionId = matchObj.group(1);

  dom = xml.dom.minidom.parseString(resp.read())
  if len(dom.getElementsByTagName('sessionkey')) == 0:
      print "Login failed"
      sys.exit(-1)

  sessionKey = dom.getElementsByTagName('sessionkey')[0].firstChild.data
#  userId = dom.getElementsByTagName('userid')[0].firstChild.data
  userId = 2

  print "# Connected with user %s (%s) with sessionKey %s" % (username, userId, sessionKey)

  params = urllib.urlencode({'command':'listUsers', 'id':userId, 'sessionkey':sessionKey})
  headers = {"Cookie" : "JSESSIONID=%s" % sessionId}
  request = connection.request("GET", "/client/api?%s" % params, None, headers);
  resp = connection.getresponse()
  dom = xml.dom.minidom.parseString(resp.read())
  if dom.getElementsByTagName('apikey') :
    apiKey = dom.getElementsByTagName('apikey')[0].firstChild.data
    secretKey = dom.getElementsByTagName('secretkey')[0].firstChild.data
  else:
    print "# Account has no apikey, executing registerUserKeys"
    params = urllib.urlencode({'command':'registerUserKeys', 'id':userId, 'sessionkey':sessionKey})
    headers = {"Cookie" : "JSESSIONID=%s" % sessionId}
    request = connection.request("GET", "/client/api?%s" % params, None, headers);
    resp = connection.getresponse()
    dom = xml.dom.minidom.parseString(resp.read())
    apiKey = dom.getElementsByTagName('apikey')[0].firstChild.data
    secretKey = dom.getElementsByTagName('secretkey')[0].firstChild.data

  connection.close()
  return (apiKey, secretKey)


(apikey, secretkey) = getApiKeys("10.200.23.16", "admin", "password", None)


#apikey="pom8IkKoTGWX4cEvrrGflh_QMm6-2gtrHYOitqE2PUlIe55tcglvxHlzvpvTPzZ-lZQbuIyxe8umuY59G6BN1w"
#secretkey="5GP3esBMT4yr3oTuTFZxxuQ1k0znUvZClC7Nb3adyhmzeC4hF_bm0TTEGv07JEgs-LBzSbZXCs8JyzMLnlN6ig"

conn = cloudConnection("10.200.23.16", apiKey=apikey, securityKey=secretkey, port=8080, logging=logging)

configuration = {
   'cpu.overprovisioning.factor'     : 10,
   'mem.overprovisioning.factor'     : 10,
   'storage.overprovisioning.factor' : 4,
   'host'                            : "10.200.23.16",
   'expunge.delay'                   : 120,
   'expunge.interval'                : 60,
   'network.gc.interval'             : 60,
   'network.gc.wait'                 : 120
   }

listconfig = listConfigurations.listConfigurationsCmd()
try:
   resp = conn.marvin_request(listconfig)
   for item in resp:
      if item.name == "host":
         if item.value == "10.200.23.16":
            print "OK, host is correct"
         else:
            print "Incorrect host setting, updating configuration"
            updateConf = updateConfiguration.updateConfigurationCmd()
            for key,value in configuration.iteritems():
               updateConf.name = key
               updateConf.value = value
               try:
                  resp = conn.marvin_request(updateConf)
                  print "Set " + key + " to " + str(value)
               except urllib2.HTTPError, e:
                  print "updateConfigurationCmd failed to set " + key + " : " + str(e.msg)  
               
            print "Configuration set, restart the management server now"
            exit()
except urllib2.HTTPError, e:
   print "listConfigurationsCmd Failed : " + str(e.msg)
   exit()
            
zoneCmd = createZone.createZoneCmd()
zoneCmd.name         = "MCCDZone"
zoneCmd.networktype  = "Advanced"
zoneCmd.dns1         = "8.8.8.8"
zoneCmd.dns2         = "8.8.8.4"
zoneCmd.internaldns1 = "10.73.2.110"
zoneCmd.internaldns2 = "10.73.2.112"
zoneCmd.domain       = "mccd.local"
try:
   resp = conn.marvin_request(zoneCmd)
   zone = resp.zone
   print "Zone " + zone.name + " created"
except urllib2.HTTPError, e:
   print "createZoneCmd Failed : " + str(e.msg)

# Setup physical network for Management and Public
physNetCmd = createPhysicalNetwork.createPhysicalNetworkCmd()
physNetCmd.name      = "MCCD Mgmt"
physNetCmd.zoneid    = zone.id
physNetCmd.isolationmethods = [ "VLAN" ]
try:
   resp = conn.marvin_request(physNetCmd)
   physNetManagement = resp.physicalnetwork
except urllib2.HTTPError, e:
   print "createPhysicalNetworkCmd Failed : " + str(e.msg)

# Add traffic type Management
addTrafficTypeCmd = addTrafficType.addTrafficTypeCmd()
addTrafficTypeCmd.physicalnetworkid = physNetManagement.id
addTrafficTypeCmd.traffictype = "Management"
addTrafficTypeCmd.xennetworklabel = "McCloud_D_Front"
addTrafficTypeCmd.kvmnetworklabel = "cloudbr0"
addTrafficTypeCmd.vmwarenetworklabel = "vSwitch0"
try:
    resp = conn.marvin_request(addTrafficTypeCmd)
except urllib2.HTTPError, e:
   print "createPhysicalNetworkCmd Failed : " + str(e.msg)

# Add traffic type Public
addTrafficTypeCmd.traffictype = "Public"
addTrafficTypeCmd.xennetworklabel = "McCloud_D_Public"
addTrafficTypeCmd.kvmnetworklabel = "cloudbr1"
addTrafficTypeCmd.vmwarenetworklabel = "vSwitch1"
try:
    resp = conn.marvin_request(addTrafficTypeCmd)
except urllib2.HTTPError, e:
   print "createPhysicalNetworkCmd Failed : " + str(e.msg)

updatePhysNet = updatePhysicalNetwork.updatePhysicalNetworkCmd();
updatePhysNet.id = physNetManagement.id
updatePhysNet.state = "Enabled"
try:
    resp = conn.marvin_request(updatePhysNet)
except urllib2.HTTPError, e:
   print "updatePhysicalNetworkCmd Failed : " + str(e.msg)

print "Physical network " + physNetManagement.name + " created for Management and Public traffic"

# Setup physical network for Guest traffic
physNetCmd = createPhysicalNetwork.createPhysicalNetworkCmd()
physNetCmd.name      = "MCCD Guest"
physNetCmd.zoneid    = zone.id
physNetCmd.isolationmethods = [ "STT" ]
try:
   resp = conn.marvin_request(physNetCmd)
   physNetGuest = resp.physicalnetwork
except urllib2.HTTPError, e:
   print "createPhysicalNetworkCmd Failed : " + str(e.msg)

# Add guest traffic label
addTrafficTypeCmd.physicalnetworkid = physNetGuest.id
addTrafficTypeCmd.traffictype = "Guest"
addTrafficTypeCmd.xennetworklabel = "NVP Network"
addTrafficTypeCmd.kvmnetworklabel = "cloudbr-int"
addTrafficTypeCmd.vmwarenetworklabel = "vSwitch2"
#addTrafficTypeCmd.vmwarenetworklabel = "dvSwitch2,,vmwaredvs"
try:
    resp = conn.marvin_request(addTrafficTypeCmd)
except urllib2.HTTPError, e:
   print "createPhysicalNetworkCmd Failed : " + str(e.msg)

updatePhysNet = updatePhysicalNetwork.updatePhysicalNetworkCmd();
updatePhysNet.id = physNetGuest.id
updatePhysNet.state = "Enabled"
try:
    resp = conn.marvin_request(updatePhysNet)
except urllib2.HTTPError, e:
   print "updatePhysicalNetworkCmd Failed : " + str(e.msg)

print "Physical network " + physNetGuest.name + " created for Guest traffic"

# Add public network ip range
createVlan = createVlanIpRange.createVlanIpRangeCmd()
createVlan.zoneid  = zone.id
createVlan.vlan    = 317
createVlan.gateway = "195.66.90.193"
createVlan.netmask = "255.255.255.224"
createVlan.startip = "195.66.90.218" 
createVlan.endip   = "195.66.90.221"
createVlan.forvirtualnetwork = True
try:
    resp = conn.marvin_request(createVlan)
    vlan = resp.vlan
except urllib2.HTTPError, e:
   print "createVlanIpRangeCmd Failed : " + str(e.msg)
print "Vlan for public internet created on vlanid " + vlan.vlan

# Add VMware DC to the zone
addDc = addVmwareDc.addVmwareDcCmd()
addDc.name = "MCCD"
addDc.vcenter = "10.200.23.26"
addDc.username = "root"
addDc.password = "chickensoup"
addDc.zoneid = zone.id
try:
    resp = conn.marvin_request(addDc)
    vmwaredc = resp.vmwaredc
except urllib2.HTTPError, e:
   print "addVmwareDc Failed : " + str(e.msg)
print "Vmware DC " + vmwaredc.name + " added to zone"

# Add Pod
createPod = createPod.createPodCmd()
createPod.name    = "MCCDPod"
createPod.zoneid  = zone.id
createPod.startip = "10.200.23.71"
createPod.endip   = "10.200.23.80"
createPod.gateway = "10.200.23.1"
createPod.netmask = "255.255.255.0"
try:
    resp = conn.marvin_request(createPod)
    pod = resp.pod
except urllib2.HTTPError, e:
   print "createPodCmd Failed : " + str(e.msg)
print "Pod " + pod.name + " created"

# Add VmWare Cluster
addVmWareCluster = addCluster.addClusterCmd()
addVmWareCluster.clustername           = "MCCDVMwareCluster"
addVmWareCluster.clustertype           = "ExternalManaged"
addVmWareCluster.hypervisor            = "VMware"
addVmWareCluster.cpuovercommitratio    = 10
addVmWareCluster.memoryovercommitratio = 10
addVmWareCluster.username              = "root"
addVmWareCluster.password              = "chickensoup"
addVmWareCluster.publicvswitchtype     = "vmwaredvs"
addVmWareCluster.guestvswitchtype      = "vmwaredvs"
addVmWareCluster.url                   = "http://10.200.23.26/MCCD/MCCDVMwareCluster"
addVmWareCluster.podid                 = pod.id
addVmWareCluster.zoneid                = zone.id

try:
    resp = conn.marvin_request(addVmWareCluster)
    vmwarecluster = resp[0]
except urllib2.HTTPError, e:
   print "addCluster Failed : " + str(e.msg)
print "Cluster " + vmwarecluster.name + " created for " + vmwarecluster.hypervisortype + " hypervisors"


# Add secondary storage
addSecondary = addSecondaryStorage.addSecondaryStorageCmd()
addSecondary.zoneid = zone.id
addSecondary.url    = "nfs://10.200.23.31/volumes/mccd_volume1/mccdxpl2_secondary"
try:
    resp = conn.marvin_request(addSecondary)
    secstor = resp.secondarystorage
except urllib2.HTTPError, e:
   print "addCluster Failed : " + str(e.msg)
print "Secondary storage added : " + secstor.name

createPrimary = createStoragePool.createStoragePoolCmd()
createPrimary.zoneid    = zone.id
createPrimary.podid     = pod.id
createPrimary.name      = "VmWare Primary Storage"
createPrimary.url       = "nfs://10.200.23.31/volumes/mccd_volume1/vmware/store1"
createPrimary.clusterid = vmwarecluster.id
try:
    resp = conn.marvin_request(createPrimary)
    pool = resp.storagepool
except urllib2.HTTPError, e:
   print "createStoragePoolCmd Failed : " + str(e.msg)
print "Primary storage pool " + pool.name + " added to " + vmwarecluster.name

# Activate network service providers
addNsp = addNetworkServiceProvider.addNetworkServiceProviderCmd()
addNsp.name              = "NiciraNvp"
addNsp.physicalnetworkid = physNetGuest.id
addNsp.servicelist       = "Connectivity,SourceNat,PortForwarding,StaticNat"
try:
    resp = conn.marvin_request(addNsp)
    nsp = resp.networkserviceprovider
except urllib2.HTTPError, e:
   print "addNetworkServiceProviderCmd Failed : " + str(e.msg)

listVR = listVirtualRouterElements.listVirtualRouterElementsCmd()
confVR = configureVirtualRouterElement.configureVirtualRouterElementCmd()
confVR.enabled = True
try:
    resp = conn.marvin_request(listVR)
    for vrnsp in resp:
        confVR.id = vrnsp.id
        conn.marvin_request(confVR)
except urllib2.HTTPError, e:
   print "configureVirtualRouterElementCmd Failed : " + str(e.msg)

listNsp = listNetworkServiceProviders.listNetworkServiceProvidersCmd()
updateNsp = updateNetworkServiceProvider.updateNetworkServiceProviderCmd()
try:
    resp = conn.marvin_request(listNsp)
    for nsp in resp:
       if nsp.name in [ "VirtualRouter", "VpcVirtualRouter", "NiciraNvp" ] :
           updateNsp.id    = nsp.id
           updateNsp.state = "Enabled"
           resp = conn.marvin_request(updateNsp)
           nsp = resp.networkserviceprovider
           print "Network Service Provider " + nsp.name + " is " + nsp.state
except urllib2.HTTPError, e:
   print "updateNetworkServiceProviderCmd Failed : " + str(e.msg)

# Add the nicira controller
addNvpDevice = addNiciraNvpDevice.addNiciraNvpDeviceCmd()
addNvpDevice.physicalnetworkid = physNetGuest.id
addNvpDevice.hostname             = "10.200.23.51"
addNvpDevice.username             = "admin"
addNvpDevice.password             = "admin"
addNvpDevice.transportzoneuuid    = "32a4c7c0-c7f7-4f81-ad1b-197cd26a05bb"
addNvpDevice.l3gatewayserviceuuid = "50736c1d-f98e-413c-a9b8-35f6b5775ea3"
try:
     resp = conn.marvin_request(addNvpDevice)
     nvpdev = resp.niciranvpdevice
except urllib2.HTTPError, e:
      print "addNiciraNvpDeviceCmd Failed : " + str(e.msg)
print "Nicira NVP Controller at " + nvpdev.hostname + " is configured"

# Enable Zone
updZone = updateZone.updateZoneCmd()
updZone.id = zone.id
updZone.allocationstate = "Enabled"
try:
     resp = conn.marvin_request(updZone)
     nvpdev = resp.niciranvpdevice
except urllib2.HTTPError, e:
      print "updateZoneCmd Failed : " + str(e.msg)
print "Zone " + zone.name + " is Enabled"



