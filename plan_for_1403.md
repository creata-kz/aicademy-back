# План: Модульная архитектура aicademy-back

> Дата: 14.03.2026
> Проект: aicademy-back
> Цель: Реструктуризация в переносимые модули + дореализация архитектуры

---

## Контекст

Бэкенд AI Academy функционально готов (MVP), но код организован плоско (`app/models/`, `app/services/`, `app/api/v1/`). Нужно:
1. Реструктурировать в **переносимые модули** — чтобы Auth, Личный кабинет, Уведомления и т.д. можно было скопировать в новый проект и адаптировать с минимальными изменениями
2. Дореализовать функции из ARCHITECTURE_AICADEMY.md (logout, rate limiting, admin, leaderboard, аналитика, multi-channel уведомления и др.)
3. Закрыть технический долг (тесты, логирование, CI/CD, безопасность)

---

## Целевая структура

```
app/
├── core/                          # Переносимая инфраструктура
│   ├── config.py                  # Pydantic Settings (все env vars)
│   ├── database.py                # SQLAlchemy async engine + get_db
│   ├── redis.py                   # Redis pool + get_redis (опционально)
│   ├── security.py                # JWT encode/decode + bcrypt (generic)
│   ├── exceptions.py              # AppException, NotFound, Forbidden, Conflict, RateLimited
│   ├── logging.py                 # Structured JSON logging (stdlib)
│   └── middleware.py              # Request timing, access log, error handler, Sentry
│
├── modules/
│   ├── auth/                      # Переносимый
│   │   ├── models.py              # EmailVerificationCode
│   │   ├── schemas.py             # Все auth request/response
│   │   ├── service.py             # Регистрация, верификация, логин, refresh, logout
│   │   ├── routes.py              # 10 auth endpoints + bot auth
│   │   ├── deps.py                # get_current_user, require_role
│   │   ├── telegram.py            # HMAC-валидация, bot-сессии (Redis)
│   │   ├── email.py               # Отправка кодов через Resend
│   │   └── rate_limit.py          # Redis rate limiter
│   │
│   ├── users/                     # Переносимый
│   │   ├── models.py              # User (+ is_deleted, settings JSONB)
│   │   ├── schemas.py             # UserOut, UserUpdate, ChangePassword, DeleteAccount
│   │   ├── service.py             # Профиль, смена пароля, soft-delete, настройки
│   │   └── routes.py              # /users/me/*, /users/me/change-password, DELETE /users/me
│   │
│   ├── content/                   # Адаптируемый (иерархия меняется per-project)
│   │   ├── models.py              # Track, Week, Lesson, UserEnrollment
│   │   ├── schemas.py             # TrackData, LessonData, WeekData и т.д.
│   │   ├── service.py             # Запросы к контенту, enrollment
│   │   ├── routes.py              # GET /tracks/*, POST /tracks/{slug}/enroll
│   │   └── seed.py                # Загрузка JSON -> БД
│   │
│   ├── progress/                  # Адаптируемый
│   │   ├── models.py              # LessonProgress
│   │   ├── schemas.py             # LessonProgressOut, QuizSubmission, QuizResult
│   │   ├── service.py             # complete-video, submit-quiz, complete-assignment + hook-система
│   │   ├── streak.py              # update_streak (отдельно для переносимости)
│   │   └── routes.py              # POST complete-*, GET progress
│   │
│   ├── gamification/              # Переносимый
│   │   ├── models.py              # Badge, UserBadge
│   │   ├── schemas.py             # BadgeOut, LeaderboardEntry, UserRank
│   │   ├── service.py             # evaluate_badges, leaderboard queries
│   │   └── routes.py              # GET /leaderboard, GET /tracks/{slug}/leaderboard
│   │
│   ├── notifications/             # Переносимый
│   │   ├── models.py              # Notification (+ channel, type)
│   │   ├── schemas.py             # NotificationOut, NotificationPreferences
│   │   ├── service.py             # send_notification — диспатчит по каналам
│   │   ├── channels/
│   │   │   ├── inapp.py           # Запись в БД
│   │   │   ├── email.py           # Resend
│   │   │   └── telegram.py        # Bot API push
│   │   └── routes.py              # GET/PATCH/POST notifications
│   │
│   ├── onboarding/                # Переносимый (как "Психотипирование")
│   │   ├── models.py              # QuizPair, QuizResponse
│   │   ├── schemas.py             # QuizPairOut, OnboardingResult
│   │   ├── service.py             # Расчёт архетипа (конфигурируемые оси)
│   │   ├── routes.py              # GET quiz-pairs, POST responses, POST complete
│   │   └── seed.py                # Загрузка вопросов
│   │
│   ├── admin/                     # Переносимый (каркас)
│   │   ├── schemas.py             # UserListItem, ContentEdit, BroadcastRequest
│   │   ├── service.py             # CRUD пользователей, CMS, broadcast
│   │   └── routes.py              # /admin/* (require_role("admin"))
│   │
│   ├── analytics/                 # Переносимый
│   │   ├── schemas.py             # DAUMetric, RetentionData, ContentMetrics
│   │   ├── service.py             # SQL-запросы: DAU/WAU/MAU, retention, completion rates
│   │   └── routes.py              # /admin/analytics/*
│   │
│   └── health/                    # Переносимый
│       ├── service.py             # check_db, check_redis, check_external
│       └── routes.py              # GET /health (подробный)
│
├── main.py                        # Module registry + lifespan + middleware
└── __init__.py
```

