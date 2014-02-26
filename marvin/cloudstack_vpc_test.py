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
import random

from marvin.cloudstackConnection import cloudConnection
from marvin.cloudstackException import cloudstackAPIException
from marvin.cloudstackAPI import *
from marvin import cloudstackAPI


class testVpcWithNicira(object):

   #
   # Query Zone
   #
   def internalQueryZone(self, conn) :
      lz = listZones.listZonesCmd()
      lz.available = True # List all
      resp = conn.marvinRequest(lz)
      return resp[0] # return the first zone always

   #
   # Create the VPC
   #
   def internalCreateVPC(self, conn, zone, vpcoffering) :
      cvpc = createVPC.createVPCCmd()
      cvpc.cidr = "192.168.0.0/16"
      cvpc.name = "TestVPC_" + str(random.randrange(1, 400, 1))
      cvpc.displaytext = "Test VPC"
      cvpc.zoneid = zone.id
      cvpc.vpcofferingid = vpcoffering.id

      resp = conn.marvinRequest(cvpc)
      return resp.vpc
   
   #
   # Create the VPC offering
   #
   def internalCreateVpcOffering(self, conn) :
      cvo = createVPCOffering.createVPCOfferingCmd()
      cvo.name = "VPCNiciraNvpL2_" + str(random.randrange(1, 400, 1))
      cvo.displaytext = "VPC using NiciraNvp L2 Networking"
      cvo.supportedservices = [ "Lb", "UserData", "PortForwarding",
                                "Dhcp", "Vpn", "Dns", "SourceNat",
                                "StaticNat" ]
      cvo.serviceproviderlist = [ { "service": "Lb", "provider": "VpcVirtualRouter"},
                                  { "service": "UserData", "provider": "VpcVirtualRouter"},
                                  { "service": "PortForwarding", "provider": "VpcVirtualRouter"},
                                  { "service": "Dhcp", "provider": "VpcVirtualRouter"},
                                  { "service": "Vpn", "provider": "VpcVirtualRouter"},
                                  { "service": "Dns", "provider": "VpcVirtualRouter"},
                                  { "service": "SourceNat", "provider": "VpcVirtualRouter"},
                                  { "service": "StaticNat", "provider": "VpcVirtualRouter"}]
#                                  { "service": "Connectivity", "provider": "NiciraNvp"}]
      cvo.serviceofferingid = 17
      resp = conn.marvinRequest(cvo)
      #
      # Enable the network offering
      #
      uvo = updateVPCOffering.updateVPCOfferingCmd()
      uvo.id = resp.vpcoffering.id
      uvo.state = "Enabled"
      resp = conn.marvinRequest(uvo)

      return resp.vpcoffering

   #
   # Create the network offering
   #
   def internalCreateNetworkOfferingWithLb(self, conn):
      cno = createNetworkOffering.createNetworkOfferingCmd()
      cno.name = "NiciraNvpL2VPC_" + str(random.randrange(1, 400, 1))
      cno.displaytext = "VPC offering with Nicira NVP L2"
      cno.traffictype = "GUEST"
      cno.specifyvlan = False
      cno.availability = "Optional"
      cno.conservemode = False
      cno.guestiptype = "Isolated"
      cno.usevpc = True
      cno.supportedservices = [ "Lb", "UserData", "PortForwarding",
                                "Dhcp", "Vpn", "Dns", "SourceNat",
                                "StaticNat" ]
      cno.serviceproviderlist = [ { "service": "Lb", "provider": "VpcVirtualRouter" },
                                  { "service": "UserData", "provider": "VpcVirtualRouter"},
                                  { "service": "PortForwarding", "provider": "VpcVirtualRouter"},
                                  { "service": "Dhcp", "provider": "VpcVirtualRouter"},
                                  { "service": "Vpn", "provider": "VpcVirtualRouter"},
                                  { "service": "Dns", "provider": "VpcVirtualRouter"},
                                  { "service": "SourceNat", "provider": "VpcVirtualRouter"},
                                  { "service": "StaticNat", "provider": "VpcVirtualRouter"}]
