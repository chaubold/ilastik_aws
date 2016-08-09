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

def process_waiter(popen, description, que):
    try:
        popen.wait()
    finally:
        que.put( (description, popen.returncode))


def loadFiles(config, conn_args, instanceFileDict):
    process_count = 0
    results= Queue.Queue()
    pemKey = config.get('info', 'pem')
    for instance in instanceFileDict:
        listOfFiles = instanceFileDict[instance]
        instance.wait_until_running()
    # Reload the instance attributes
        instance.load()
        dns = instance.public_dns_name
        print dns
        s = "rsync " + "-rave \"ssh -i " + pemKey + " -o StrictHostKeyChecking=no -o LogLevel=ERROR\" " + str(listOfFiles) + " ubuntu@" + dns + ":/home/ubuntu/in/"
        print s
        args = shlex.split(s)
        print args
        p = subprocess.Popen(args)
        thread.start_new_thread(process_waiter, (p, instance, results))

        process_count +=1


    while process_count > 0:
        print process_count
        description, rc= results.get()
        print "job", description, "ended with rc =", rc
        if rc != 0:
            instance = description
            instance.wait_until_running()
        # Reload the instance attributes
            instance.load()
            dns = instance.public_dns_name
            print dns
            s = "rsync " + "-rave \"ssh -i " + pemKey + " -o StrictHostKeyChecking=no -o LogLevel=ERROR\" " + str(description) + " ubuntu@" + dns + ":/home/ubuntu/in/"
            print s
            args = shlex.split(s)
            print args
            p = subprocess.Popen(args)
            thread.start_new_thread(process_waiter, (p, description, results))

        else:
            process_count-= 1

    # while process_count > 0:
    #     description, rc= results.get()
    #     print "job", descthreadLoadription, "ended with rc =", rc
    #     if rc != 0:
    #         instance = instanceFileDict[description]
    #         instance.wait_until_running()
    #     # Reload the instance attributes
    #         instance.load()
    #         dns = instance.public_dns_name
    #         print dns
    #         s = "scp " + "-B -oStrictHostKeyChecking=no -i " + pemKey + " " + filename + " ubuntu@" + dns + ":" + os.path.basename(filename)
    #         print s
    #         args = shlex.split(s)
    #         print args
    #         p = subprocess.Popen(args)
    #         thread.start_new_thread(process_waiter, (p, filename, results))
    #         process_count +=1
    #     process_count-= 1



def loadProjectFiles(projectpath, config, conn_args, instanceFileDict):
    process_count = 0
    results= Queue.Queue()
    pemKey = config.get('info', 'pem')
    for filename in instanceFileDict:

        instance = instanceFileDict[filename]
        instance.wait_until_running()
        instance.load()
        dns = instance.public_dns_name
        print dns
        s = "scp " + "-B -oStrictHostKeyChecking=no -i " + pemKey + " " + projectpath + " ubuntu@" + dns + ":/home/ubuntu/" + os.path.basename(projectpath)
        print s
        args = shlex.split(s)
        print args
        p = subprocess.Popen(args)
        thread.start_new_thread(process_waiter, (p, str(instanceFileDict[filename]) + " finished copying project file...", results))
        process_count +=1

    while process_count > 0:
        description, rc= results.get()
        print "job", description, "ended with rc =", rc
        process_count-= 1

def triggerIlastik(filename, config, projectpath, instanceFileDict):
    process_count = 0
    results= Queue.Queue()
    pemKey = config.get('info', 'pem')   
    

    for filename in instanceFileDict:
        instance = instanceFileDict[filename]
        instance.wait_until_running()
        instance.load()
        dns = instance.public_dns_name
        print dns

        s = "ssh -oStrictHostKeyChecking=no -i " + pemKey + " ubuntu@" + dns +" \'export LAZYFLOW_TOTAL_RAM_MB=950; /home/ubuntu/ilastik-1.2.0rc7-Linux/run_ilastik.sh --headless --project=/home/ubuntu/in/" + os.path.basename(projectpath) + "--output_filename_format=/home/ubuntu/out/" + os.path.basename(filename)+ "\'"
        print s
        args = shlex.split(s)
        print args
        p = subprocess.Popen(args)
        thread.start_new_thread(process_waiter, (p, filename, results))
        process_count += 1

    while process_count > 0:
        print process_count
        description, rc= results.get()
        print "job", description, "ended with rc =", rc
        if rc != 0:
            instance = instanceFileDict[description]
            instance.wait_until_running()
        # Reload the instance attributes
            instance.load()
            dns = instance.public_dns_name
            print dns
            s = "ssh -oStrictHostKeyChecking=no -i " + pemKey + " ubuntu@" + dns +" \'export LAZYFLOW_TOTAL_RAM_MB=950; /home/ubuntu/ilastik-1.2.0rc7-Linux/run_ilastik.sh --headless --project=/home/ubuntu/in/" + os.path.basename(projectpath) + "--output_filename_format=/home/ubuntu/out/" + os.path.basename(description)+ "\'"
            print s
            args = shlex.split(s)
            print args
            p = subprocess.Popen(args)
            thread.start_new_thread(process_waiter, (p, description, results))
        else:
            process_count-= 1

