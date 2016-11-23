Here are the steps I took to get access to AWS services from an EC2 instance:

1. Create a new policy that grants permission to assign and pass roles to EC2 instances
   * in the IAM control panel, go to `policies`
   * `Create Policy` -> `Create your own policy`
   * give it some name, and in the `Document`, paste the following:

        ```json
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:PassRole",
                        "iam:ListInstanceProfiles",
                        "ec2:*"
                    ],
                    "Resource": "*"
                }
            ]
        }
        ```

2. Give your user permission to assign roles to instances:
   * in the IAM control panel, go to `users`, select your user (you should have created one!)
   * in `permissions`, click `attach policy` and use your newly created policy 
     (you can filter your own at the top with `Policy Type -> Customer Managed Policies`)
   
3. Create a new role for EC2 instances
   * in the IAM control panel, go to `roles`
   * create a new role
   * attach the policies you need for your instances (e.g. `AmazonSQSFullAccess`, `AmazonS3FullAccess`, ...)

4. Launch a new EC2 instance with the new role
   * in the EC2 Management Console, click `Launch Instance`, select your favorite OS
   * do not skip all the configuration panels, but in the `Instance Profiles` or `IAM Roles` field, 
     select the role created in the step before!

5. Use `boto3` on the instances to connect to the respective services (and you probably need to specify a region),
   **no need to configure the credentials with the `aws` command line tool**, 
   e.g.:

    ```py
    import boto3
    sqs = boto3.resource('sqs', region_name='eu-central-1')
    for queue in sqs.queues.all():
        print(queue.url)
    ``` 

## Doing all of the above from python using boto3:

** requires the logged in user (specified in `~/.aws/credentials`) to have the `AdministratorAccess` policy! **

```py
# setup
import boto3
iam = boto3.resource('iam')
ec2 = boto3.resource('ec2')
iamClient = boto3.client('iam')
ec2Client = boto3.client('ec2')

# new user
iamClient.create_user(UserName='ilastikuser')

# policy that allows the current user to assign instance profiles to instances:
doc='''{"Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole",
                "iam:ListInstanceProfiles",
                "ec2:*"
            ],
            "Resource": "*"
        }
    ]
}'''

policy = iamClient.create_policy(PolicyName='ilastikInstanceRole', PolicyDocument=doc)

# give the policy to the user
iamClient.create_access_key(UserName='ilastikuser')
iu = iam.User('ilastikuser')
iu.attach_policy(PolicyArn=policy['Policy']['Arn'])

roleDoc = '''{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {"Service": "ec2.amazonaws.com" },
      "Effect": "Allow"
    }
  ]
}'''

# create the role with full SQS and S3 access:
iamClient.create_role(RoleName='ilastikInstanceRole', AssumeRolePolicyDocument=roleDoc)
role = iam.Role('ilastikInstanceRole')
role.attach_policy(PolicyArn='arn:aws:iam::aws:policy/AmazonSQSFullAccess')
role.attach_policy(PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess')

# create a security group that allows SSH access (tcp port 22) from everywhere to our instances:
ec2Client.create_security_group(GroupName='ilastikFirewallSettingsSecurityGroup', Description='Security Group for ilastik that allows SSH access for debugging')
ec2Client.authorize_security_group_ingress(GroupName='ilastikFirewallSettingsSecurityGroup',IpProtocol='tcp',FromPort=22,ToPort=22, CidrIp='0.0.0.0/0')

# create an instance profile from the role
instanceProfile = iamClient.create_instance_profile(InstanceProfileName='ilastikInstanceProfile')
iamClient.add_role_to_instance_profile(InstanceProfileName='ilastikInstanceProfile', RoleName='ilastikInstanceRole')

# create an instance using the instance profile and some existing amazon machine image (AMI).
# Instance will be booted immediately!
instances = ec2.create_instances(ImageId='', # specify a machine image
                                 MinCount=1, # choose a larger number here if you want more than one instance!
                                 MaxCount=1,
                                 KeyName='', # specify an SSH key pair that you have created in the AWS console to be able to SSH to the machine. Comment out if not needed.
                                 InstanceType='t2.micro' # select the instance type
                                 SecurityGroups=['ilastikFirewallSettingsSecurityGroup'],
                                 IamInstanceProfile={'Name':'ilastikInstanceProfile'})

# to stop the instance: (remains available as configured machine, can be started again)
ec2Client.stop_instances(InstanceIds=[instances[0].id])

# to terminate the instance: (will be gone after some time after shutdown)
ec2Client.terminate_instances(InstanceIds=[instances[0].id])

# to figure out the dns name or IP:
instances[0].load()
instances[0].public_ip_address
instances[0].public_dns_name

# lastly set up the message queues and S3 bucket:
sqs = boto3.resource('sqs', **conn_args)
```

## References

* http://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2.html
* http://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html