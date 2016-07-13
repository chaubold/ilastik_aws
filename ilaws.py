import boto3
import sys
import os
import ConfigParser
import code
import subprocess
import shlex
import glob

def deploy_instance(config, conn_args):
  # latest ubuntu ami
  ami_id = config.get('info', 'ami_id')


  # define userdata to be run at instance launch

  ec2_res = boto3.resource('ec2', **conn_args)

  new_instance = ec2_res.create_instances(
      ImageId=ami_id,
      MinCount=1,
      MaxCount=1,
      KeyName = config.get('info', 'keyname'),
      InstanceType=config.get('info', 'instancetype'),
      SecurityGroups=[config.get('info', 'securitygroup')]
      )


def loadFile(filename, config, conn_args, instances):
    for instance in instances:
        instance.wait_until_running()

    # Reload the instance attributes
        instance.load()
        dns = instance.public_dns_name
        print dns



        s = "scp " + "-B -oStrictHostKeyChecking=no -i ~/mdm.pem " + filename + " ubuntu@" + dns + ":" + os.path.basename(filename)
        print s
        args = shlex.split(s)
        print args
        subprocess.Popen(args)


def loadProjectFile(projectpath, config, conn_args, instances):
    for instance in instances:
        instance.wait_until_running()

    # Reload the instance attributes
        instance.load()
        dns = instance.public_dns_name
        print dns


        s = "scp " + "-B -oStrictHostKeyChecking=no -i ~/mdm.pem " + projectpath + " ubuntu@" + dns + ":/home/ubuntu/" + os.path.basename(projectpath)

        print s
        args = shlex.split(s)
        print args
        subprocess.Popen(args)

def triggerIlastik(instances):
    for instance in instances:
        instance.wait_until_running()

    # Reload the instance attributes
        instance.load()
        dns = instance.public_dns_name
        print dns


        s = "ssh -i ~/mdm.pem ubuntu@" + dns +" \'export LAZYFLOW_TOTAL_RAM_MB=950; /home/ubuntu/ilastik-1.2.0rc6-Linux/run_ilastik.sh --headless --project=/home/ubuntu/" + os.path.basename(projectpath) + " /home/ubuntu/" + os.path.basename(filename)+ "\'"
        print s
        args = shlex.split(s)
        print args
        subprocess.Popen(args)

def retrieveSegmentation(filename, instances):
    for instance in instances:
        instance.wait_until_running()

    # Reload the instance attributes
        instance.load()
        dns = instance.public_dns_name
        print dns


        s = "scp " + "-oStrictHostKeyChecking=no -i ~/mdm.pem ubuntu@" + dns + ":/home/ubuntu/" + os.path.basename(filename)[:-4] + "_Probabilities.h5 " + os.path.basename(filename)[:-4] + "_Probabilities.h5"
        print s
        args = shlex.split(s)
        print args
        subprocess.Popen(args)



def populateInstance(filename, projectpath, config, conn_args, fileCount):


    ec2 = boto3.resource('ec2', **conn_args)


    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    code.interact(local=locals())
    count = 0
    while(count != fileCount):
        count = 0
        for instance in instances:
            count+=1

    for instance in instances:
        instance.wait_until_running()

# Reload the instance attributes
        instance.load()
        dns = instance.public_dns_name
        print dns



        s = "scp " + "-oStrictHostKeyChecking=no -i ~/mdm.pem " + filename + " ubuntu@" + dns + ":" + os.path.basename(filename)
        print s

        p = subprocess.call(s, shell=True)


        s = "scp " + "-oStrictHostKeyChecking=no -i ~/mdm.pem " + projectpath + " ubuntu@" + dns + ":/home/ubuntu/" + os.path.basename(projectpath)
        print s
        p = subprocess.call(s, shell=True)

        s = "ssh -i ~/mdm.pem ubuntu@" + dns +" \'export LAZYFLOW_TOTAL_RAM_MB=950; /home/ubuntu/ilastik-1.2.0rc6-Linux/run_ilastik.sh --headless --project=/home/ubuntu/" + os.path.basename(projectpath) + " /home/ubuntu/" + os.path.basename(filename)+ "\'"
        print s
        p = subprocess.call(s, shell=True)

        s = "scp " + "-oStrictHostKeyChecking=no -i ~/mdm.pem ubuntu@" + dns + ":/home/ubuntu/" + os.path.basename(filename)[:-4] + "_Probabilities.h5 " + os.path.basename(filename)[:-4] + "_Probabilities.h5"
        print s
        p = subprocess.call(s, shell=True)

        instance.terminate()






def main():
    if len(sys.argv) < 3:
        print "-------------------------------------------------------------"
        print "ilaws -- a wrapper for AWS for launching ilastik segmentation on the cloud"
        print "usage: python ilaws.py <path to directory with input data> <path to ilastik project file>"
        print "written by michael morehead @ ilastik workshop 2016"
        print "-------------------------------------------------------------"
        sys.exit()
    folderpath = sys.argv[1]
    projectpath = sys.argv[2]
    config = ConfigParser.ConfigParser()
    config.read("./config.ini")

    conn_args = {
        'aws_access_key_id': config.get('info', 'aws_access_key_id'),
        'aws_secret_access_key': config.get('info', 'aws_secret_access_key'),
        'region_name': config.get('info', 'region_name')
    }



    l = glob.glob(os.path.join(folderpath, "*"))
    print "starting " + str(len(l)) + " instances"
    for fileCount, each in enumerate(l):
        print 1
        deploy_instance(config, conn_args)


    ec2 = boto3.resource('ec2', **conn_args)


    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])

    count = 0
    print "waiting for instances to spawn..."
    while(count < fileCount):
        count = 0

        for instance in instances:
            count += 1

    print "instances ready, sending data!"


    for filename in l:
        loadFile(filename, config, conn_args, instances)


    for filename in l:
        loadProjectFile(projectpath, config, conn_args, instances)

    for filename in l:
        triggerIlastik(instances)

    for filename in l:
        retrieveSegmentation(filename, instances)



if __name__ == "__main__":
    main()
