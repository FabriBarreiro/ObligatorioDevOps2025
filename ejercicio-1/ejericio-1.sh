#!/bin/bash

#Variables

mostrar_info=false
password=""
archivo=""

#Validaciones

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
            password="$2"
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



