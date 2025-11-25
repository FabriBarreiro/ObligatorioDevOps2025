
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

if [[ ! -r "$archivo" ]]; then
        echo "ERROR: Error de lectura sobre $archivo" >&2
        exit 6
fi


# Valido que el archivo este correctamente creado

while IFS= read -r linea; do

IFS=':' read -ra campos <<< "$linea"

if [[ ${#campos[@]} -ne 5 ]]; then
    echo "ERROR: línea inválida: $linea" >&2
    echo "la cantidad de campos es distinta de 5" >&2
    exit 7
fi

if [[ -z "${campos[0]}" ]]; then
                echo "Error: línea inválida, usuario vacío" >&2
                exit 8
fi

done < "$archivo"


# Si la estructura del archivo es correcta, creo los usuarios

while IFS=':' read -r usuario comentario home creahome shell; do

    # Valores por defecto si campos están vacíos
    comentario="${comentario:-"-"}"
    home="${home:-/home/$usuario}"
    creahome="${creahome:-NO}"
    shell="${shell:-/bin/bash}"

    comando=(useradd)

    if [ "$comentario" != "-" ]; then
            comando+=(-c "$comentario")
    fi

    comando+=(-d "$home")

    # Crear home si corresponde
    if [ "$creahome" != "NO" ]; then
            comando+=(-m)
    fi

    # Shell
    if ! grep -qxF "$shell" /etc/shells; then
            echo "ERROR: la shell $shell no está en /etc/shells" >&2
            exit 8
    else
            comando+=(-s "$shell")
    fi


    # Usuario
    comando+=("$usuario")

    if "${comando[@]}"; then
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
            fi
    fi

done < "$archivo"

if [[ "$mostrar_info" == true ]]; then
        echo "Se han creado $usuarios_creados usuarios con éxito."
fi
