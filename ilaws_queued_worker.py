import boto3
from botocore.client import Config
import botocore
import ConfigParser
import subprocess
import zipfile
import os
import time

if __name__ == "__main__":
    # load config
    config = ConfigParser.ConfigParser()
    config.read("./config.ini")
    ilastikPath = config.get('info', 'ilastikPath')
    assert(ilastikPath.count(' ') == 0)
    bucketName = config.get('info', 'bucket')

    # set up queues
    sqs = boto3.resource('sqs', region_name=config.get('info', 'region_name'))
    taskQueue = sqs.get_queue_by_name(QueueName='ilastik-task-queue')
    finishedQueue = sqs.get_queue_by_name(QueueName='ilastik-finished-queue')

    # set up S3 connection
    # WARNING: the signature_version needs to be adjusted for eu-central-1, no idea whether that also works for us
    s3 = boto3.client('s3', config=Config(signature_version='s3v4'))

    try:
        while True:
            for message in taskQueue.receive_messages(MessageAttributeNames=['ilp-key', 'file-key'], MaxNumberOfMessages=1):
                # Get the custom author message attribute if it was set
                if message.message_attributes is not None:
                    ilastikProjectKey = message.message_attributes.get('ilp-key').get('StringValue')
                    inputFileKey = message.message_attributes.get('file-key').get('StringValue')
                else:
                    print("Got unknown message {}".format(message))
                
                # get rid of spaces in filename 
                filename = (message.body).replace(' ', '')
                print("Got {}, for project {} and file key {}, downloading...".format(filename, ilastikProjectKey, inputFileKey))
                
                # download ilasik project
                try:
                    s3.download_file(bucketName, ilastikProjectKey, "ilastikproject.zip")
                except botocore.exceptions.ClientError:
                    print("Could not find ilastik project download")
                    message.delete()
                    continue
                
                # download raw data file
                try:
                    s3.download_file(bucketName, inputFileKey, filename)
                    s3.delete_object(Bucket=bucketName, Key=inputFileKey)
                except botocore.exceptions.ClientError:
                    print("Could not find raw data file to download")
                    message.delete()
                    continue

                # unzip ilp and give it our default name
                with zipfile.ZipFile('ilastikproject.zip', 'r') as z:
                    assert(len(z.namelist()) == 1)
                    originalFileName = z.namelist()[0]
                    z.extract(originalFileName)
                    os.rename(originalFileName, 'ilastikproject.ilp')

                # run shell command
                my_env = os.environ.copy()
                my_env["LAZYFLOW_TOTAL_RAM_MB"] = config.get('info', 'maxRam')
                command = "{}/run_ilastik.sh --headless --project=ilastikproject.ilp --output_filename_format=result.h5 {}".format(ilastikPath, filename)
                print("Running " + command)
                subprocess.check_call(command.split(' '), env=my_env)

                # upload result
                outputFileKey = inputFileKey + '_result'
                s3.upload_file('result.h5', bucketName, outputFileKey)

                # clean up
                os.remove('ilastikproject.zip')
                os.remove('ilastikproject.ilp')
                os.remove(filename)
                os.remove('result.h5')

                # Let the queue know that the message is processed
                message.delete()

                # send a reply
                print("Sending a reply for job {}".format(filename))
                finishedQueue.send_message(MessageBody=filename, MessageAttributes={
                    'file-key': {
                        'StringValue':inputFileKey,
                        'DataType': 'String'
                    },
                    'result-key': {
                        'StringValue':outputFileKey,
                        'DataType': 'String'
                    }
                })

    except KeyboardInterrupt:
        print("Shutting down ilastik worker")