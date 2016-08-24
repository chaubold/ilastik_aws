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
    sqs = boto3.resource('sqs', region_name='eu-central-1')
    taskQueue = sqs.get_queue_by_name(QueueName='ilastik-task-queue')
    finishedQueue = sqs.get_queue_by_name(QueueName='ilastik-finished-queue')

    # set up S3 connection, the signature_version needs to be adjusted for eu-central-1 !
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
                try:
                    s3.download_file("chauboldtestbucket", ilastikProjectKey, "ilastikproject.zip")
                except botocore.exceptions.ClientError:
                    print("Could not find ilastik project download")
                    message.delete()
                    continue

                try:
                    s3.download_file("chauboldtestbucket", inputFileKey, filename)
                    s3.delete_object(Bucket='chauboldtestbucket', Key=inputFileKey)
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
                my_env["LAZYFLOW_TOTAL_RAM_MB"] = "950"
                command = "{}/run_ilastik.sh --headless --project=ilastikproject.ilp --output_filename_format=result.h5 {}".format(ilastikPath, filename)
                print("Running " + command)
                subprocess.check_call(command.split(' '), env=my_env)

                outputFileKey = inputFileKey + '_result'
                # s3.upload_file('result.h5', 'chauboldtestbucket', outputFileKey)
                print("Simulating processing")
                time.sleep(2)

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