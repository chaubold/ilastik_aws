import boto3
import sys
import os
import ConfigParser
import code
import subprocess
import glob

def deploy_instance(config, conn_args):
  # latest ubuntu ami
  ami_id = config('info', 'ami_id')


  # define userdata to be run at instance launch

  ec2_res = boto3.resource('ec2', **conn_args)

  new_instance = ec2_res.create_instances(
      ImageId=ami_id,
      MinCount=1,
      MaxCount=1,
      KeyName = config('info', 'ami_id'),
      InstanceType=config('info', 'instancetype'),
      SecurityGroups=[config('info', 'securitygroup')]
      )




def populateInstance(filename, config, conn_args, fileCount):


    ec2 = boto3.resource('ec2', **conn_args)

    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    code.interact(local=locals())
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

        instance.terminate()






def main():
    if len(sys.argv) < 3:
        print "-------------------------------------------------------------"
        print "ilaws -- a wrapper for AWS for launching ilastik segmentation"
        print "usage: python ilaws.py [path to directory with input data] [path to ilastik project file]"
        print "written by michael morehead @ ilastik 2016 workshop"
        print "-------------------------------------------------------------"
    folderpath = sys.argv[1]
    projectpath = sys.argv[2]
    config = ConfigParser.ConfigParser()

    conn_args = {
        'aws_access_key_id': config('info', 'aws_access_key_id'),
        'aws_secret_access_key': config('info', 'aws_secret_access_key'),
        'region_name': config('info', 'region_name')
    }


    l = glob.glob(os.path.join(folderpath, "*"))

    for fileCount, each in l:
        code.interact(local=locals())
        deploy_instance(config, conn_args)
    for fileCount, filename in l:
        populateInstance(filename, config, conn_args, fileCount)


if __name__ == "__main__":
    main()
