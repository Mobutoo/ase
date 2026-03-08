# Ase — Human-Centric Flow Engine

> "The power to make things happen." (Yoruba)

Ase is a human-oriented productivity app that bridges project management with human execution. Built on adaptive flow modes, energy tracking, and ambient music integration.

Forked from [PomoTracker](https://github.com/viodid/PomoTracker) (MIT License).

## Stack

- **Backend**: Django 4.2 + DRF + PostgreSQL + Redis
- **Frontend**: React 18 + Vite + Tailwind CSS
- **Docker**: Multi-stage build (single container)

## Development

```bash
# Backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# Frontend
cd frontend && npm install && npm run dev
```

## License

MIT
