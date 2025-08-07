from app import create_app, db
from app.models import User, Post, Message, Notification, Task
import sqlalchemy as sa
import sqlalchemy.orm as so

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'app': app,
        'db': db,
        'sa': sa,
        'so': so,
        'User': User,
        'Post': Post,
        'Message': Message,
        'Notification': Notification,
        'Task': Task
    }

if __name__ == '__main__':
    app.run()
