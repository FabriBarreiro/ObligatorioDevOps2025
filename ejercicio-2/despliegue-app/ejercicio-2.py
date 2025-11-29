import boto3
import base64
import secrets
import string
from pathlib import Path

#Generar una contraseña segura aleatoria para la BD
def generar_password(longitud: int = 20) -> str:
    caracteres = string.ascii_letters + string.digits + "!#$%^&*()-_=+"
    return "".join(secrets.choice(caracteres) for _ in range(longitud))

#Generar un sufijo corto para nombres únicos de recursos
def generar_sufijo(longitud: int = 6) -> str:
    caracteres = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(caracteres) for _ in range(longitud))

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

#Obtener la ultima AMI de AL2023
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

sufijo = generar_sufijo()

sg_web_name = f"SG-webserver-{sufijo}"
sg_rds_name = f"SG-bd-{sufijo}"
db_identifier = f"dbwebserver-{sufijo}"

#Rutas relativas al repositorio
#El objetivo de esto es que el script funcione en cualquier equipo que clone el repo, independientemente de la ruta absoluta de los archivos de la app
BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR.parent / "app"

#Obtener el id de la VPC default
vpc_id = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"][0]["VpcId"]

instance_profile_webserver = "LabInstanceProfile"

#Crear SG para la instancia de webserver
sg_webserver = ec2.create_security_group(
    GroupName=sg_web_name,
    Description="SG para webserver",
    VpcId=vpc_id
)["GroupId"]

# Tag de SG_WEBSERVER
ec2.create_tags(
    Resources=[sg_webserver],
    Tags=[{"Key": "Proyecto", "Value": "ObligatorioDevOps"}]
)

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

#Crear SG para la base de datos RDS (solo acepta tráfico desde el SG del webserver)
sg_rds = ec2.create_security_group(
    GroupName=sg_rds_name,
    Description="SG para base de datos MySQL",
    VpcId=vpc_id
)["GroupId"]

# Tageo de SG_RDS
ec2.create_tags(
    Resources=[sg_rds],
    Tags=[{"Key": "Proyecto", "Value": "ObligatorioDevOps"}]
)

#Permitir solo MySQL (3306) desde el SG del webserver
ec2.authorize_security_group_ingress(
    GroupId=sg_rds,
    IpPermissions=[
        {
            "IpProtocol": "tcp",
            "FromPort": 3306,
            "ToPort": 3306,
            "UserIdGroupPairs": [
                {"GroupId": sg_webserver},
            ],
        },
    ],
)

# Generar credenciales seguras para la BD (sin hardcodear en el código)
db_username = "admin"
db_password = generar_password()

# Crear instancia RDS MySQL para usar de BD del webserver
rds.create_db_instance(
    DBName="dbwebserver",
    DBInstanceIdentifier=db_identifier,
    AllocatedStorage=20,
    DBInstanceClass="db.t3.micro",
    Engine="mysql",
    MasterUsername=db_username,
    MasterUserPassword=db_password,
    VpcSecurityGroupIds=[sg_rds],
    PubliclyAccessible=False,
    BackupRetentionPeriod=1,
    MultiAZ=False,
    StorageType="gp2",
    AutoMinorVersionUpgrade=True,
)

# Esperar a que la instancia RDS esté disponible
waiter_rds = rds.get_waiter("db_instance_available")
waiter_rds.wait(DBInstanceIdentifier=db_identifier)

# Obtener endpoint de la base de datos
info_rds = rds.describe_db_instances(DBInstanceIdentifier=db_identifier)

# Tageo de RDS
rds.add_tags_to_resource(
    ResourceName=f"arn:aws:rds:us-east-1:{info_rds['DBInstances'][0]['DBInstanceArn'].split(':')[4]}:db:{db_identifier}",
    Tags=[{"Key": "Proyecto", "Value": "ObligatorioDevOps"}]
)

db_endpoint = info_rds["DBInstances"][0]["Endpoint"]["Address"]
db_port = info_rds["DBInstances"][0]["Endpoint"]["Port"]

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

# Tageo de EC2
ec2.create_tags(
    Resources=[ec2_webserver],
    Tags=[{"Key": "Proyecto", "Value": "ObligatorioDevOps"}]
)


# Esperar a que la instancia esté en estado "running" y pase los status checks
waiter = ec2.get_waiter('instance_status_ok')
waiter.wait(InstanceIds=[ec2_webserver])

#Subir archivos PHP/HTML/CSS/JS al webroot
for file in APP_DIR.iterdir():
    if file.suffix in [".php", ".html", ".css", ".js"]:
        subir_archivos_webserver(ec2_webserver, str(file), f"/var/www/html/{file.name}")

#Subir init_db.sql fuera del webroot
subir_archivos_webserver(ec2_webserver, str(APP_DIR / "init_db.sql"), "/var/www/init_db.sql")

#Se aseguran permisos, se inicializa la bd, se crea .env y se reinicia apache
resp_cmd = ssm.send_command(
    InstanceIds=[ec2_webserver],
    DocumentName="AWS-RunShellScript",
    Parameters={
        "commands": [
            "sudo chown -R apache:apache /var/www/html",
            "sudo chown apache:apache /var/www/init_db.sql",
            "sudo chmod 600 /var/www/init_db.sql",
            f"mysql -h {db_endpoint} -u {db_username} -p{db_password} dbwebserver < /var/www/init_db.sql",
            f"printf 'DB_HOST={db_endpoint}\nDB_NAME=demo_db\nDB_USER=demo_user\nDB_PASS=demo_pass\n\nAPP_USER=admin\nAPP_PASS=admin123\n' | sudo tee /var/www/.env >/dev/null",
            "sudo chown apache:apache /var/www/.env",
            "sudo chmod 600 /var/www/.env",
            "sudo systemctl restart httpd php-fpm",
        ]
    },
)

# Esperar a que el comando termine correctamente
command_id = resp_cmd["Command"]["CommandId"]

import time
while True:
    inv = ssm.get_command_invocation(CommandId=command_id, InstanceId=ec2_webserver)
    if inv["Status"] in ["Success", "Failed", "Cancelled", "TimedOut"]:
        break
    time.sleep(2)

# Obtener la IP pública
info_webserver = ec2.describe_instances(InstanceIds=[ec2_webserver])
ip_publica_webserver = info_webserver["Reservations"][0]["Instances"][0]["PublicIpAddress"]

print("El script se ejecutó correctamente.")
print("")
print("===== RESUMEN DE RECURSOS CREADOS =====")
print(f"- Security Group web creado: {sg_webserver} (Nombre: {sg_web_name})")
print(f"- Security Group BD creado: {sg_rds} (Nombre: {sg_rds_name})")
print(f"- Instancia RDS creada: {db_identifier} (DBName: dbwebserver)")
print(f"- Instancia EC2 creada: {ec2_webserver}")
print("")
print("Acceso a la app:")
print(f"  -> http://{ip_publica_webserver}/login.php")
print("=======================================")
