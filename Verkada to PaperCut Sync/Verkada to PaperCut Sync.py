'''
	.NOTES
	===========================================================================
	 Created on:  07/15/2025
	 Updated on:	07/15/2025
	 Created by:  James Krolik
	 Filename:    Verkada - Papercut Badge Sync.py
	===========================================================================
	.DESCRIPTION
		This script is designed to take the first two active badges in Verkada
    and inject into PaperCut for badge authentication.

    .USAGE
        This should be implemented via n8n or similiar with a secure vault to 
        store your keys
'''
#VSCode Imports
from pip._vendor import requests   

#If not using VSCode, here are the direct imports
#import requests

from xml.etree import ElementTree
import os
import platform
import time

###################
# Parameter Block #
###################

verkadaKey = ''  #Enter your Verkada API key here

baseURL = 'https://api.verkada.com'
url = baseURL + '/token'

papercutAuthToken = '' #Enter your PaperCut API token here
papercutServer = ''  #Enter your FQDN servername here
papercutApiUrl = 'http://' + papercutServer + ':9191/rpc/api/xmlrpc'

rateLimitCounter = 0
rateLimitMaximum = 250  #Set this below the maximum rate limit.
rateLimitSeconds = 60

##################
# Function Block #
##################

def clearScreen():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

def papercutIsUserActive(samAccountName):
    #Set up our XML payload
    xmlRpcRequest = f'''
    <methodCall>
    <methodName>api.isUserExists</methodName>
    <params>
        <param>
        <value>
            <string>{papercutAuthToken}</string>
        </value>
        </param>
        <param>
        <value>
            <string>{samAccountName}</string>
        </value>
        </param>
    </params>
    </methodCall> 
    '''

    #Send the request
    response = requests.post(papercutApiUrl, data=xmlRpcRequest)

    #Parse the response
    root = ElementTree.fromstring(response.text)
    #Find the key for the active user
    activeUser = root.find('.//boolean')

    if activeUser.text == "1":
        return True
    else:
        return False
    
def papercutSetBadge(samAccountName,badgeNumber,type):
    if badgeNumber == 0:
        badgeNumber = None  #Unset the variable, effectively setting it to NULL.
      
    #Set up our XML payload
    xmlRpcRequest = f'''
    <methodCall>
    <methodName>api.setUserProperty</methodName>
    <params>
        <param>
        <value>
            <string>{papercutAuthToken}</string>
        </value>
        </param>
        <param>
        <value>
            <string>{samAccountName}</string>
        </value>
        </param>
        <param>
            <value>
                <string>{type}</string>
            </value>
            <value>
                <string>{badgeNumber}</string>
            </value>
        </param>
    </params>
    </methodCall> 
    '''

    #Send the request
    response = requests.post(papercutApiUrl, data=xmlRpcRequest, headers=headers)
    #Parse the response for verbosity if needed.
    root = ElementTree.fromstring(response.text)
    
#################
# Program Begin #
#################

clearScreen

#Get our access token from Verkada
headers = {
    "accept": "application/json",
    "x-api-key": verkadaKey
}

response = requests.post(url, headers=headers)
token = response.json()
token = token["token"]

#Flush our response out of memory
response = None

###############################################
#  Get all user userID's for subsequent query #
###############################################

url = baseURL + "/access/v1/access_users"

headers = {
    "accept": "application/json",
    "x-verkada-auth": token
    }

response = requests.get(url, headers=headers)

getUsers = response.json() 
totalUsers = len(getUsers["access_members"]) 

#Flush our response out of memory
response = None

for i in range(totalUsers):
    user = getUsers["access_members"][i]["full_name"]
    userID = getUsers["access_members"][i]["user_id"]
    email = getUsers["access_members"][i]["email"]
    userSAM = email.split("@")[0]

    rateLimitCounter = rateLimitCounter + 1
    if rateLimitCounter > rateLimitMaximum:
        print("\nHit rate limit, sleeping\n")
        time.sleep(rateLimitSeconds)
        rateLimitCounter = 0

    url =  baseURL + "/access/v1/access_users/user?user_id=" + userID

    #Reset the badge on iteration
    userBadge = None

    try:
        response = requests.get(url, headers=headers)

        isAccountActiveInPapercut = None
        isAccountActiveInPapercut = papercutIsUserActive(userSAM)

        if isAccountActiveInPapercut:
            validCardCount = 0
            userBadge = response.json()
            userCards = len(userBadge["cards"])

            #Flush our response out of memory.
            response = None

            #Iterate through each of the employee's badges
            for j in range(0,userCards):
                card = None
                isBadgeActive = userBadge["cards"][j]["active"]
                if isBadgeActive:
                    validCardCount += 1
                
                #Set the badges
                if validCardCount == 1:
                    card = userBadge["cards"][j]["facility_code"] + userBadge["cards"][j]["card_number"]
                    papercutSetBadge(userSAM,card,"primary-card-number")
                if validCardCount == 2:
                    card = userBadge["cards"][j]["facility_code"] + userBadge["cards"][j]["card_number"]
                    papercutSetBadge(userSAM,card,"secondary-card-number")

                #Unset any remaining cards
                if validCardCount == 0:
                    papercutSetBadge(userSAM,0,"primary-card-number")
                    papercutSetBadge(userSAM,0,"secondary-card-number")
                if validCardCount == 1:
                    papercutSetBadge(userSAM,0,"secondary-card-number")
    except Exception as e:
        print(e)

#Flush all variables out of memory.
user = None
userID = None
email = None
userSAM = None
userBadge = None
userCards = None
card = None
response = None
