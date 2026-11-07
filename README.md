# -Encyclopedia.
Wikipedia is a free online encyclopedia that consists of a number of encyclopedia entries on various topics. Encyclopedias are divided into articles or entries that are arranged alphabetically by article name

## Run locally

Requires Python 3.10 or newer.

```sh
python -m pip install -r requirements.txt
python manage.py migrate
DJANGO_DEBUG=True python manage.py runserver
```

Open http://127.0.0.1:8000/. Entries are stored as Markdown files in `entries/`.
Use the sidebar to search, create a page, or visit a random entry. Each entry has
an Edit Page link. Titles are unique (case-insensitively), and rendered Markdown
is sanitized before display.

Run checks and tests with:

```sh
python manage.py check
python manage.py test encyclopedia
```

For deployment, set `DJANGO_SECRET_KEY` to a private, persistent value and
`DJANGO_ALLOWED_HOSTS` to a comma-separated list of your hostnames. Debug mode is
off by default; the development fallback key is generated at startup.
Configure your production server to serve collected static files.
