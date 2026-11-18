# =====================================================================
# DOCKERFILE - AGILISTA API (PRODUÇÃO / RENDER)
# =====================================================================

# 1. Imagem Base Oficial do Python (Versão Slim: leve, rápida e segura)
FROM python:3.13-slim

# 2. Variáveis de ambiente para comportamento ideal do Python em containers:
#    - PYTHONDONTWRITEBYTECODE: impede a criação de arquivos .pyc
#    - PYTHONUNBUFFERED: envia saídas de log diretamente para o terminal em tempo real
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3. Diretório de trabalho dentro do container
WORKDIR /app

# 4. Instalação de dependências mínimas do sistema (libpq5 para PostgreSQL e curl para healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 5. Otimização de Cache de Camadas do Docker:
#    Copia apenas o requirements.txt primeiro para aproveitar o cache do pip install
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copia os arquivos da aplicação
COPY app/ ./app/
COPY frontend/ ./frontend/
COPY migrations/ ./migrations/
COPY alembic.ini .
COPY criar_admin.py .
COPY main.py .

# 7. Documenta a porta que a aplicação escuta internamente
EXPOSE 8000

# 8. Execução de Migrações no Boot e Inicialização:
#    - alembic upgrade head: garante que as tabelas no PostgreSQL sejam criadas/atualizadas no deploy
#    - uvicorn main:app: inicia o servidor FastAPI na porta dinâmica injetada pelo Render ($PORT)
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]