#                                  { "service": "Connectivity", "provider": "NiciraNVP"} ]
      cno.servicecapabilitylist = [ { "service": "SourceNat", "capabilitytype": "SupportedSourceNatTypes", "capabilityvalue": "peraccount" },
                                    { "service": "Lb", "capabilitytype": "SupportedLbIsolation", "capabilityvalue": "dedicated" } ]                            
      #cno.tags
      #cno.networkrate
      #cno.serviceofferingid

      resp = conn.marvinRequest(cno)
      networkoffering = resp.networkoffering

      #
      # Enable the network offering
      #
      uno = updateNetworkOffering.updateNetworkOfferingCmd()
      uno.id = networkoffering.id
      uno.state = "Enabled"
      resp = conn.marvinRequest(uno)
      return networkoffering

   #
   # Create the network offering without Lb
   #
   def internalCreateNetworkOfferingNoLb(self, conn) :
      cno = createNetworkOffering.createNetworkOfferingCmd()
      cno.name = "NiciraNvpL2VPCNoLB_" + str(random.randrange(1, 400, 1))
      cno.displaytext = "VPC offering with Nicira NVP L2 without Lb"
      cno.traffictype = "GUEST"
      cno.specifyvlan = False
      cno.availability = "Optional"
      cno.conservemode = False
      cno.guestiptype = "Isolated"
      cno.usevpc = True
      cno.supportedservices = [ "UserData", "PortForwarding",
                                "Dhcp", "Vpn", "Dns", "SourceNat",
                                 "StaticNat" ]
      cno.serviceproviderlist = [ { "service": "UserData", "provider": "VpcVirtualRouter"},
                                  { "service": "PortForwarding", "provider": "VpcVirtualRouter"},
                                  { "service": "Dhcp", "provider": "VpcVirtualRouter"},
                                  { "service": "Vpn", "provider": "VpcVirtualRouter"},
                                  { "service": "Dns", "provider": "VpcVirtualRouter"},
                                  { "service": "SourceNat", "provider": "VpcVirtualRouter"},
                                  { "service": "StaticNat", "provider": "VpcVirtualRouter"}]
#                                  { "service": "Connectivity", "provider": "NiciraNVP"} ]
      cno.servicecapabilitylist = [ { "service": "SourceNat", "capabilitytype": "SupportedSourceNatTypes", "capabilityvalue": "peraccount" } ]                  
      #cno.tag
      #cno.networkrate
      #cno.serviceofferingid

      resp = conn.marvinRequest(cno)
      networkofferingnolb = resp.networkoffering

      #
      # Enabled the network offering
      #
      uno = updateNetworkOffering.updateNetworkOfferingCmd()
      uno.id = networkofferingnolb.id
      uno.state = "Enabled"
      resp = conn.marvinRequest(uno)
      return networkofferingnolb

   #
   # Create a network
   #
   def internalCreateNetwork(self, conn, networkoffering, vpc, zone) :
      cn = createNetwork.createNetworkCmd()
      cn.networkofferingid = networkoffering.id
      cn.displaytext="tier"
      tier = str(random.randrange(10, 250, 1))
      cn.name="tier_" + str(tier)
      cn.gateway="192.168." + str(tier) + ".1"
      cn.netmask="255.255.255.0"
      cn.vpcid=vpc.id
      cn.zoneid=zone.id

      resp = conn.marvinRequest(cn)
      print repr(resp)
      return resp

   #
   # Run the test
   #
   def testRun(self) :
      (apikey, secretkey) = self.getApiKeys("localhost", "admin", "password", None)
      blub = mgmtDetails()
      blub.apiKey=apikey
      blub.securityKey=secretkey

      conn = cloudConnection(blub, logging=logging)

      # Seed the random generator that we use to generate names
      random.seed()

      try:
         zone = self.internalQueryZone(conn)
         vpcoffering = self.internalCreateVpcOffering(conn);
         vpc = self.internalCreateVPC(conn, zone, vpcoffering)
 
         vpcnetwithlb = self.internalCreateNetworkOfferingWithLb(conn);
         vpcnetnolb = self.internalCreateNetworkOfferingNoLb(conn);

         network_with_lb = self.internalCreateNetwork(conn, vpcnetwithlb, vpc, zone)
         network_without_lb = self.internalCreateNetwork(conn, vpcnetnolb, vpc, zone)
         network_without_lb = self.internalCreateNetwork(conn, vpcnetnolb, vpc, zone)
         
      except urllib2.HTTPError, e:
         print e.read()
         raise e

   def getApiKeys(self, host, username, password, domain):
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

class mgmtDetails(object):
    apiKey = ""
    securityKey = ""
    mgtSvrIp = "localhost"
    port = 8080
    user = "admin"
    passwd = "password"
    certCAPath = None
    certPath = None
    useHttps = "False"

if __name__ == "__main__":
   
   blub = testVpcWithNicira()
   blub.testRun()
