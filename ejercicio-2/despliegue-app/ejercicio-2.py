import boto3

def obtenerAMI():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    resp = ec2.describe_images(
        Owners=["amazon"],
        Filters=[
            {"Name": "name", "Values": ["al2023-ami-*"]},
            {"Name": "architecture", "Values": ["x86_64"]},
        ]
    )["Images"]

    resp.sort(key=lambda x: x["CreationDate"], reverse=True)
    return resp[0]["ImageId"]

ec2=boto3.client('ec2')
rds=boto3.client('rds')
ssm=boto3.client('ssm')
