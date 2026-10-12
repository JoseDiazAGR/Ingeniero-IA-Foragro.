#!/usr/bin/env python3
"""
Script para crear el primer usuario administrador del dashboard.
Uso: python scripts/create_admin.py
"""

import getpass
import sys
from pathlib import Path

# Asegurar que el paquete `app` esté en el path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_db
from app.security import hash_password


def main():
    print("=== Crear usuario administrador FORAGRO ===")
    username = input("Usuario: ").strip()
    if not username:
        print("El usuario no puede estar vacío.")
        return

    password = getpass.getpass("Contraseña: ")
    confirm = getpass.getpass("Confirmar contraseña: ")

    if password != confirm:
        print("Las contraseñas no coinciden.")
        return

    if len(password) < 8:
        print("La contraseña debe tener al menos 8 caracteres.")
        return

    try:
        password_hash = hash_password(password)
    except ValueError as e:
        print(f"Error: {e}")
        return

    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, password_hash),
            )
            conn.commit()
            print(f"✅ Usuario '{username}' creado exitosamente.")
        except Exception as e:
            print(f"❌ Error creando usuario: {e}")


if __name__ == "__main__":
    main()