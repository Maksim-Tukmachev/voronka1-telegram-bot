# voronka1-telegram-bot

Минимальная Telegram-воронка: `/start` → проверка подписки на канал → ссылка на видео → отложенное напоминание про бесплатный разбор стратегии.

Стек: **Python 3.10+**, **aiogram 3**.

GitHub хранит только код. Бот должен работать на вашей машине или VPS (процесс с long polling).

## Что делает бот

1. `/start` — приветствие и оффер бесплатного 20-минутного видео по маркетингу.
2. Просит подписаться на канал и нажать «Подписался».
   - Кнопка-ссылка на канал (`CHANNEL_URL`).
   - Callback «Подписался» проверяет членство через `getChatMember`.
3. После подтверждения подписки отправляет `VIDEO_URL` и CTA написать «аудит» в `AUDIT_URL`.
4. Через `FOLLOWUP_DELAY_SECONDS` (по умолчанию 1200 = 20 мин) шлёт напоминание про бесплатный разбор.

Отложенные сообщения хранятся в SQLite (`data/followups.db` по умолчанию), поэтому после рестарта незавершённые follow-up’ы не теряются. Пока бот не запущен, сообщения не уходят — процесс должен быть жив (или перезапущен до/после due-time).

## Важно: бот — админ канала

Для проверки подписки бот должен быть **администратором** канала (`CHANNEL_USERNAME` / `CHANNEL_ID`). Иначе `getChatMember` не сработает.

## Локальный запуск

```bash
git clone https://github.com/Maksim-Tukmachev/voronka1-telegram-bot.git
cd voronka1-telegram-bot

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Отредактируйте .env: вставьте TELEGRAM_BOT_TOKEN из @BotFather
# Для быстрых тестов можно поставить FOLLOWUP_DELAY_SECONDS=60

python -m bot
```

Остановка: `Ctrl+C`.

## Переменные окружения

| Переменная | Описание |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен бота (обязательно) |
| `CHANNEL_USERNAME` | Канал с `@`, например `@samartsevvv` |
| `CHANNEL_ID` | Альтернатива username (числовой id) |
| `CHANNEL_URL` | Ссылка на кнопку «Подписаться» |
| `VIDEO_URL` | Ссылка на видео (сейчас stub) |
| `AUDIT_URL` | Ссылка на разбор / «аудит» |
| `FOLLOWUP_DELAY_SECONDS` | Задержка follow-up (сек), default `1200` |
| `FOLLOWUP_DB_PATH` | Путь к SQLite (опционально) |

Реальные токены **не коммитьте**. В репозитории только `.env.example`.

## Деплой на VPS (кратко)

1. Клонируйте репозиторий на сервер.
2. Создайте `.env` с боевым токеном.
3. Запускайте через `systemd`, `supervisord` или `tmux`/`screen`, чтобы процесс переживал disconnect SSH.
4. Добавьте бота админом в канал.

## Структура

```
bot/
  __main__.py   # entry: python -m bot
  config.py     # env / .env
  handlers.py   # /start + callback подписки
  followup.py   # SQLite + asyncio scheduler
  texts.py      # русские тексты
.env.example
requirements.txt
```
