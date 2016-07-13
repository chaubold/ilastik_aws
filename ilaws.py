import boto3
import sys
import os
import ConfigParser
import code
import subprocess
import glob

def deploy_instance(config):
  # latest ubuntu ami
  ami_id = config('info', 'ami_id')


  # define userdata to be run at instance launch




  conn_args = {
      'aws_access_key_id': 'AKIAIBXC7HPX376YYNXA',
      'aws_secret_access_key': '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',
      'region_name': 'us-east-1'
  }

  ec2_res = boto3.resource('ec2', **conn_args)

  new_instance = ec2_res.create_instances(
      ImageId=ami_id,
      MinCount=1,
      MaxCount=1,
      KeyName = config('info', 'ami_id'),
      InstanceType=config('info', 'instancetype'),
      SecurityGroups=[config('info', 'securitygroup')]
      )




def populateInstance():
    conn_args = {
        'aws_access_key_id': config('info', 'aws_access_key_id'),
        'aws_secret_access_key': config('info', 'aws_secret_access_key'),
        'region_name': config('info', 'region_name')
    }

    ec2 = boto3.resource('ec2', **conn_args)

    instances = ec2.instances.filter(
    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    for instance in instances:
        instance.wait_until_running()

# Reload the instance attributes
        instance.load()
        dns = instance.public_dns_name
        print dns



        s = "scp " + "-i ~/mdm.pem ./exampleset/VCN_subsubsample_crop-10000.tif ubuntu@" + dns + ":/home/ubuntu/VCN_subsubsample_crop-10000.tif"
        print s
        p = subprocess.call(s, shell=True)


        s = "scp " + "-i ~/mdm.pem ./batchtest.ilp ubuntu@" + dns + ":/home/ubuntu/batchtest.ilp"
        print s
        p = subprocess.call(s, shell=True)

        s = "ssh -i ~/mdm.pem ubuntu@" + dns +" 'export LAZYFLOW_TOTAL_RAM_MB=950; /home/ubuntu/ilastik-1.2.0rc6-Linux/run_ilastik.sh --headless --project=/home/ubuntu/batchtest.ilp /home/ubuntu/VCN_subsubsample_crop-10000.tif'"
        print s
        p = subprocess.call(s, shell=True)

        s = "scp " + "-i ~/mdm.pem ubuntu@" + dns + ":/home/ubuntu/ ./batchtest.ilp batchtest.ilp"
        print s
        p = subprocess.call(s, shell=True)


        code.interact(local=locals())


def sendScriptCmd():
    conn_args = {
        'aws_access_key_id': 'AKIAIBXC7HPX376YYNXA',
        'aws_secret_access_key': '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',
        'region_name': 'us-east-1'
    }

    ec2 = boto3.resource('ec2', **conn_args)

    instances = ec2.instances.filter(
    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    for instance in instances:
        instance.wait_until_running()

        conn_args = {
            'aws_access_key_id': 'AKIAIBXC7HPX376YYNXA',
            'aws_secret_access_key': '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',
            'region_name': 'us-east-1'
        }

# Reload the instance attributes
        instance.load()
        dns = instance.public_dns_name
        print dns
        client_ssm = boto3.client("ssm", **conn_args)
        client_ssm.list_commands()
        #code.interact(local=locals())
        print instance.id
        client_ssm.send_command(InstanceIds=['i-0b209edfcb3870d7a'], DocumentName='AWS-RunShellScript',Parameters={"commands" : ["/home/ec2-user/ilastik-1.2.0rc6-Linux/run_ilastik.sh --headless --project=/home/ec2-user/batchtest.ilp /home/ec2-user/VCN_subsubsample_crop-10000.tif"]}, TimeoutSeconds=30)

def main():
    folderpath = sys.argv[1]
    projectpath = sys.argv[2]
    config = ConfigParser.ConfigParser()


    l = glob.glob(os.path.join(folderpath, "*"))







populateInstance()
