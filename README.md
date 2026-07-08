# bot_4_spotify

Телеграм-бот для скачивания музыки со Spotify в формате mp3. Принимает ссылки
на одиночные треки (`open.spotify.com/track/...`) и отдаёт их юзеру как аудио.

## Как это работает

Spotify сам не отдаёт файлы. Бот добывает mp3 через **цепочку движков с
фоллбеком** (`bot/services/providers/`): пробует их по очереди, и если движок
падает сбоем (5xx / таймаут / 429 / ошибка CDN) — молча переходит к следующему.
Каждый движок мэтчит трек по метаданным и отдаёт прямую ссылку на mp3, бот её
скачивает и шлёт в Telegram.

Порядок цепочки:

1. `spotify-downloader9` — RapidAPI, основной
2. `spotify-downloader-mp33` — RapidAPI
3. `spotify-downloader23` — RapidAPI
4. `spotify-downloader-v2` — RapidAPI, 320kbps (метадату добирает через Spotify oEmbed)
5. `spotify-music-mp3-downloader-api` — RapidAPI, исходный движок
6. `spotdl` — self-hosted (качает с YouTube через yt-dlp), последний рубеж, когда легли все RapidAPI

Успешные треки кэшируются в БД по `file_id` — повторная отправка мгновенная.
Кэш проверяется **до** обращения к движкам, поэтому уже скачанный трек уедет
юзеру даже когда все движки недоступны.

Добавить/убрать движок или сменить порядок — правится в одном месте:
`_build_providers()` в `bot/services/spotify.py`.

## Стек

- **Python 3.12** + **aiogram 3** (асинхронный Telegram-бот)
- **PostgreSQL 16** + **SQLAlchemy 2** (asyncpg драйвер)
- **httpx** — HTTP-клиент к RapidAPI-движкам
- **spotdl** + **ffmpeg** + **yt-dlp** — self-hosted фоллбек-движок
- **Docker Compose** — бот + postgres + autoheal

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
   подписаться (free tier) на движки из цепочки (см. `.env.example`) и
   скопировать `X-RapidAPI-Key` — он один на все. Хватит и одного движка,
   остальные добавят надёжности.
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

- **RapidAPI квота:** у каждого движка свой бесплатный лимит (обычно 50–100
  запросов/мес). Цепочка размазывает нагрузку: когда один упрётся в лимит (429),
  бот перейдёт к следующему.
- **CDN/сервер 5xx:** отдельные движки иногда падают (как было `[server] 500`
  и `[cdn] 504`) — теперь это ловит фоллбек и переходит к следующему движку.
  Алерт админам приходит, только если легли **все** движки разом.
- **spotdl медленнее:** последний рубеж качает с YouTube и собирает mp3 через
  ffmpeg — это дольше (~10–30 сек) и грузит CPU, но срабатывает редко.
- **Лимит Telegram Bot API:** файлы > 50 МБ не отправляются. Обычный
  mp3-трек весит 3–10 МБ, так что это редко задевает.