---

## Принцип переносимости модулей

**Каждый модуль — папка со стандартным интерфейсом:**
```python
# modules/auth/__init__.py
from .routes import router
from .models import EmailVerificationCode
models = [EmailVerificationCode]
```

**main.py использует реестр:**
```python
ENABLED_MODULES = [
    "app.modules.auth",
    "app.modules.users",
    "app.modules.content",
    ...
]
```

**Чтобы перенести модуль в новый проект:** скопировать папку, добавить в ENABLED_MODULES, поправить 1-2 импорта (прежде всего путь к User-модели).

**Связь между модулями — через хуки, а не прямые импорты:**
```python
# progress/service.py — после действия вызывает зарегистрированные хуки
_on_progress_hooks: list[Callable] = []
def register_progress_hook(fn): _on_progress_hooks.append(fn)

# gamification/__init__.py — регистрирует свой хук при импорте
from app.modules.progress.service import register_progress_hook
register_progress_hook(evaluate_badges)
```
Если в новом проекте нет gamification — progress работает автономно.

**Правила зависимостей (DAG):**
- Все модули -> `app/core/` (config, database, security, redis, exceptions)
- `auth` -> `users` (нужна модель User)
- `progress` <-hook- `gamification` (опциональная связь)
- `admin`, `analytics` -> читают модели всех модулей (read-only)
- `notifications` <- вызывается другими модулями через `send_notification()`
- `content`, `onboarding`, `health` — полностью независимы

---

## Фазы реализации

### Фаза 0: Инфраструктура (core/) — Размер: M

> Фундамент, на котором стоят все модули

**Создать `app/core/`:**
- `config.py` — перенести из `app/config.py`, добавить: `REDIS_URL`, `SENTRY_DSN`, `S3_BUCKET`, `COOKIE_DOMAIN`, `LOG_LEVEL`, `ENVIRONMENT`
- `database.py` — перенести из `app/database.py` без изменений
- `security.py` — извлечь из `auth_service.py`: `hash_password`, `verify_password`, `create_access_token`, `decode_access_token`
- `redis.py` — Redis async pool + `get_redis()` dependency. Graceful fallback если REDIS_URL не задан
- `exceptions.py` — базовый `AppException(HTTPException)` + `NotFound`, `Forbidden`, `Conflict`, `RateLimited`
- `logging.py` — structured JSON logging через stdlib. Убить все `print()` в проекте
- `middleware.py` — request timing, access log, global exception handler, Sentry init

**Также:**
- `docker-compose.yml` (postgres + redis + app)
- Обновить `requirements.txt`: `redis[hiredis]`, `sentry-sdk[fastapi]`
- Обновить `.env.example`
- Создать shim-файлы (`app/config.py` -> `from app.core.config import settings`) для обратной совместимости

**Файлы-источники:**
- `app/config.py` -> `app/core/config.py`
- `app/database.py` -> `app/core/database.py`
- `app/services/auth_service.py` (4 generic функции) -> `app/core/security.py`

