# Используем легкий Python 3.12
FROM python:3.12-slim

# Устанавливаем uv (самый быстрый менеджер пакетов)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Ставим системные зависимости для PyInstaller (binutils нужен для сборки загрузчика)
RUN apt-get update && apt-get install -y binutils && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Сначала копируем файлы зависимостей (для кэширования слоев Docker)
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости проекта + PyInstaller
RUN uv sync --frozen
RUN uv pip install pyinstaller

# Копируем весь остальной код
COPY . .

# Собираем бинарник в один файл
# --hidden-import нужны, так как PyInstaller иногда теряет эти либы
RUN uv run pyinstaller --onefile --name mosmetro --clean mosmetro/__main__.py \
    --hidden-import=furl \
    --hidden-import=pydantic \
    --hidden-import=user_agent \
    --hidden-import=tenacity \
    --hidden-import=bs4 \
    --hidden-import=httpx \
    --collect-all mosmetro