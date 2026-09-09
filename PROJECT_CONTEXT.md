# Green Vita Bot — Project Context

## 1. Project
Project name: Green Vita Bot
Repository: ~/green-vita-bot

This file is the central project context for continuing work across project chats.
Before making changes:
- Read this file.
- Preserve working features.
- Create a backup before each new feature/fase.
- Do not overwrite or remove existing functionality unless explicitly required.
- Stop on meaningful build/runtime errors before continuing.

---

## 2. Current Architecture

Main services:
- admin: FastAPI admin/PWA
- bot: Telegram bot
- bale: Bale bot adapter with custom HTTP Bot API client
- db: PostgreSQL 16
- redis: Redis 7

Docker Compose is used for service management.

---

## 3. Current Stable Status

All main services are currently running.

Expected healthy state:
- admin: Up / healthy
- bot: Up
- bale: Up
- db: Up / healthy
- redis: Up / healthy

Bale worker currently uses long polling.

Bale bot connection has been verified successfully.

---

## 4. Bale Bot

Files:
- src/bale/client.py
- src/bale/handlers.py
- src/bale/main.py
- src/bale/state.py
- src/bale/__init__.py

### Bale client
Custom HTTP client using:
- https://tapi.bale.ai/bot<TOKEN>

Important:
- send_message() supports optional reply_markup.
- Do NOT introduce python-bale-bot classes/dependencies unless explicitly required and verified.
- The working contact keyboard uses raw Bot API JSON.

### Bale state
Redis-backed state machine:
- state key: bale:state:<bale_id>
- data key: bale:state:<bale_id>:data
- TTL: 30 minutes

---

## 5. Bale Features Confirmed Working

### Main menu
Inline keyboard navigation works.

### Diagnosis
Flow:
- user selects diagnosis
- receives photo prompt
- photo is downloaded through Bale API
- existing AI diagnosis flow is used
- result is stored
- result contains expert visit option

### Plant identification
Flow:
- user selects identification
- receives photo prompt
- photo is downloaded through Bale API
- existing AI identification flow is used
- result contains expert visit option

### Plants
CRUD flow exists and has been tested:
- add
- view
- delete

### Expert visit
Three entry points:
1. Main menu → expert visit
2. Diagnosis result → expert visit
3. Identification result → expert visit

All three use the common expert visit flow.

Expert visit flow:
1. collect first/last name
2. collect phone
3. two supported phone methods:
   - direct Bale Contact button
   - manual phone entry
4. validate phone
5. update user contact
6. create/update visit record
7. notify admin/PWA
8. generate visit code
9. show success message
10. remove Reply Keyboard
11. keep inline Home button

### Contact button
Working API payload:

{
  "reply_markup": {
    "keyboard": [
      [
        {
          "text": "📱 ارسال شماره تلفن",
          "request_contact": true
        }
      ]
    ],
    "resize_keyboard": true,
    "one_time_keyboard": true
  }
}

Important:
- Contact arrives in message.contact.
- Phone number is read from message.contact.phone_number.
- Manual phone entry must remain supported.

### Keyboard removal
Verified working payload:

{
  "reply_markup": {
    "remove_keyboard": true,
    "inline_keyboard": [
      [
        {
          "text": "🏠 منوی اصلی",
          "callback_data": "home"
        }
      ]
    ]
  }
}

This was directly tested against Bale API and returned HTTP 200.

---

## 6. Bale Callback Routing

Current callback routes include:
- home
- plants
- plant_add
- plant_view:<id>
- plant_delete:<id>
- plant_delete_confirm:<id>
- diagnose
- identify
- visit
- diagnosis_visit:<id>
- identification_visit:<id>
- about
- help

Diagnosis and identification expert-visit callbacks are routed into the common expert visit state flow.

---

## 7. Expert Visit Backend

Main function:
- _finish_bale_expert_visit()

Supported source values:
- direct
- diagnosis
- identification

Existing visit logic:
- direct source creates a Diagnosis record with:
  disease_name = "درخواست ویزیت متخصص"
  ai_provider = "manual"
  expert_visit_requested = true
- diagnosis source marks diagnosis.expert_visit_requested = true
- identification source marks identification.expert_visit_requested = true
- admin badge is updated
- PWA push notification is sent
- visit code is returned to user

Do not duplicate this logic in new handlers.

---

## 8. Logging

Temporary UPDATE DEBUG logging was removed from src/bale/main.py.

A broken logger.info call was removed after it caused:
TypeError: not all arguments converted during string formatting

Current expected Bale log startup:
- Bale bot connected
- Starting Bale long polling

No Traceback / Logging error should remain.

---

## 9. Important Backups

Recent stable backups include:
- post-bale-stable-20260909-004733.tar.gz
- pre-bale-phone-keyboard-final-20260909-004416.tar.gz
- pre-bale-contact-handler-20260909-003749.tar.gz
- pre-bale-phone-replymarkup-20260909-003359.tar.gz
- pre-bale-contact-rebuild-20260909-002036.tar.gz

Backup directory:
- /root/green-vita-backups

Before any new feature/fase, create a new timestamped backup.

---

## 10. Current Known Repo State

There are existing uncommitted changes across the project, including:
- docker-compose.yml
- requirements.txt
- admin routers/templates/static assets
- bot diagnosis handler
- core config
- database models/repositories
- Bale source files
- Alembic migrations
- PWA/admin assets

Do NOT assume the working tree should be clean.

Do NOT reset or discard unrelated changes.

---

## 11. Known Security Issue

The Bale bot token has previously appeared in terminal/log output.

Action required:
- rotate/revoke the exposed Bale bot token
- put the replacement token into the environment configuration
- never print or expose the token in logs or responses

Do not echo the token.

---

## 12. Development Rules

1. Backup before each new feature phase.
2. Preserve all working functionality.
3. Prefer existing architecture over adding dependencies.
4. Verify API behavior directly before implementing uncertain integrations.
5. Use raw Bale Bot API when the project already uses a custom HTTP client.
6. Build the affected Docker service after source changes.
7. Recreate the affected service after successful build.
8. Check service status and logs.
9. Test the real user flow before declaring success.
10. Do not continue past meaningful errors without fixing them.
11. Avoid temporary debug logging in production.
12. Keep Telegram functionality intact while modifying Bale.

---

## 13. Immediate Next Priorities

1. Rotate exposed Bale bot token.
2. Review and clean remaining Bale code duplication.
3. Verify all Bale callback/state paths.
4. Verify diagnosis → visit and identification → visit end-to-end.
5. Perform final Bale regression test.
6. Record a new stable backup/version.
7. Continue with the next project feature based on actual PROJECT_CONTEXT state.

