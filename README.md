# ObligatorioDevOps2025

# Ejercicio 2

Este ejercicio consiste en un script de aprovisionamiento de infraestructura en AWS, hecho con python usando el SDK de AWS "Boto3". El objetivo es desplegar automáticamente una arquitectura completa utilizando **Python**, **Boto3**, **Amazon EC2**, **Amazon RDS**, **AWS Systems Manager** y **Security Groups**.

En el repositorio encontraras que el ejercicio se divide en 2 secciones.

app/: Aqui encontraras todos los archivos necesarios para el funcionamiento de la aplicacion.
despliegue-app: Aqui se encuentra el script de aprovisionamiento.

---
## ⚙️ ¿Qué hace el script `ejercicio-2.py`?
El script automatiza **todo** el despliegue de la infraestructura necesaria para la aplicación web.

### 🔹 1. Carga las credenciales AWS desde el entorno
El script usa las variables:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN`
- `AWS_DEFAULT_REGION`

Esto es necesario para autenticarse contra AWS, de otra manera el script no funcionaria.

### 🔹 2. Genera nombres únicos mediante un sufijo aleatorio
Esto permite ejecutar el script múltiples veces sin conflictos:
- `SG-webserver-xxxxxx`
- `SG-bd-xxxxxx`
- `dbwebserver-xxxxxx`

### 🔹 3. Crea los Security Groups
- **SG del WebServer**: expone **80 y 443** al internet.
- **SG de la Base de Datos**: sólo permite tráfico del SG del WebServer.

Ambos SG quedan etiquetados con:
```
Proyecto = ObligatorioDevOps
```

### 🔹 4. Crea la instancia RDS MySQL
- Usa la DB `dbwebserver`
- Genera password aleatorio seguro para el usuario admin
- Espera a que la instancia esté en estado `available`
- Obtiene el endpoint final
- Etiquetada con el tag del proyecto

### 🔹 5. Crea la instancia EC2 Amazon Linux 2023
- Instala Apache, PHP y MySQL Client
- Instala SSM Agent
- Expone la IP pública
- Etiquetada con el tag del proyecto

### 🔹 6. Sube los archivos de la aplicación vía SSM
Los archivos se envían desde el repositorio local a la instancia EC2 mediante `AWS-RunShellScript`.

### 🔹 7. Inicializa la base de datos
Ejecuta automáticamente:
```
mysql -h {db_endpoint} -u {db_username} -p{db_password} dbwebserver < /var/www/init_db.sql
```

### 🔹 8. Crea el archivo `.env`
Conecta la aplicación a RDS:
```
DB_HOST=endpoint de rds
DB_NAME=nombre de la base de datos
DB_USER=usuario de la base de datos
DB_PASS=contrasena de la base de datos
```

### 🔹 9. Reinicia Apache
Deja la aplicación operativa y accesible.

### 🔹 10. Muestra un resumen final
Incluye:
- IDs de SGs creados
- ID de EC2
- Nombre de instancia RDS
- IP pública
- URL de acceso
```
http://<IP_PUBLICA>/login.php
```

---
## ▶️ ¿Cómo ejecutar el script?
### 1. Crear entorno virtual
```
python3 -m venv venv
source venv/bin/activate
```

### 2. Instalar dependencias
```
pip install -r requirements.txt
```

### 3. Exportar credenciales AWS
```
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
export AWS_DEFAULT_REGION=us-east-1

Tambien se puede modificar ~/.aws/credentials y pegar los accesos ahi.
```

### 4. Ejecutar
```
python ejercicio-2.py
```
---
## 🏷️ Uso de Tags
Todos los recursos creados (EC2, SG, RDS) incluyen:
```
Proyecto = ObligatorioDevOps
```
Esto permite:
- Filtrar recursos en AWS
- Identificar qué pertenecen al la infaestructura aprovisionada para el obligatorio
- Facilitar limpieza final
---
## ✨ Conclusión
Este ejercicio implementa un despliegue *end-to-end* profesional utilizando:
- Infraestructura como código en Python/Boto3
- Prácticas de seguridad
- Automatización completa
- Aplicación web funcional
