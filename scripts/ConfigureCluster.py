#!/bin/env python

import subprocess
import sys
import os
import yaml
import argparse

def exec_ssh(COMMAND,thehost):
    ssh = subprocess.Popen(["ssh","-t", "%s" % thehost, COMMAND],
                           shell=False,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    #result = ssh.stdout.readlines()
#    print('\t\t'+ str(ssh.stdout.read()))
    for line in ssh.stdout.readlines():
        sys.stdout.write('\t\t'+line)

def exec_scp(FILE,thehost):
    cathost = subprocess.Popen(["scp", FILE,"%s:" % thehost],
                               shell=False,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    print(cathost.stdout.readlines()) 

parser = argparse.ArgumentParser()

parser.add_argument ('ACTION',choices=['provision','start','stop','restart','status'])
parser.add_argument ( '-c','--config',help='Path to config file',action='store',dest='config')
parser.add_argument ( '-g','--group',help='Name of the server group',action='store',dest='group')

opts = parser.parse_args()

print(opts.config)
print(opts.group)

with open(opts.config, 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

if not opts.group in cfg:
    print("Group " + opts.group + " Not found")
    exit(1)

HOSTS=[]

for host in cfg[opts.group]:
    if host == 'username' :
        username=cfg[opts.group][host]
    else:
    # print(cfg[opts.group][host]['hostname'])
        HOSTS.append((cfg[opts.group][host]['hostname'],cfg[opts.group][host]['int_ip'],host))

# Sort by node index
HOSTS.sort(key=lambda tup: tup[2])
print(HOSTS)

#       ('ec2-user@ec2-54-226-106-186.compute-1.amazonaws.com','10.151.47.49')]

# Build HOSTS file for this cluster

scriptdir = os.path.dirname(os.path.realpath(__file__))

print(scriptdir)

try:
    os.chdir ( scriptdir + '/' + opts.group )
except IOError: 
    os.mkdir ( scriptdir + '/' + opts.group )

counter=1

fo = open ( "hosts","wb")
for HOST in HOSTS:
    # Get the hostname
    #thehost=str(HOST[0].split('@')[1])
    thehost=username + '@' + str(HOST[0])

    # Write this host to the hosts file
    #fo.write(str(HOST[1]) + " " + thehost + ' ' + 'cluster' + str(counter) + '\n')
    fo.write(str(HOST[1]) + " " + 'cluster' + str(HOST[2].split('node')[1]) + ' # ' + thehost + '\n')

    # Writeout the zookeeper id file
    h = open (thehost +".myid","wb")
    h.write(str(HOST[2].split('node')[1]))
    h.close()
     
    counter+=1
fo.close()

# Ports are handled in ~/.ssh/config since we use OpenSSH
COMMANDS=['sudo bash /home/ec2-user/placehosts.sh %s',
          'which chef-solo || sudo yum -y localinstall https://opscode-omnibus-packages.s3.amazonaws.com/el/6/x86_64/chef-12.0.3-1.x86_64.rpm',
          'which git || sudo yum -y install git',
          'cd /opt/storm && sudo git pull',
          'cd /opt/ || sudo git clone https://github.com/scott-mead/storm.git',
          'cd /opt/storm/chef-repo && sudo chef-solo -c solo.rb -j solo.json']

for HOST in HOSTS:
    thehost=username + '@' + HOST[0]

    print("Now connecting to: " + HOST[2] + " " + thehost)

    if opts.ACTION == 'provision':
        exec_scp(scriptdir + "/hosts",thehost)
        exec_scp(scriptdir + "/placehosts.sh",thehost)
        exec_scp(thehost+".myid",thehost)

        for COMMAND in COMMANDS:
            if 'placehosts.sh' in COMMAND:
                COMMAND = COMMAND % thehost
        
            print("\tNow Executing: " + COMMAND)
            exec_ssh(COMMAND,thehost)

    elif opts.ACTION=='status':
        exec_ssh ('ps aux | egrep \'supervisor|zookeeper|storm\'',thehost)
            
    else:
        COMMAND="sudo /etc/init.d/supervisord " + opts.ACTION
        print("\tNow Executing: " + COMMAND)
        exec_ssh(COMMAND,thehost)

os.chdir(scriptdir)

