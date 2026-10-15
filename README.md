# TezPOS Pro

Multi-role Restaurant POS & Management System.

## Tech Stack
Python, Django, Django REST Framework, Channels, PostgreSQL

## Setup
1. `python -m venv venv`
2. `venv\Scripts\activate`
3. `pip install -r requirements.txt`
4. Create `.env` with SECRET_KEY, DEBUG, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
5. `python manage.py migrate`
6. `python manage.py createsuperuser`
7. `python manage.py runserver`