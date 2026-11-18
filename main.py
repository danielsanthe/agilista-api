"""
Ponto de entrada da aplicação AgiLista.

Permite iniciar o servidor utilizando:

    py -m uvicorn main:app --reload

Este arquivo importa a aplicação criada em app/main.py.
"""

# Importa o objeto app do arquivo principal da aplicação.
from app.main import app


# Define que o objeto app poderá ser importado
# diretamente deste módulo.
__all__ = ["app"]