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

## References

* http://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2.html
* http://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html
* http://docs.aws.amazon.com/cli/latest/userguide/cli-iam-policy.html
