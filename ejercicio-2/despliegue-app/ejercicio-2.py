import boto3

def obtenerAMI():
    ec2 = boto3.client("ec2")
    resp = ec2.describe_images(
        Owners=["amazon"],
        Filters=[
            {"Name": "name", "Values": ["al2023-ami-*"]},
            {"Name": "architecture", "Values": ["x86_64"]},
        ]
    )["Images"]

    resp.sort(key=lambda x: x["CreationDate"], reverse=True)
    return resp[0]["ImageId"]

ec2 = boto3.client("ec2")
rds = boto3.client("rds")
ssm = boto3.client("ssm")

vpc_id = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"][0]["VpcId"]

instance_profile_webserver = "LabInstanceProfile"

#Crear SG para la instancia de webserver
sg_webserver = ec2.create_security_group(
    GroupName="SG-webserver",
    Description="SG para webserver",
    VpcId=vpc_id
)["GroupId"]

#Permitir los puertos http y https
ec2.authorize_security_group_ingress(
    GroupId=sg_webserver,
    IpPermissions=[
        {
            "IpProtocol": "tcp",
            "FromPort": 80,
            "ToPort": 80,
            "IpRanges": [
                {"CidrIp": "0.0.0.0/0"}
            ],
        },
        {
            "IpProtocol": "tcp",
            "FromPort": 443,
            "ToPort": 443,
            "IpRanges": [
                {"CidrIp": "0.0.0.0/0"}
            ],
        },
    ],
)

# Crear webserver
ami_id = obtenerAMI()

comandos_iniciales = """#!/bin/bash
sudo dnf clean all
sudo dnf makecache
sudo dnf -y update
sudo dnf -y install amazon-ssm-agent || true
sudo systemctl enable --now amazon-ssm-agent || true
sudo dnf -y install httpd php php-cli php-fpm php-common php-mysqlnd mariadb105
sudo systemctl enable --now httpd
sudo systemctl enable --now php-fpm

echo '<FilesMatch \\.php$>
  SetHandler "proxy:unix:/run/php-fpm/www.sock|fcgi://localhost/"
</FilesMatch>' | sudo tee /etc/httpd/conf.d/php-fpm.conf

echo "<?php phpinfo(); ?>" | sudo tee /var/www/html/info.php

sudo systemctl restart httpd php-fpm
"""

ec2_webserver = ec2.run_instances(
    ImageId=ami_id,
    InstanceType="t2.micro",
    MinCount=1,
    MaxCount=1,
    SecurityGroupIds=[sg_webserver],
    IamInstanceProfile={"Name": instance_profile_webserver},
    UserData=comandos_iniciales,
 )["Instances"][0]["InstanceId"]


# Esperar a que la instancia esté en estado "running" y pase los status checks
waiter = ec2.get_waiter('instance_status_ok')
waiter.wait(InstanceIds=[ec2_webserver])

# Obtener la IP pública
info_webserver = ec2.describe_instances(InstanceIds=[ec2_webserver])
ip_publica_webserver = info_webserver["Reservations"][0]["Instances"][0]["PublicIpAddress"]

print("El script se ejecuto correctamente.")
print("")
print(f"Security Group creado: {sg_webserver} (Nombre: SG-webserver)")
print(f"Instancia EC2 creada: {ec2_webserver}")
print(f"IP pública de la instancia: {ip_publica_webserver}")
