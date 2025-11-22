import boto3
import base64
from pathlib import Path

#Subida de un archivo local a la instancia EC2 usando SSM
def subir_archivos_webserver(instance_id, ruta_local, ruta_remota):
    # Leer archivo local en binario
    with open(ruta_local, "rb") as f:
        contenido = f.read()

    #Codificar en Base64 para enviarlo seguro vía SSM
    contenido_b64 = base64.b64encode(contenido).decode()

    #Comando que se ejecuta en el webserver: decodifica y escribe el archivo en destino
    comando = f"echo '{contenido_b64}' | base64 -d | sudo tee {ruta_remota} >/dev/null"

    #Ejecutar el comando en webserver mediante AWS SSM
    ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [comando]},
    )

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

# Rutas relativas al repositorio
BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR.parent / "app"


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

#Crear webserver
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

# Subir archivos PHP/HTML/CSS/JS al webroot
for file in APP_DIR.iterdir():
    if file.suffix in [".php", ".html", ".css", ".js"]:
        subir_archivos_webserver(ec2_webserver, str(file), f"/var/www/html/{file.name}")

# Subir init_db.sql fuera del webroot
subir_archivos_webserver(ec2_webserver, str(APP_DIR / "init_db.sql"), "/var/www/init_db.sql")

# Ajustar permisos y reiniciar Apache
ssm.send_command(
    InstanceIds=[ec2_webserver],
    DocumentName="AWS-RunShellScript",
    Parameters={
        "commands": [
            "sudo chown -R apache:apache /var/www/html",
            "sudo chown apache:apache /var/www/init_db.sql",
            "sudo chmod 600 /var/www/init_db.sql",
            "sudo systemctl restart httpd php-fpm",
        ]
    },
)

# Obtener la IP pública
info_webserver = ec2.describe_instances(InstanceIds=[ec2_webserver])
ip_publica_webserver = info_webserver["Reservations"][0]["Instances"][0]["PublicIpAddress"]

print("El script se ejecuto correctamente.")
print("")
print(f"Security Group creado: {sg_webserver} (Nombre: SG-webserver)")
print(f"Instancia EC2 creada: {ec2_webserver}")
print(f"IP pública de la instancia: {ip_publica_webserver}")
