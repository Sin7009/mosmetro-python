# Используем легкий Python 3.12
FROM python:3.12-slim

# Устанавливаем uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Ставим системные зависимости для PyInstaller
RUN apt-get update && apt-get install -y binutils && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Сначала копируем только файлы зависимостей
COPY pyproject.toml uv.lock ./

# 2. Устанавливаем ТОЛЬКО библиотеки (httpx, pydantic...), не трогая сам проект
# Это позволит Docker закэшировать этот слой, пока не изменятся зависимости
RUN uv sync --frozen --no-install-project

# 3. Теперь копируем весь код, включая README.md и исходники
COPY . .

# 4. Устанавливаем сам проект и PyInstaller
RUN uv sync --frozen
RUN uv pip install pyinstaller

# 5. Собираем бинарник
RUN uv run pyinstaller --onefile --name mosmetro --clean mosmetro/__main__.py \
    --hidden-import=furl \
    --hidden-import=pydantic \
    --hidden-import=user_agent \
    --hidden-import=tenacity \
    --hidden-import=bs4 \
    --hidden-import=httpx \
    --collect-all mosmetro