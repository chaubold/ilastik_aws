import boto3
import sys
import os
import ConfigParser
import code
import subprocess
import shlex
import glob
import Queue, thread
import time


config = ConfigParser.ConfigParser()
config.read("./config.ini")


conn_args = {
    'aws_access_key_id': config.get('info', 'aws_access_key_id'),
    'aws_secret_access_key': config.get('info', 'aws_secret_access_key'),
    'region_name': config.get('info', 'region_name')
}

ec2 = boto3.resource('ec2', **conn_args)


instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]).terminate()

