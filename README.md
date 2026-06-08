# Запуск проекта

## Создать виртуальное окружение

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux/Mac:

```bash
source venv/bin/activate
```

## Установить зависимости

```bash
pip install -r requirements.txt
```

## Создать .env

```env
BOT_TOKEN=your_token
DATABASE_URL=postgresql://user:password@localhost:5432/medical_bot
APP_TIMEZONE=Europe/Moscow
```

## Запустить бота

```bash
python -m app.main
```
