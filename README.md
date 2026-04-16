# SERRAFINS — Django Liquid Glass Website

Modern Django full-stack website with:
- Authentication (`register`, `login`, `logout`, protected `dashboard`)
- Aiven PostgreSQL-ready database configuration
- Frosted / liquid-glass visual theme (light blue + white)
- Smooth ambient and 3D tilt animations
- Secrets stored in `.env` (ignored by git)

## Stack
- Django 5
- PostgreSQL (Aiven) via env config
- Vanilla CSS/JS for glassmorphism + animation

## Project Structure
- `serrafins_site/` — Django project settings and root URLs
- `core/` — app with auth views/forms/routes
- `templates/` — frontend pages
- `static/css/style.css` — liquid glass theme
- `static/js/main.js` — ambient/3D effects
- `.env` — local secrets (gitignored)
- `.env.example` — safe template for environment variables

## Quick Start
1. Create and activate a Python virtual environment.
2. Install dependencies:
	- `pip install -r requirements.txt`
3. Copy and edit env values:
	- `.env` already exists; fill your real values, especially DB creds.
4. Run migrations:
	- `python manage.py migrate`
5. Run server:
	- `python manage.py runserver`

Open: `http://127.0.0.1:8000/`

## Aiven Database Setup
You can configure in either mode:

### Option A: `DATABASE_URL` (recommended)
Use Aiven connection URL in `.env`:
- `DATABASE_URL=postgresql://user:password@host:port/dbname?sslmode=require`

### Option B: Split variables
Set:
- `DB_ENGINE=django.db.backends.postgresql`
- `AIVEN_DB_HOST`
- `AIVEN_DB_PORT`
- `AIVEN_DB_NAME`
- `AIVEN_DB_USER`
- `AIVEN_DB_PASSWORD`
- `AIVEN_SSLMODE=require`

## Security Notes
- `.env` is excluded in `.gitignore`.
- Replace `DJANGO_SECRET_KEY` with a strong random value.
- Set `DEBUG=False` in production.
- Set production `ALLOWED_HOSTS`.
