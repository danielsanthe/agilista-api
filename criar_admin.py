
"""
Script para cadastrar um usuário administrador no AgiLista.
Executar na raiz do projeto agilista-api.
"""

from getpass import getpass
from datetime import datetime

from pwdlib import PasswordHash
from sqlmodel import Session, select

from app.database import engine
from app.models.usuario import Usuario


def criar_admin():

    print("\n=== Cadastro de Administrador AgiLista ===\n")

    nome = input("Nome completo: ").strip()
    email = input("E-mail: ").strip().lower()

    if not nome or not email:
        print("Nome e e-mail são obrigatórios.")
        return

    senha = getpass("Digite a senha: ")
    confirmacao = getpass("Confirme a senha: ")

    if not senha:
        print("A senha não pode ficar vazia.")
        return

    if senha != confirmacao:
        print("As senhas não conferem.")
        return

    password_hash = PasswordHash.recommended()
    senha_hash = password_hash.hash(senha)

    with Session(engine) as session:

        usuario_existente = session.exec(
            select(Usuario).where(Usuario.email == email)
        ).first()

        if usuario_existente:
            print("Já existe um usuário cadastrado com esse e-mail.")
            return

        administrador = Usuario(
            nome_usuario=nome,
            email=email,
            senha_hash=senha_hash,
            tipo_plano="FreeTrial",
            tipo_usuario="ADMIN",
            flag_sincronizado=1,
            data_cadastro=datetime.now().isoformat()
        )

        try:
            session.add(administrador)
            session.commit()
            session.refresh(administrador)

            print("\nAdministrador cadastrado com sucesso!")
            print(f"ID: {administrador.id_usuario}")
            print(f"Nome: {administrador.nome_usuario}")
            print(f"E-mail: {administrador.email}")
            print(f"Perfil: {administrador.tipo_usuario}")

        except Exception:
            session.rollback()
            raise


if __name__ == "__main__":
    criar_admin()
