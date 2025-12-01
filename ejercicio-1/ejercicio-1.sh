#!/bin/bash

#Variables

mostrar_info=false
contrasena=""
archivo=""
usuarios_creados=0


#Validaciones

if [[ $EUID -ne 0 ]]; then
    echo "ERROR: Debes ejecutar este script como root" >&2
    exit 10
fi



while [[ $# -gt 0 ]]; do
    case "$1" in
        -i)
            mostrar_info=true
            shift
        ;;
        -c)
            if [[ -z "$2" ]]; then
                echo "ERROR: falta contraseña para -c" >&2
                exit 1
            fi
            contrasena="$2"
            shift 2
        ;;
        -*)
            echo "ERROR: modificador inválido $1" >&2
            exit 2
        ;;
        *)
            archivo="$1"
            shift
        ;;
    esac
done

if [[ -z "$archivo" ]]; then
    echo "ERROR: debe indicar el archivo con los usuarios a crear" >&2
    exit 3
fi

if [[ ! -e "$archivo" ]]; then
    echo "ERROR: el archivo $archivo no existe" >&2
    exit 4
fi


if [[ ! -f "$archivo" ]]; then
            echo "ERROR: $archivo no es un archivo regular" >&2
    exit 5
fi

permisos=$(stat -c "%A" "$archivo")

owner_read=${permisos:1:1}
group_read=${permisos:4:1}
others_read=${permisos:7:1}

if [[ "$owner_read" != "r" && "$group_read" != "r" && "$others_read" != "r" ]]; then
    echo "ERROR: el archivo no tiene permiso de lectura"
    exit 6
fi

#Proceso todas las lineas
while IFS= read -r linea; do

errores=false

    # Validar cantidad EXACTA de ":" → deben ser 4
    cant_dos_puntos=$(grep -o ":" <<< "$linea" | wc -l)

    if [[ "$cant_dos_puntos" -ne 4 ]]; then
        echo "ERROR: línea inválida cantidad de campos incorrecta: $linea" >&2
        errores=true
        echo "ATENCION: el usuario $(cut -d':' -f1 <<< "$linea") no pudo ser creado"
        echo ""
        continue   #sigue con la siguiente linea
    fi

    #leer los 5 campos
    IFS=':' read -r usuario comentario home creahome shell <<< "$linea"

    if [[ -z "$usuario" ]]; then
        echo "Error: línea inválida, usuario vacío" >&2
        errores=true
    fi


    # Valores por defecto si campos están vacíos
    if [[ -z "$comentario" ]]; then
        comentario=""
    fi

    if [[ -z "$home" ]]; then
        home="/home/$usuario"
    fi

    if [[ -z "$creahome" ]]; then
        creahome="SI"
    fi

    if [[ -z "$shell" ]]; then
        shell="/bin/bash"
    fi

    #Conierte a mayusculas el texto para siempre compararlo en mayusculas
    creahome="${creahome^^}"

    comando=(useradd)

    if [ "$comentario" != "" ]; then
        comando+=(-c "$comentario")
    fi

    comando+=(-d "$home")

    # Crear home si corresponde
    if [[ "$creahome" != "SI" && "$creahome" != "NO" ]]; then
        echo "ERROR: campo CREAR_HOME inválido: $creahome" >&2
        errores=true
    fi

    if [ "$creahome" == "SI" ]; then
        comando+=(-m)

    fi

   if [ "$creahome" == "NO" ]; then
        comando+=(-M)
   fi

 # Validar home existente si corresponde

   if [[ "$creahome" == "NO" && ! -d "$home" ]]; then
     echo "ERROR: el home $home no existe y creahome=NO" >&2
     errores=true
   fi

    if [[ "$creahome" == "SI" && -e "$home" ]]; then
        echo "ERROR: el home $home ya existe, no se puede crear" >&2
        errores=true
    fi

    # Shell
   if ! grep -qxF "$shell" /etc/shells; then
    echo "Atencion: la shell $shell no está en /etc/shells" >&2
   fi

comando+=(-s "$shell")

    # Usuario
    if id "$usuario" &>/dev/null; then
        echo "ERROR: El usuario $usuario ya existe" >&2
        errores=true
    else
        comando+=("$usuario")
    fi

    if [[ "$errores" == false  ]]; then
        if "${comando[@]}" &>/dev/null; then
            usuarios_creados=$((usuarios_creados+1))
            # Asignar contraseña si se pasó -c
            if [ -n "$contrasena" ]; then
                echo "$usuario:$contrasena" | chpasswd
            fi

            if [[ "$mostrar_info" == true ]]; then
                echo "Usuario $usuario creado con éxito con datos indicados:"
                echo "Comentario: $comentario"
                echo "Dir home: $home"
                echo "Asegurado existencia de directorio home: $creahome"
                echo "Shell por defecto: $shell"
                echo
            fi
        else
            if [[ "$mostrar_info" == true ]]; then
                echo "ATENCION: el usuario $usuario no pudo ser creado"
                echo ""
            fi
        fi
    else
        echo "ATENCION: el usuario $usuario no pudo ser creado"
        echo ""
    fi

done < "$archivo"

if [[ "$mostrar_info" == true ]]; then
    echo "Se han creado $usuarios_creados usuarios con éxito."
fi
