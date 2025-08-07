import os
from flask import Blueprint
import click
from datetime import datetime, date, timedelta

bp = Blueprint('cli', __name__, cli_group=None)

@bp.cli.group()
def translate():
    """Translation and localization commands."""
    pass

@translate.command()
@click.argument('lang')
def init(lang):
    """Initialize a new language."""
    if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
        raise RuntimeError('extract command failed')
    if os.system(
            'pybabel init -i messages.pot -d app/translations -l ' + lang):
        raise RuntimeError('init command failed')
    os.remove('messages.pot')

@translate.command()
def update():
    """Update all languages."""
    if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
        raise RuntimeError('extract command failed')
    if os.system('pybabel update -i messages.pot -d app/translations'):
        raise RuntimeError('update command failed')
    os.remove('messages.pot')

@translate.command()
def compile():
    """Compile all languages."""
    if os.system('pybabel compile -d app/translations'):
        raise RuntimeError('compile command failed')

# Daily Scripture Commands
@bp.cli.group()
def scripture():
    """Scripture management commands."""
    pass

@scripture.command()
@click.option('--year', default=None, type=int, help='Year to populate (default: current year)')
def populate_verses(year):
    """Populate database with all 365 daily verses."""
    from app import db
    from app.models import Scripture
    from app.logos.daily_verses import DAILY_VERSES
    from app.logos.utils import fetch_scripture_from_api
    
    if year is None:
        year = datetime.now().year
    
    click.echo(f"Populating daily verses for {year}...")
    start_date = date(year, 1, 1)
    success_count = 0
    error_count = 0
    
    with click.progressbar(range(365), label='Loading verses') as bar:
        for day_num in bar:
            current_date = start_date + timedelta(days=day_num)
            daily_reference = DAILY_VERSES[day_num]
            
            # Check if already exists
            existing = Scripture.query.filter_by(date=current_date).first()
            if existing:
                continue
            
            try:
                scripture = fetch_scripture_from_api(daily_reference)
                if scripture:
                    scripture.date = current_date
                    db.session.commit()
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                click.echo(f"\nError with {daily_reference}: {e}", err=True)
    
    click.echo(f"\n✓ Completed! Added {success_count} verses, {error_count} errors")

@scripture.command()
def test_daily():
    """Test today's daily verse."""
    from app.logos.utils import get_verse_of_the_day
    
    verse = get_verse_of_the_day()
    click.echo(f"Today's verse ({date.today()}):")
    click.echo(f"Reference: {verse.book} {verse.chapter}:{verse.verse}")
    click.echo(f"Text: {verse.text[:100]}...")
    click.echo(f"Translation: {verse.translation}")

@scripture.command()
def create_posts():
    """Manually create daily scripture posts for all users."""
    from app.tasks import create_daily_scripture_posts
    
    result = create_daily_scripture_posts()
    click.echo(result)

@scripture.command()
def list_jobs():
    """List all scheduled jobs."""
    from rq_scheduler import Scheduler
    from app import create_app
    
    app = create_app()
    scheduler = Scheduler(connection=app.redis)
    
    jobs = scheduler.get_jobs()
    if jobs:
        click.echo("Scheduled jobs:")
        for job in jobs:
            click.echo(f"  {job.id}: {job.func_name}")
    else:
        click.echo("No scheduled jobs found")
        