**Миграции:** нет
**Тесты:** `tests/conftest.py` с async fixtures (httpx AsyncClient + test DB)

---

### Фаза 1: Модуль Auth — Размер: L

> Первый полноценный модуль. Самый критичный для переносимости

**Перенести и доработать:**
- `app/services/auth_service.py` -> `modules/auth/service.py` (без 4 generic-функций — они в core/security.py)
- `app/services/email_service.py` -> `modules/auth/email.py` (**удалить debug print'ы!**)
- `app/services/telegram_bot.py` -> `modules/auth/telegram.py` (заменить in-memory dict -> Redis)
- `app/models/verification_code.py` -> `modules/auth/models.py`
- `app/schemas/auth.py` -> `modules/auth/schemas.py`
- `app/api/v1/auth.py` + `app/api/v1/bot.py` -> `modules/auth/routes.py`
- `app/api/deps.py` -> `modules/auth/deps.py`

**Новое:**
- `POST /auth/logout` — blacklist JWT в Redis
- `modules/auth/rate_limit.py` — Redis rate limiter (5 reg/час/IP, 3 кода/10мин/email, 10 login/15мин/IP)
- httpOnly cookie: auth endpoints ставят `Set-Cookie` + возвращают token в body (обратная совместимость с фронтом)
- Защита: убрать дефолтный JWT_SECRET в production, убрать утечку API key в print'ах

**Миграции:** нет (модели без изменений)

---

### Фаза 2: Модуль Users — Размер: M

> User-модель + профиль + настройки

**Перенести:**
- `app/models/user.py` -> `modules/users/models.py`
- `app/schemas/user.py` -> `modules/users/schemas.py`
- `app/api/v1/users.py` -> `modules/users/routes.py`

**Новое:**
- Поля в User: `is_deleted`, `deleted_at`, `settings` (JSONB)
- `PATCH /users/me/password` — смена пароля (текущий + новый)
- `DELETE /users/me` — soft-delete (is_deleted=true, deleted_at=now)
- `PATCH /users/me/settings` — notification preferences, etc.
- `POST /users/me/link-telegram`, `DELETE /users/me/unlink-telegram`
- `get_current_user` проверяет `is_deleted`

**Миграция 005:** добавить `is_deleted`, `deleted_at`, `settings` в `users`

---

### Фаза 3: Модуль Content — Размер: M

> Контент-иерархия (Track -> Week -> Lesson)

**Перенести:**
- `app/models/track.py`, `week.py`, `lesson.py`, `enrollment.py` -> `modules/content/models.py`
- `app/schemas/track.py`, `week.py`, `lesson.py` -> `modules/content/schemas.py`
- `app/api/v1/tracks.py` -> `modules/content/routes.py`
- `app/seed/seed_data.py` -> `modules/content/seed.py`

**Новое:**
- `modules/content/service.py` — выделить query-логику из routes в сервис

**Миграции:** нет

---

### Фаза 4: Модуль Progress — Размер: M

> Прогресс + стрики + hook-система

**Перенести:**
- `app/models/progress.py` (только LessonProgress) -> `modules/progress/models.py`
- `app/schemas/progress.py` -> `modules/progress/schemas.py`
- `app/services/progress_service.py` -> `modules/progress/service.py`
- `app/services/streak_service.py` -> `modules/progress/streak.py`
- `app/api/v1/lessons.py` + `app/api/v1/progress.py` -> `modules/progress/routes.py`

**Новое:**
- Hook-система: `register_progress_hook(fn)` — вызывается после каждого progress-действия
- Gamification регистрирует `evaluate_badges` как hook -> progress не зависит от gamification напрямую

**Миграции:** нет

---

### Фаза 5: Модуль Gamification — Размер: M

> Бейджи + лидерборд

**Перенести:**
- `app/models/badge.py` + `UserBadge` из `progress.py` -> `modules/gamification/models.py`
- `app/schemas/badge.py` -> `modules/gamification/schemas.py`
- `app/services/badge_service.py` -> `modules/gamification/service.py`

**Новое:**
- `GET /leaderboard` — глобальный (top по XP, SQL ROW_NUMBER)
- `GET /tracks/{slug}/leaderboard` — per-track
- `GET /users/me/rank` — ранг текущего пользователя
- Redis-кэш для top-100 (TTL 5 мин)
- Регистрация `evaluate_badges` как progress hook

**Миграции:** нет (опционально: materialized view для leaderboard)

---

### Фаза 6: Модуль Notifications — Размер: M

> 3 канала: in-app, email, Telegram

**Перенести:**
- `app/models/notification.py` -> `modules/notifications/models.py`
- `app/schemas/notification.py` -> `modules/notifications/schemas.py`
- `app/api/v1/notifications.py` -> `modules/notifications/routes.py`

**Новое:**
- Поля в Notification: `channel` (in_app/email/telegram), `notification_type`
- `modules/notifications/channels/` — три адаптера
- `send_notification(db, user_id, text, channels, type)` — единый интерфейс
- `GET /notifications/unread-count`
- Учёт user.settings (какие каналы включены)

**Миграция 006:** добавить `channel`, `notification_type` в `notifications`

---

### Фаза 7: Модуль Onboarding — Размер: S

> Профориентационный квиз (самый независимый модуль)

**Перенести:**
- `app/models/quiz_pair.py` -> `modules/onboarding/models.py`
- `app/schemas/onboarding.py` -> `modules/onboarding/schemas.py`
- `app/api/v1/onboarding.py` -> `modules/onboarding/routes.py` + `service.py`

**Новое:**
- Выделить `_calculate_archetype()` из routes в service
- Сделать оси конфигурируемыми (сейчас hardcoded narrative/visuals/system)
- `modules/onboarding/seed.py` — вынести seeding вопросов отдельно

**Миграции:** нет

---

### Фаза 8: Модуль Admin — Размер: L

> Админ-панель API

**Новое (нет текущего кода):**
- `GET /admin/users` — список с фильтрами (role, search, active/deleted), пагинация
- `GET /admin/users/{id}` — детали + прогресс + бейджи
- `PATCH /admin/users/{id}` — смена роли, бан/разбан
- `GET /admin/content/tracks` — CMS-список курсов
- `PUT /admin/content/tracks/{slug}/lessons/{lesson_slug}` — редактирование урока
- `POST /admin/notifications/broadcast` — массовая рассылка
- `GET /admin/dashboard` — сводная статистика
- Все endpoints: `require_role("admin")` или `require_role("moderator", "admin")`

**Миграции:** нет (работает с существующими моделями)

---

### Фаза 9: Модуль Analytics — Размер: M

> Метрики и дашборд

**Новое:**
- `GET /admin/analytics/engagement` — DAU/WAU/MAU
- `GET /admin/analytics/retention` — когортный retention
- `GET /admin/analytics/content` — completion rate по курсам/урокам
- SQL-запросы на PostgreSQL (COUNT DISTINCT, cohort analysis)
- Опционально: `activity_log` таблица для детального трекинга

**Миграция 007 (опционально):** создать `activity_log(user_id, action, metadata JSONB, created_at)`

---

### Фаза 10: Модуль Health — Размер: S

> Мониторинг инфраструктуры

**Новое:**
- `GET /health` -> `{"status": "ok"|"degraded", "checks": {"db": ..., "redis": ...}, "version": ...}`
- Sentry integration в `core/middleware.py`
- UptimeRobot polling -> алерт в Telegram при downtime

**Миграции:** нет

---

### Фаза 11: Cleanup + CI/CD + Тесты — Размер: L

> Финальная зачистка

1. **Удалить старые директории:** `app/models/`, `app/schemas/`, `app/services/`, `app/api/`, `app/seed/`
2. **Alembic env.py** — обновить чтобы собирал модели из всех модулей
3. **CI/CD (.github/workflows/):**
   - `ci.yml`: ruff lint -> mypy -> pytest (с Postgres service container)
   - `deploy.yml`: auto-deploy Railway on push to main
4. **Тесты (pytest-asyncio + httpx):**
   ```
   tests/
   ├── conftest.py
   ├── test_auth/
   ├── test_users/
   ├── test_content/
   ├── test_progress/
   ├── test_gamification/
   ├── test_notifications/
   ├── test_onboarding/
   ├── test_admin/
   └── test_health/
   ```
5. **requirements.txt:** добавить `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`

---

## Группировка по спринтам (недельные)

| Спринт | Фазы | Фокус |
|--------|-------|-------|
| 1 | 0 + 10 | Инфраструктура + Health (фундамент) |
| 2 | 1 + 2 | Auth + Users (безопасность, критический путь) |
| 3 | 3 + 7 | Content + Onboarding (независимые, простые) |
| 4 | 4 + 5 | Progress + Gamification (связаны hook-системой) |
| 5 | 6 | Notifications (multi-channel — нетривиально) |
| 6 | 8 + 9 | Admin + Analytics (схожие паттерны) |
| 7 | 11 | Cleanup, CI/CD, тесты |

---

## Что переносится откуда (маппинг файлов)

### В app/core/ (из текущего кода):
| Источник | Назначение | Что берём |
|----------|-----------|-----------|
| `app/config.py` | `core/config.py` | Весь файл + новые поля |
| `app/database.py` | `core/database.py` | Весь файл без изменений |
| `app/services/auth_service.py` | `core/security.py` | hash_password, verify_password, create_access_token, decode_access_token |

### В app/modules/ (из текущего кода):
| Источник | Модуль | Назначение |
|----------|--------|-----------|
| `app/services/auth_service.py` (остаток) | auth | `service.py` |
| `app/services/email_service.py` | auth | `email.py` |
| `app/services/telegram_bot.py` | auth | `telegram.py` |
| `app/models/verification_code.py` | auth | `models.py` |
| `app/schemas/auth.py` | auth | `schemas.py` |
| `app/api/v1/auth.py` + `bot.py` | auth | `routes.py` |
| `app/api/deps.py` | auth | `deps.py` |
| `app/models/user.py` | users | `models.py` |
| `app/schemas/user.py` | users | `schemas.py` |
| `app/api/v1/users.py` | users | `routes.py` |
| `app/models/track.py`, `week.py`, `lesson.py`, `enrollment.py` | content | `models.py` |
| `app/schemas/track.py`, `week.py`, `lesson.py` | content | `schemas.py` |
| `app/api/v1/tracks.py` | content | `routes.py` |
| `app/seed/seed_data.py` | content | `seed.py` |
| `app/models/progress.py` (LessonProgress) | progress | `models.py` |
| `app/schemas/progress.py` | progress | `schemas.py` |
| `app/services/progress_service.py` | progress | `service.py` |
| `app/services/streak_service.py` | progress | `streak.py` |
| `app/api/v1/lessons.py` + `progress.py` | progress | `routes.py` |
| `app/models/badge.py` + UserBadge | gamification | `models.py` |
| `app/schemas/badge.py` | gamification | `schemas.py` |
| `app/services/badge_service.py` | gamification | `service.py` |
| `app/models/notification.py` | notifications | `models.py` |
| `app/schemas/notification.py` | notifications | `schemas.py` |
| `app/api/v1/notifications.py` | notifications | `routes.py` |
| `app/models/quiz_pair.py` | onboarding | `models.py` |
| `app/schemas/onboarding.py` | onboarding | `schemas.py` |
| `app/api/v1/onboarding.py` | onboarding | `routes.py` + `service.py` |

---

## Критические исправления безопасности (в рамках фаз 0-1)

1. **JWT_SECRET** — убрать дефолт `"super-secret-jwt-key-change-in-production"`. Raise error при старте если не задан и ENVIRONMENT != "dev"
2. **Debug prints в email_service.py** — 7 штук, включая утечку префикса API-ключа. Заменить на structured logging
3. **In-memory auth sessions** (telegram_bot.py) — не переживают рестарт. Перенести в Redis
4. **Hardcoded localhost** в telegram_bot.py:16 и config.py — вынести в env vars

---

## Верификация

После каждой фазы:
1. `docker-compose up` — приложение стартует без ошибок
2. Все существующие endpoints отвечают корректно
3. Новые endpoints работают
4. `alembic upgrade head` проходит без ошибок
5. Фронтенд (aicademy-front) продолжает работать без изменений

После фазы 11:
- `ruff check .` — 0 ошибок
- `pytest` — все тесты зелёные
- CI pipeline проходит на GitHub Actions
