# bot_4_spotify

Телеграм-бот для скачивания музыки со Spotify в формате mp3. Принимает ссылки
на одиночные треки (`open.spotify.com/track/...`) и отдаёт их юзеру как аудио.

## Как это работает

Spotify сам не отдаёт файлы — трек качается через публичный
[Spotify Music MP3 Downloader API](https://rapidapi.com/) на RapidAPI
(под капотом провайдер мэтчит трек по метаданным и берёт аудио с другого
источника). Бот делает один HTTP-запрос → получает прямую ссылку на mp3 →
скачивает → отправляет в Telegram. Успешные треки кэшируются в БД по
`file_id`, поэтому повторная отправка той же ссылки — мгновенная.

## Стек

- **Python 3.12** + **aiogram 3** (асинхронный Telegram-бот)
- **PostgreSQL 16** + **SQLAlchemy 2** (asyncpg драйвер)
- **httpx** — HTTP-клиент к RapidAPI
- **Docker Compose** — бот + postgres + autoheal

Без ffmpeg, без Spotify-приложения, без yt-dlp.

## Что поддерживается

- [x] Одиночные треки (`/track/...`)
- [x] Мультиязычность: ru / uz / en
- [x] Админ-панель: статистика, обязательная подписка на каналы, рассылка
- [x] Rate limit: 5 запросов в минуту на юзера
- [x] Кэш отправленных треков (файлы не качаются повторно)
- [ ] Альбомы и плейлисты — пока нет (в следующей версии)
- [ ] Подкасты и эпизоды — не поддерживаются

## Запуск

### Что нужно заранее

1. **BOT_TOKEN** от [@BotFather](https://t.me/BotFather)
2. **RapidAPI Key** — зарегиться на [rapidapi.com](https://rapidapi.com),
   подписаться на **Spotify Music MP3 Downloader API** (тариф Basic / Free),
   скопировать `X-RapidAPI-Key`
3. **Telegram ID админа** — узнать у [@userinfobot](https://t.me/userinfobot)
4. Установленный Docker и Docker Compose

### Шаги

```bash
cp .env.example .env
# открыть .env и заполнить: BOT_TOKEN, BOT_USERNAME, RAPIDAPI_KEY,
# ADMIN_IDS, ADMIN_USERNAME, DB_PASSWORD
docker compose up -d --build
docker compose logs -f bot
```

В логах должно появиться `Бот @<username> запущен!` — значит всё ок.

## Переменные .env

Все переменные описаны в `.env.example`. Обязательные:

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | токен бота от BotFather |
| `BOT_USERNAME` | имя бота без `@` |
| `RAPIDAPI_KEY` | ключ из RapidAPI dashboard |
| `DB_PASSWORD` | пароль Postgres (можно любой) |
| `ADMIN_IDS` | telegram-id админов через запятую |
| `ADMIN_USERNAME` | username главного админа без `@` |

## Использование

В Telegram:

- `/start` — главное меню
- Отправь ссылку `https://open.spotify.com/track/<id>` — бот пришлёт mp3
- `/profile` — твоя статистика
- `/language` — сменить язык (ru / uz / en)
- `/admin` — админ-панель (только для `ADMIN_IDS`)

## Структура проекта

```
bot_4_spotify/
├── bot/
│   ├── main.py              # точка входа, регистрация роутеров
│   ├── config.py            # настройки из .env (pydantic-settings)
│   ├── emojis.py            # премиум-эмодзи
│   ├── i18n.py              # словарь переводов ru/uz/en
│   ├── database/            # models + crud + engine
│   ├── handlers/            # start, admin, download
│   ├── middlewares/         # rate_limit, subscription
│   ├── services/
│   │   └── spotify.py       # httpx-клиент к RapidAPI
│   ├── keyboards/           # inline-клавиатуры
│   └── utils/               # helpers, commands
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Админ-панель

`/admin` открывает меню с разделами:

- **Статистика** — всего юзеров, за сегодня, скачанных треков, каналов
- **Каналы подписки** — добавить/удалить обязательные каналы (после добавления
  любой юзер должен быть подписан на все, иначе бот блокирует ссылки)
- **Рассылка** — массовая отправка сообщения (текст/фото/видео) всем юзерам

## Известные ограничения

- **RapidAPI квота:** бесплатный тариф обычно 50–100 запросов в месяц. Для
  ~100 req/week возможно понадобится Basic тариф (~$5/мес).
- **CDN 5xx:** ~1–5% запросов могут падать с ошибкой CDN провайдера —
  решается повтором того же запроса.
- **Лимит Telegram Bot API:** файлы > 50 МБ не отправляются. Обычный
  mp3-трек весит 3–10 МБ, так что это редко задевает.
