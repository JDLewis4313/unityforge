web: bash -c "flask db upgrade && flask translate compile && gunicorn manage:app"
worker: rq worker manage-tasks
