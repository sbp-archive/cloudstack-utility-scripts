#!/usr/bin/python

import marvin
import json
import urllib2
import random
import time
from marvin.cloudstackConnection import cloudConnection
from marvin.cloudstackException import cloudstackAPIException
from marvin.cloudstackAPI import *
from marvin import cloudstackAPI


class testTemplateReady(object):

   #
   # Query Zone
   #
   def internalQueryZone(self, conn) :
      lz = listZones.listZonesCmd()
      lz.available = True # List all
      resp = conn.make_request(lz)
      return resp[0] # return the first zone always

   def checkTemplateReady(self, conn, zone) :
      lt = listTemplates.listTemplatesCmd()
      lt.templatefilter="featured"
      lt.zoneid=zone.id
      resp = conn.make_request(lt)
      return resp;
      
   #
   # Run the test
   #
   def testRun(self) :
      apikey = "Q1rKKrMjxNhGopcGQv-c5eiVh7oSdiZ1wgElUu5jdawFonr6_c2JB_K5bnBsq7_JnmpNO9rxu-6_qcQzhG3DJA"
      secretkey = "JQV1JqWIUvH6FGOofjfaOs8EAHTUA5IZTRcpQUqFEL06MDUaWM8HMukUT5tBQUb7G7M0cfNK6rM766Ln0HXmDw"
      conn = cloudConnection("localhost", apiKey=apikey, securityKey=secretkey, port=8080, protocol="http")

      # Seed the random generator that we use to generate names
      random.seed()

      try:
         zone = self.internalQueryZone(conn)
         timeremaining = 3 # 20 minutes
         ready = True
         while (timeremaining > 0) :
            templatelist = self.checkTemplateReady(conn, zone)
            if not templatelist is None :
               for template in templatelist :
                  if template.account == "system" and  template.isready :
                     ready = False
            if ready :
               break
            time.sleep(60)
            timeremaining = timeremaining - 1
         if not ready :
            raise Exception('timeout waiting for templates to become ready')
         print "All templates are ready"
         
      except urllib2.HTTPError, e:
         print e.read()
         raise e

if __name__ == "__main__":
   blub = testTemplateReady()
   blub.testRun()
