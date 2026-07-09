"""Мультиязычность — русский, узбекский, английский.
Использование: from bot.i18n import t
  t("start.welcome", lang="en", name="John")
"""

from bot.emojis import E

TRANSLATIONS = {
    # ═══════════════════════ START ═══════════════════════
    "start.welcome": {
        "ru": (
            f"{E['bot']} <b>Привет, {{name}}!</b>\n\n"
            f"{E['audio']} Я помогу тебе скачать музыку с Spotify "
            f"в формате mp3 @ 320 kbps — с обложкой, тегами и исполнителем.\n\n"
            f"{E['pin']} <b>Как пользоваться:</b>\n"
            "Просто отправь мне ссылку на трек, альбом или плейлист:\n"
            f"{E['link']} <code>https://open.spotify.com/track/...</code>\n\n"
            "Выбери действие ниже:"
        ),
        "uz": (
            f"{E['bot']} <b>Salom, {{name}}!</b>\n\n"
            f"{E['audio']} Spotify'dan musiqa yuklab olishda yordam beraman — "
            f"mp3 @ 320 kbps, muqova va teglar bilan.\n\n"
            f"{E['pin']} <b>Qanday foydalanish:</b>\n"
            "Menga trek, albom yoki pleylist havolasini yuboring:\n"
            f"{E['link']} <code>https://open.spotify.com/track/...</code>\n\n"
            "Quyidagi tugmalardan birini tanlang:"
        ),
        "en": (
            f"{E['bot']} <b>Hi, {{name}}!</b>\n\n"
            f"{E['audio']} I'll help you download music from Spotify "
            f"as mp3 @ 320 kbps — with cover art, tags and artist info.\n\n"
            f"{E['pin']} <b>How to use:</b>\n"
            "Just send me a link to a track, album or playlist:\n"
            f"{E['link']} <code>https://open.spotify.com/track/...</code>\n\n"
            "Choose an action below:"
        ),
    },

    # ═══════════════════════ BUTTONS ═══════════════════════
    "btn.download": {
        "ru": "Скачать музыку",
        "uz": "Musiqa yuklab olish",
        "en": "Download music",
    },
    "btn.profile": {
        "ru": "Мой профиль",
        "uz": "Mening profilim",
        "en": "My profile",
    },
    "btn.help": {
        "ru": "Помощь",
        "uz": "Yordam",
        "en": "Help",
    },
    "btn.back": {
        "ru": "Назад",
        "uz": "Orqaga",
        "en": "Back",
    },
    "btn.cancel": {
        "ru": "Отмена",
        "uz": "Bekor qilish",
        "en": "Cancel",
    },
    "btn.language": {
        "ru": "Сменить язык",
        "uz": "Tilni o'zgartirish",
        "en": "Change language",
    },
    "btn.confirm_download": {
        "ru": "Скачать",
        "uz": "Yuklab olish",
        "en": "Download",
    },
    "btn.check_sub": {
        "ru": "Проверить подписку",
        "uz": "Obunani tekshirish",
        "en": "Check subscription",
    },
    "btn.admin_panel": {
        "ru": "Админ-панель",
        "uz": "Admin panel",
        "en": "Admin panel",
    },
    "btn.admin_stats": {
        "ru": "Статистика",
        "uz": "Statistika",
        "en": "Statistics",
    },
    "btn.admin_channels": {
        "ru": "Каналы подписки",
        "uz": "Obuna kanallari",
        "en": "Subscription channels",
    },
    "btn.admin_broadcast": {
        "ru": "Рассылка",
        "uz": "Xabar yuborish",
        "en": "Broadcast",
    },
    "btn.admin_home": {
        "ru": "В главное меню",
        "uz": "Asosiy menyuga",
        "en": "Main menu",
    },
    "btn.admin_add": {
        "ru": "Добавить канал",
        "uz": "Kanal qo'shish",
        "en": "Add channel",
    },
    "btn.admin_back": {
        "ru": "Назад в админку",
        "uz": "Admin panelga qaytish",
        "en": "Back to admin",
    },
    "btn.admin_cancel": {
        "ru": "Отмена",
        "uz": "Bekor qilish",
        "en": "Cancel",
    },

    # ═══════════════════════ DOWNLOAD FLOW ═══════════════════════
    "download.prompt": {
        "ru": (
            f"{E['audio']} <b>Скачивание с Spotify</b>\n\n"
            "Отправь мне ссылку на:\n"
            "• Трек\n"
            "• Альбом\n"
            "• Плейлист\n\n"
            f"{E['link']} Пример: <code>https://open.spotify.com/track/...</code>"
        ),
        "uz": (
            f"{E['audio']} <b>Spotify'dan yuklab olish</b>\n\n"
            "Menga havola yuboring:\n"
            "• Trek\n"
            "• Albom\n"
            "• Pleylist\n\n"
            f"{E['link']} Misol: <code>https://open.spotify.com/track/...</code>"
        ),
        "en": (
            f"{E['audio']} <b>Download from Spotify</b>\n\n"
            "Send me a link to:\n"
            "• Track\n"
            "• Album\n"
            "• Playlist\n\n"
            f"{E['link']} Example: <code>https://open.spotify.com/track/...</code>"
        ),
    },
    "download.fetching_info": {
        "ru": f"{E['refresh']} Получаю информацию…",
        "uz": f"{E['refresh']} Ma'lumot olinmoqda…",
        "en": f"{E['refresh']} Fetching info…",
    },
    "download.not_spotify": {
        "ru": (
            f"{E['warning']} Это не похоже на ссылку Spotify.\n\n"
            "Отправь мне ссылку вида "
            "<code>https://open.spotify.com/track/...</code>"
        ),
        "uz": (
            f"{E['warning']} Bu Spotify havolasiga o'xshamaydi.\n\n"
            "<code>https://open.spotify.com/track/...</code> "
            "ko'rinishidagi havola yuboring"
        ),
        "en": (
            f"{E['warning']} This doesn't look like a Spotify link.\n\n"
            "Send a link like "
            "<code>https://open.spotify.com/track/...</code>"
        ),
    },
    "download.not_supported": {
        "ru": (
            f"{E['ban']} Подкасты и эпизоды пока не поддерживаются.\n\n"
            "Поддерживаются только треки, альбомы и плейлисты."
        ),
        "uz": (
            f"{E['ban']} Podkast va epizodlar hozircha qo'llab-quvvatlanmaydi.\n\n"
            "Faqat treklar, albomlar va pleylistlar qo'llab-quvvatlanadi."
        ),
        "en": (
            f"{E['ban']} Podcasts and episodes are not supported yet.\n\n"
            "Only tracks, albums and playlists are supported."
        ),
    },
    "download.track_info": {
        "ru": (
            f"{E['audio']} <b>{{title}}</b>\n"
            f"{E['profile']} {{artist}}\n"
            f"{E['folder']} {{album}}\n"
            f"{E['clock']} {{duration}}\n\n"
            f"{E['download']} Начинаю скачивание…"
        ),
        "uz": (
            f"{E['audio']} <b>{{title}}</b>\n"
            f"{E['profile']} {{artist}}\n"
            f"{E['folder']} {{album}}\n"
            f"{E['clock']} {{duration}}\n\n"
            f"{E['download']} Yuklab olish boshlanmoqda…"
        ),
        "en": (
            f"{E['audio']} <b>{{title}}</b>\n"
            f"{E['profile']} {{artist}}\n"
            f"{E['folder']} {{album}}\n"
            f"{E['clock']} {{duration}}\n\n"
            f"{E['download']} Starting download…"
        ),
    },
    "download.only_tracks_supported": {
        "ru": (
            f"{E['info']} Пока поддерживаются только <b>одиночные треки</b>.\n\n"
            "Альбомы и плейлисты — в следующей версии. "
            "Отправь ссылку вида <code>https://open.spotify.com/track/...</code>"
        ),
        "uz": (
            f"{E['info']} Hozircha faqat <b>bitta trek</b> qo'llab-quvvatlanadi.\n\n"
            "Albom va pleylistlar — keyingi versiyada. "
            "<code>https://open.spotify.com/track/...</code> ko'rinishidagi havola yuboring"
        ),
        "en": (
            f"{E['info']} Only <b>single tracks</b> are supported for now.\n\n"
            "Albums and playlists will come in the next version. "
            "Send a link like <code>https://open.spotify.com/track/...</code>"
        ),
    },
    "download.downloading_track": {
        "ru": f"{E['refresh']} Скачиваю трек…",
        "uz": f"{E['refresh']} Trek yuklab olinmoqda…",
        "en": f"{E['refresh']} Downloading track…",
    },
    "download.uploading": {
        "ru": f"{E['plane']} Отправляю в Telegram…",
        "uz": f"{E['plane']} Telegramga yuborilmoqda…",
        "en": f"{E['plane']} Uploading to Telegram…",
    },
    "download.track_sent": {
        "ru": f"{E['check']} Готово!",
        "uz": f"{E['check']} Tayyor!",
        "en": f"{E['check']} Done!",
    },
    # ═══════════════════════ PROFILE ═══════════════════════
    "profile.title": {
        "ru": (
            f"{E['profile']} <b>Мой профиль</b>\n\n"
            f"{E['bot']} Имя: {{full_name}}\n"
            f"{E['pin']} ID: <code>{{user_id}}</code>\n"
            f"{E['chart']} Скачано треков: {{downloads}}"
        ),
        "uz": (
            f"{E['profile']} <b>Mening profilim</b>\n\n"
            f"{E['bot']} Ism: {{full_name}}\n"
            f"{E['pin']} ID: <code>{{user_id}}</code>\n"
            f"{E['chart']} Yuklangan treklar: {{downloads}}"
        ),
        "en": (
            f"{E['profile']} <b>My profile</b>\n\n"
            f"{E['bot']} Name: {{full_name}}\n"
            f"{E['pin']} ID: <code>{{user_id}}</code>\n"
            f"{E['chart']} Tracks downloaded: {{downloads}}"
        ),
    },

    # ═══════════════════════ HELP ═══════════════════════
    "help.text": {
        "ru": (
            f"{E['info']} <b>Помощь</b>\n\n"
            f"{E['audio']} Этот бот качает музыку с Spotify в формате "
            "mp3 @ 320 kbps с обложкой и тегами.\n\n"
            f"{E['pin']} <b>Что можно отправить:</b>\n"
            "• Ссылку на трек\n"
            "• Ссылку на альбом\n"
            "• Ссылку на плейлист\n\n"
            f"{E['lightning']} <b>Как это работает:</b>\n"
            "Бот находит совпадение на YouTube Music и проставляет теги "
            "из Spotify.\n\n"
            f"{E['warning']} Подкасты и эпизоды не поддерживаются.\n\n"
            f"{E['profile']} По всем вопросам: @{{admin}}"
        ),
        "uz": (
            f"{E['info']} <b>Yordam</b>\n\n"
            f"{E['audio']} Bu bot Spotify'dan musiqani mp3 @ 320 kbps "
            "formatida muqova va teglar bilan yuklab oladi.\n\n"
            f"{E['pin']} <b>Nimalarni yuborish mumkin:</b>\n"
            "• Trek havolasi\n"
            "• Albom havolasi\n"
            "• Pleylist havolasi\n\n"
            f"{E['lightning']} <b>Qanday ishlaydi:</b>\n"
            "Bot YouTube Music'dan mos treklarni topib, Spotify teglarini "
            "o'rnatadi.\n\n"
            f"{E['warning']} Podkast va epizodlar qo'llab-quvvatlanmaydi.\n\n"
            f"{E['profile']} Savollar uchun: @{{admin}}"
        ),
        "en": (
            f"{E['info']} <b>Help</b>\n\n"
            f"{E['audio']} This bot downloads Spotify music as mp3 @ 320 kbps "
            "with cover art and tags.\n\n"
            f"{E['pin']} <b>What you can send:</b>\n"
            "• Track link\n"
            "• Album link\n"
            "• Playlist link\n\n"
            f"{E['lightning']} <b>How it works:</b>\n"
            "The bot finds a match on YouTube Music and applies Spotify "
            "tags to it.\n\n"
            f"{E['warning']} Podcasts and episodes are not supported.\n\n"
            f"{E['profile']} For questions: @{{admin}}"
        ),
    },

    # ═══════════════════════ SUBSCRIPTION ═══════════════════════
    "sub.welcome": {
        "ru": (
            f"{E['lock']} <b>Требуется подписка</b>\n\n"
            "Чтобы пользоваться ботом, подпишись на каналы ниже и нажми "
            f"{E['check']} «Проверить подписку»."
        ),
        "uz": (
            f"{E['lock']} <b>Obuna kerak</b>\n\n"
            "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling va "
            f"{E['check']} «Obunani tekshirish» tugmasini bosing."
        ),
        "en": (
            f"{E['lock']} <b>Subscription required</b>\n\n"
            "To use the bot, subscribe to the channels below and tap "
            f"{E['check']} «Check subscription»."
        ),
    },
    "sub.not_subscribed": {
        "ru": f"{E['warning']} Ты ещё не подписан на все каналы.",
        "uz": f"{E['warning']} Siz hali barcha kanallarga obuna bo'lmagansiz.",
        "en": f"{E['warning']} You're not subscribed to all channels yet.",
    },
    "sub.success": {
        "ru": f"{E['check']} Отлично! Подписка подтверждена.",
        "uz": f"{E['check']} Ajoyib! Obuna tasdiqlandi.",
        "en": f"{E['check']} Great! Subscription confirmed.",
    },

    # ═══════════════════════ LANGUAGE ═══════════════════════
    "lang.choose": {
        "ru": f"{E['gear']} Выбери язык:",
        "uz": f"{E['gear']} Tilni tanlang:",
        "en": f"{E['gear']} Choose a language:",
    },
    "lang.changed": {
        "ru": f"{E['check']} Язык изменён на русский",
        "uz": f"{E['check']} Til o'zbekchaga o'zgartirildi",
        "en": f"{E['check']} Language changed to English",
    },

    # ═══════════════════════ ERRORS ═══════════════════════
    "error.rate_limit": {
        "ru": (
            f"{E['clock']} Слишком много запросов.\n"
            "Подожди {seconds} секунд."
        ),
        "uz": (
            f"{E['clock']} Juda ko'p so'rov.\n"
            "{seconds} soniya kuting."
        ),
        "en": (
            f"{E['clock']} Too many requests.\n"
            "Please wait {seconds} seconds."
        ),
    },
    "error.generic": {
        "ru": f"{E['cross']} Ошибка: {{msg}}",
        "uz": f"{E['cross']} Xato: {{msg}}",
        "en": f"{E['cross']} Error: {{msg}}",
    },
    "error.track_failed": {
        "ru": f"{E['cross']} Не удалось скачать этот трек.",
        "uz": f"{E['cross']} Bu trekni yuklab bo'lmadi.",
        "en": f"{E['cross']} Failed to download this track.",
    },
    "error.spotify_api_down": {
        "ru": (
            f"{E['warning']} Spotify сейчас недоступен. "
            "Попробуй через пару минут."
        ),
        "uz": (
            f"{E['warning']} Spotify hozir javob bermayapti. "
            "Bir necha daqiqadan keyin urinib ko'ring."
        ),
        "en": (
            f"{E['warning']} Spotify is unavailable right now. "
            "Try again in a couple of minutes."
        ),
    },
    "error.track_unavailable": {
        "ru": (
            f"{E['cross']} Не удалось найти этот трек ни в одном источнике. "
            "Скорее всего, его нет в доступных каталогах — попробуй другой трек."
        ),
        "uz": (
            f"{E['cross']} Bu trek hech qaysi manbadan topilmadi. "
            "Ehtimol, u mavjud kataloglarda yo'q — boshqa trekni sinab ko'ring."
        ),
        "en": (
            f"{E['cross']} Couldn't find this track in any source. "
            "It's likely not in the available catalogs — try another track."
        ),
    },

    # ═══════════════════════ ADMIN ═══════════════════════
    "admin.title": {
        "ru": f"{E['lock']} <b>Админ-панель</b>",
        "uz": f"{E['lock']} <b>Admin panel</b>",
        "en": f"{E['lock']} <b>Admin panel</b>",
    },
    "admin.no_access": {
        "ru": f"{E['lock']} Нет доступа",
        "uz": f"{E['lock']} Ruxsat yo'q",
        "en": f"{E['lock']} No access",
    },
    "admin.stats": {
        "ru": (
            f"{E['chart']} <b>Статистика</b>\n\n"
            f"{E['users']} Всего юзеров: {{total_users}}\n"
            f"{E['plus']} За сегодня: {{today_users}}\n"
            f"{E['download']} Всего скачиваний: {{total_downloads}}\n"
            f"{E['megaphone']} Каналов подписки: {{total_channels}}"
        ),
        "uz": (
            f"{E['chart']} <b>Statistika</b>\n\n"
            f"{E['users']} Jami foydalanuvchilar: {{total_users}}\n"
            f"{E['plus']} Bugun: {{today_users}}\n"
            f"{E['download']} Jami yuklamalar: {{total_downloads}}\n"
            f"{E['megaphone']} Obuna kanallari: {{total_channels}}"
        ),
        "en": (
            f"{E['chart']} <b>Statistics</b>\n\n"
            f"{E['users']} Total users: {{total_users}}\n"
            f"{E['plus']} Today: {{today_users}}\n"
            f"{E['download']} Total downloads: {{total_downloads}}\n"
            f"{E['megaphone']} Subscription channels: {{total_channels}}"
        ),
    },
    "admin.channels_title": {
        "ru": f"{E['megaphone']} <b>Каналы для обязательной подписки</b>",
        "uz": f"{E['megaphone']} <b>Majburiy obuna kanallari</b>",
        "en": f"{E['megaphone']} <b>Required subscription channels</b>",
    },
    "admin.channels_empty": {
        "ru": "Пока ни одного канала не добавлено.",
        "uz": "Hozircha kanallar qo'shilmagan.",
        "en": "No channels added yet.",
    },
    "admin.add_channel_prompt": {
        "ru": (
            f"{E['plus']} Отправь ID канала (например <code>-1001234567890</code>).\n"
            f"{E['info']} Бот должен быть добавлен админом в этот канал."
        ),
        "uz": (
            f"{E['plus']} Kanal ID raqamini yuboring (masalan <code>-1001234567890</code>).\n"
            f"{E['info']} Bot kanalga admin sifatida qo'shilgan bo'lishi kerak."
        ),
        "en": (
            f"{E['plus']} Send the channel ID (e.g. <code>-1001234567890</code>).\n"
            f"{E['info']} The bot must be an admin in that channel."
        ),
    },
    "admin.add_channel_title": {
        "ru": f"{E['edit']} Введи название канала:",
        "uz": f"{E['edit']} Kanal nomini kiriting:",
        "en": f"{E['edit']} Enter the channel title:",
    },
    "admin.add_channel_link": {
        "ru": (
            f"{E['link']} Отправь ссылку-приглашение "
            "(например <code>https://t.me/channel</code> или <code>@channel</code>):"
        ),
        "uz": (
            f"{E['link']} Havolani yuboring "
            "(masalan <code>https://t.me/channel</code> yoki <code>@channel</code>):"
        ),
        "en": (
            f"{E['link']} Send the invite link "
            "(e.g. <code>https://t.me/channel</code> or <code>@channel</code>):"
        ),
    },
    "admin.add_channel_success": {
        "ru": f"{E['check']} Канал <b>{{title}}</b> добавлен.",
        "uz": f"{E['check']} Kanal <b>{{title}}</b> qo'shildi.",
        "en": f"{E['check']} Channel <b>{{title}}</b> added.",
    },
    "admin.add_channel_error": {
        "ru": f"{E['cross']} Ошибка: {{msg}}",
        "uz": f"{E['cross']} Xato: {{msg}}",
        "en": f"{E['cross']} Error: {{msg}}",
    },
    "admin.channel_removed": {
        "ru": f"{E['trash']} Канал удалён.",
        "uz": f"{E['trash']} Kanal o'chirildi.",
        "en": f"{E['trash']} Channel removed.",
    },
    "admin.broadcast_prompt": {
        "ru": (
            f"{E['plane']} Отправь сообщение для рассылки "
            "(текст, фото или видео):"
        ),
        "uz": (
            f"{E['plane']} Tarqatish uchun xabar yuboring "
            "(matn, rasm yoki video):"
        ),
        "en": (
            f"{E['plane']} Send the broadcast message "
            "(text, photo or video):"
        ),
    },
    "admin.broadcast_confirm": {
        "ru": f"{E['warning']} Разослать всем {{total}} юзерам?",
        "uz": f"{E['warning']} Barcha {{total}} foydalanuvchiga yuborilsinmi?",
        "en": f"{E['warning']} Send to all {{total}} users?",
    },
    "admin.broadcast_started": {
        "ru": f"{E['plane']} Рассылка запущена…",
        "uz": f"{E['plane']} Tarqatish boshlandi…",
        "en": f"{E['plane']} Broadcast started…",
    },
    "admin.broadcast_done": {
        "ru": (
            f"{E['check']} <b>Рассылка завершена</b>\n\n"
            f"Доставлено: {{success}}\n"
            f"Ошибок: {{failed}}"
        ),
        "uz": (
            f"{E['check']} <b>Tarqatish tugadi</b>\n\n"
            f"Yuborildi: {{success}}\n"
            f"Xatoliklar: {{failed}}"
        ),
        "en": (
            f"{E['check']} <b>Broadcast finished</b>\n\n"
            f"Delivered: {{success}}\n"
            f"Failed: {{failed}}"
        ),
    },
    "admin.id_not_number": {
        "ru": f"{E['cross']} ID должен быть числом. Попробуй ещё раз.",
        "uz": f"{E['cross']} ID raqam bo'lishi kerak. Qaytadan urinib ko'ring.",
        "en": f"{E['cross']} ID must be a number. Try again.",
    },
    "admin.link_invalid": {
        "ru": f"{E['cross']} Невалидная ссылка. Попробуй ещё раз.",
        "uz": f"{E['cross']} Noto'g'ri havola. Qaytadan urinib ko'ring.",
        "en": f"{E['cross']} Invalid link. Try again.",
    },
    "admin.confirm_delete": {
        "ru": f"{E['warning']} Удалить канал <code>{{channel_id}}</code>?",
        "uz": f"{E['warning']} <code>{{channel_id}}</code> kanalini o'chirasizmi?",
        "en": f"{E['warning']} Delete channel <code>{{channel_id}}</code>?",
    },
    "admin.broadcast_preview": {
        "ru": f"{E['eye']} Так будет выглядеть сообщение. Отправить?",
        "uz": f"{E['eye']} Xabar shunday ko'rinadi. Yuborilsinmi?",
        "en": f"{E['eye']} This is how the message will look. Send?",
    },
    "btn.admin_confirm_del": {
        "ru": "Да, удалить",
        "uz": "Ha, o'chirish",
        "en": "Yes, delete",
    },
    "btn.admin_cancel_del": {
        "ru": "Отмена",
        "uz": "Bekor qilish",
        "en": "Cancel",
    },
    "btn.admin_broadcast_confirm": {
        "ru": "Отправить",
        "uz": "Yuborish",
        "en": "Send",
    },
    "admin.cancelled": {
        "ru": f"{E['cross']} Отменено.",
        "uz": f"{E['cross']} Bekor qilindi.",
        "en": f"{E['cross']} Cancelled.",
    },
    "admin.alert_source_failed": {
        "ru": (
            f"{E['warning']} <b>Проблема с источником</b>\n\n"
            f"Источник: <code>{{source}}</code>\n"
            f"Ошибка: <code>{{msg}}</code>"
        ),
        "uz": (
            f"{E['warning']} <b>Manbada muammo</b>\n\n"
            f"Manba: <code>{{source}}</code>\n"
            f"Xato: <code>{{msg}}</code>"
        ),
        "en": (
            f"{E['warning']} <b>Source failure</b>\n\n"
            f"Source: <code>{{source}}</code>\n"
            f"Error: <code>{{msg}}</code>"
        ),
    },

    # ═══════════════════════ COMMANDS MENU ═══════════════════════
    "cmd.start": {
        "ru": "Запустить бота",
        "uz": "Botni ishga tushirish",
        "en": "Start the bot",
    },
    "cmd.menu": {
        "ru": "Главное меню",
        "uz": "Asosiy menyu",
        "en": "Main menu",
    },
    "cmd.profile": {
        "ru": "Мой профиль",
        "uz": "Mening profilim",
        "en": "My profile",
    },
    "cmd.help": {
        "ru": "Помощь",
        "uz": "Yordam",
        "en": "Help",
    },
    "cmd.language": {
        "ru": "Сменить язык",
        "uz": "Tilni o'zgartirish",
        "en": "Change language",
    },
}


def t(key: str, lang: str = "ru", **kwargs) -> str:
    """Получить перевод по ключу и языку."""
    translations = TRANSLATIONS.get(key, {})
    text = translations.get(lang, translations.get("en", f"[{key}]"))
    if kwargs:
        text = text.format(**kwargs)
    return text


def detect_language(language_code: str | None) -> str:
    """Определяет язык по Telegram: ru → русский, uz → узбекский, остальное → английский."""
    if not language_code:
        return "en"
    if language_code.startswith("ru"):
        return "ru"
    if language_code.startswith("uz"):
        return "uz"
    return "en"
