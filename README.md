# Собачьи отмазки

Telegram-бот собирает отмазки для владельцев собак из трёх согласованных слотов:
ситуационного зачина, цельной причины и подходящего финала. В каталоге 344 уникальных
фрагмента и 8 928 комбинаций без LLM и внешних AI API.

## Локальный запуск

Требуется Python 3.12.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp .env.example .env
# заполнить BOT_TOKEN и USER_HASH_SECRET
.venv/bin/alembic upgrade head
.venv/bin/dog-excuses
```

В BotFather для бота необходимо включить inline mode (`/setinline`), иначе кнопка
«Поделиться» не сможет отправлять результат в другой чат.

## Проверки

```bash
ruff check .
ruff format --check .
mypy .
pytest
docker build -t dog-excuses-bot .
```

## Docker Compose

```bash
cp .env.example .env
docker compose up --build -d
```

SQLite хранится в именованном volume `bot-data`. Контейнер применяет миграции перед
каждым запуском.

## Production CI/CD

Workflow `.github/workflows/ci-cd.yml` выполняет проверки, собирает готовый образ в
GitHub Actions, публикует его в GHCR с неизменяемым тегом commit SHA и разворачивает
на сервере `89.125.250.84` только после успешной сборки.

Production использует отдельный Compose-проект `pesdnyak` и каталог `/opt/pesdnyak`.
Он не публикует порты, не подключается к сетям других проектов и не выполняет
`docker compose down` или глобальный `docker system prune`. SQLite хранится в
`/opt/pesdnyak/data`, независимо от release-каталогов.

В GitHub repository settings необходимо создать environment `production` и добавить
в него secrets:

- `BOT_TOKEN` — токен `@PesdnyakBot`;
- `USER_HASH_SECRET` — длинная случайная строка для HMAC;
- `DEPLOY_SSH_PRIVATE_KEY` — приватный ключ, соответствующий разрешённому на сервере;
- `DEPLOY_KNOWN_HOSTS` — закреплённая строка known_hosts для `89.125.250.84`.

Публичный ключ сервера для `DEPLOY_KNOWN_HOSTS` следует сверить с уже доверенным
локальным подключением, например через `ssh-keygen -F 89.125.250.84 ~/.ssh/known_hosts`.
Workflow сам формирует `/opt/pesdnyak/shared/runtime.env` из secrets на каждом деплое;
runtime-файл не хранится в Git и имеет права `600`.

Первый production-деплой запускается push-коммитом в `main` или вручную через
`workflow_dispatch` на ветке `main`. Перед ним обязательно остановить локально
запущенный экземпляр `@PesdnyakBot`: Telegram допускает только один long-polling
процесс с одним токеном.

Release-скрипт сначала загружает образ, затем переключает `/opt/pesdnyak/current`,
ожидает healthy-состояния контейнера и при ошибке возвращает предыдущий release.