def retrieveSegmentations(filename, instanceFileDict, config):

    process_count = 0
    results= Queue.Queue()
    pemKey = config.get('info', 'pem')
    for filename in instanceFileDict:
        instance = instanceFileDict[filename]
        instance.wait_until_running()
        instance.load()
        dns = instance.public_dns_name
        print dns

        s = "scp " + "-B -oStrictHostKeyChecking=no -o LogLevel=ERROR -i " + pemKey + " ubuntu@" + dns + ":/home/ubuntu/" + os.path.basename(filename)[:-4] + "_Probabilities.h5 " + os.path.basename(filename)[:-4] + "_Probabilities.h5"
        print s
        args = shlex.split(s)
        print args
        p = subprocess.Popen(args)
        thread.start_new_thread(process_waiter, (p, filename, results))
        process_count += 1

    while process_count > 0:
        description, rc= results.get()
        print "job", description, "ended with rc =", rc
        if rc != 0:
            instance = instanceFileDict[description]
            instance.wait_until_running()
        # Reload the instance attributes
            instance.load()
            dns = instance.public_dns_name
            print dns
            s = "scp " + "-B -oStrictHostKeyChecking=no -o LogLevel=ERROR -i " + pemKey + " ubuntu@" + dns + ":/home/ubuntu/" + os.path.basename(description)[:-4] + "_Probabilities.h5 " + os.path.basename(description)[:-4] + "_Probabilities.h5"
            print s
            args = shlex.split(s)
            print args
            p = subprocess.Popen(args)
            thread.start_new_thread(process_waiter, (p, description, results))
        else:
            process_count-= 1

    for filename in instanceFileDict:
        instance = instanceFileDict[filename]
        instance.wait_until_running()
        instance.load()

        instance.terminate()


def populateInstance(filename, projectpath, config, conn_args, fileCount):


    ec2 = boto3.resource('ec2', **conn_args)


    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    code.interact(local=locals())
    count = 0
    pemKey = config.get('info', 'pem')
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



        s = "scp " + "-oStrictHostKeyChecking=no -i " + pemKey + " " + filename + " ubuntu@" + dns + ":" + os.path.basename(filename)
        print s

        p = subprocess.call(s, shell=True)


        s = "scp " + "-oStrictHostKeyChecking=no -i " + pemKey + " " + projectpath + " ubuntu@" + dns + ":/home/ubuntu/" + os.path.basename(projectpath)
        print s
        p = subprocess.call(s, shell=True)

        s = "ssh -i " + pemKey + " ubuntu@" + dns +" \'export LAZYFLOW_TOTAL_RAM_MB=950; /home/ubuntu/ilastik-1.2.0rc6-Linux/run_ilastik.sh --headless --project=/home/ubuntu/" + os.path.basename(projectpath) + " /home/ubuntu/" + os.path.basename(filename)+ "\'"
        print s
        p = subprocess.call(s, shell=True)

        s = "scp " + "-oStrictHostKeyChecking=no -i " + pemKey + " ubuntu@" + dns + ":/home/ubuntu/" + os.path.basename(filename)[:-4] + "_Probabilities.h5 " + os.path.basename(filename)[:-4] + "_Probabilities.h5"
        print s
        p = subprocess.call(s, shell=True)

        instance.terminate()


def spawnInstancesAndWait(numberToSpawn, l, config, conn_args, ec2):
    print "starting " + str(numberToSpawn) + " instances"
    for each in range(numberToSpawn):
        deploy_instance(config, conn_args)
    fileCount = numberToSpawn
 

    count = 0
    print "waiting for instances to spawn..."
    while(count < fileCount):
        count = 0
        instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
        for instance in instances:
            count += 1
    
    process_count = 0
    results= Queue.Queue()
    pemKey = config.get('info', 'pem')   
    

    for instance in instances:
        instance.load()
        dns = instance.public_dns_name
        print dns

        s = "ssh -oStrictHostKeyChecking=no -i " + pemKey + " ubuntu@" + dns +" \'mkdir out; mkdir in\'"
        print s
        #code.interact(local=locals())
        args = shlex.split(s)
        print args
        p = subprocess.Popen(args)
        thread.start_new_thread(process_waiter, (p, instance, results))
        process_count += 1


    while process_count > 0:
        print process_count
        description, rc= results.get()
        print "job", description, "ended with rc =", rc
        if rc != 0:
            instance = description
            #code.interact(local=locals())
            instance.wait_until_running()
        # Reload the instance attributes
            instance.load()
            dns = instance.public_dns_name
            print dns
            s = "ssh -oStrictHostKeyChecking=no -i " + pemKey + " ubuntu@" + dns +" \'mkdir out; mkdir in\'"
            print s
            args = shlex.split(s)
            print args
            p = subprocess.Popen(args)
            thread.start_new_thread(process_waiter, (p, description, results))
        else:
            process_count-= 1

    print "instances ready, sending data!"




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

    numInstances = 2

    conn_args = {
        'aws_access_key_id': config.get('info', 'aws_access_key_id'),
        'aws_secret_access_key': config.get('info', 'aws_secret_access_key'),
        'region_name': config.get('info', 'region_name')
    }
    ec2 = boto3.resource('ec2', **conn_args)


    l = glob.glob(os.path.join(folderpath, "*"))

    spawnInstancesAndWait(numInstances, l, config, conn_args, ec2)

    instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    instanceFileDict = {}

    for ii, instance in enumerate(instances):
        listOfFiles = []
        for each in l[ii::numInstances]:
            listOfFiles.append(each)
        instanceFileDict[instance] = listOfFiles



    loadFiles(config, conn_args, instanceFileDict)

    #loadProjectFiles(projectpath, config, conn_args, instanceFileDict)

    triggerIlastik(l, config, projectpath, instanceFileDict)

    
    retrieveSegmentations(l, instanceFileDict, config)



if __name__ == "__main__":
    main()
