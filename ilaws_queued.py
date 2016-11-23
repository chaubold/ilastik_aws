import boto3
from botocore.client import Config
import botocore
import sys
import os
import ConfigParser
import glob
import zipfile
import time

def main():
    if len(sys.argv) < 3:
        print "-------------------------------------------------------------"
        print "ilaws -- a wrapper for AWS for launching ilastik segmentation on the cloud\n"
        print "USAGE: python ilaws_queued.py <path to directory with input data> <path to ilastik project file>\n"
        print "Originally by michael morehead @ ilastik workshop 2016,"
        print "Adjusted to use Amazon's SQS and S3 by Carsten Haubold, 2016"
        print "-------------------------------------------------------------"
        sys.exit()
    folderPath = sys.argv[1]
    projectPath = sys.argv[2]
    config = ConfigParser.ConfigParser()
    config.read("./config.ini")
    bucketName = config.get('info', 'bucket')

    print("Setting up connection")
    conn_args = {
        'aws_access_key_id': config.get('info', 'aws_access_key_id'),
        'aws_secret_access_key': config.get('info', 'aws_secret_access_key'),
        'region_name': config.get('info', 'region_name')
    }

    # messaging queues: set up and remove all previous messages
    sqs = boto3.resource('sqs', **conn_args)
    taskQueue = sqs.get_queue_by_name(QueueName='ilastik-task-queue')
    finishedQueue = sqs.get_queue_by_name(QueueName='ilastik-finished-queue')
    try:
        taskQueue.purge()
        finishedQueue.purge()
    except botocore.exception.ClientError:
        print("Could not purge message queues, might not have waited 60 seconds in between")
    
    # WARNING: the signature_version needs to be adjusted for eu-central-1, no idea whether that also works for us
    s3 = boto3.client('s3', config=Config(signature_version='s3v4'), **conn_args)

    # upload ilastik project file as zip
    if not projectPath.endswith('.zip'):
        print("Zipping ilastik project file")
        with zipfile.ZipFile(projectPath+'.zip', 'w') as z:
            z.write(projectPath)
        projectPath += '.zip'
    print("Uploading ilastik project file")
    s3.upload_file(projectPath, bucketName, "ilastik-project-zip")
    
    filesToProcess = glob.glob(os.path.join(folderPath, "*"))
    remainingKeys = []

    # dispatch work
    print("Dispatching jobs:")
    for index, fileFullPath in enumerate(filesToProcess):
        if not os.path.isfile(fileFullPath):
            print("Skipping {}, is no file".format(fileFullPath))
            continue
        
        # upload data and project file
        filename = os.path.basename(fileFullPath)
        fileKey = "image-{}".format(index)
        print("Uploading {} to {}:{}".format(filename, bucketName, fileKey))
        s3.upload_file(fileFullPath, bucketName, fileKey)
        

        # send message about task:
        taskQueue.send_message(MessageBody=filename, MessageAttributes={
            'ilp-key': {
                'StringValue':'ilastik-project-zip', 
                'DataType': 'String'
            }, 
            'file-key': {
                'StringValue':fileKey,
                'DataType': 'String'
            }
        })
        
        remainingKeys.append(fileKey)
    print("\n*********************\nDone dispatching all tasks\n*********************\n")

    # wait for all results:
    try:
        print("Waiting for results")
        while len(remainingKeys) > 0:
            for message in finishedQueue.receive_messages(MessageAttributeNames=['result-key', 'file-key', 'log-key'], MaxNumberOfMessages=1):
                # Get the custom author message attribute if it was set
                if message.message_attributes is not None:
                    resultFileKey = message.message_attributes.get('result-key').get('StringValue')
                    inputFileKey = message.message_attributes.get('file-key').get('StringValue')
                    logFileKey = message.message_attributes.get('log-key').get('StringValue')
                else:
                    print("Got unknown message {}".format(message))

                filename = message.body
                print("Got result for {} = {}, downloading...".format(message.body, inputFileKey))

                # download file and remove from s3
                try:
                    if resultFileKey != 'ERROR':
                        s3.download_file(bucketName, resultFileKey, os.path.join(folderPath, 'result_' + filename))
                        s3.delete_object(Bucket=bucketName, Key=resultFileKey)
                    else:
                        print("Input file {} finished with errors, see the log file".format(filename))
                    s3.download_file(bucketName, logFileKey, os.path.join(folderPath, 'log_' + filename + '.txt'))
                    s3.delete_object(Bucket=bucketName, Key=logFileKey)
                    message.delete()
                except botocore.exceptions.ClientError:
                    print("Could not find result file {} to download".format(filename))
                    message.delete()
                    continue

                assert(inputFileKey in remainingKeys)
                remainingKeys.remove(inputFileKey)

    except KeyboardInterrupt:
        print("WARNING: not all results have been fetched yet, but will still be computed, and the results will be stored in S3")
    
    
    try:
        print("Deleting ilastik project file on server")
        s3.delete_object(Bucket=bucketName, Key="ilastik-project-zip")
    except botocore.exceptions.ClientError:
        print("Could not delete ilastik project file from S3")

    print("\n*********************\nDone!\n*********************\n")

if __name__ == "__main__":
    main()
