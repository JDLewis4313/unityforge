from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, Optional
from app.models import Scripture

class ScriptureSearchForm(FlaskForm):
    query = StringField('Search Scripture', validators=[DataRequired(), Length(min=1, max=100)])
    submit = SubmitField('Search')

class JournalEntryForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=1, max=140)])
    content = TextAreaField('Content', validators=[DataRequired(), Length(min=1, max=5000)])
    scripture_id = IntegerField('Scripture Reference', validators=[Optional()])
    submit = SubmitField('Save Entry')
    
    def __init__(self, *args, **kwargs):
        super(JournalEntryForm, self).__init__(*args, **kwargs)
        # Populate scripture choices
        scriptures = Scripture.query.order_by(Scripture.date.desc()).limit(20).all()
        self.scripture_choices = [(s.id, f"{s.reference} ({s.date})") for s in scriptures]

class ScripturePostForm(FlaskForm):
    reference = StringField('Scripture Reference', validators=[DataRequired(), Length(min=1, max=100)])
    custom_text = TextAreaField('Add Your Thoughts', validators=[Optional(), Length(max=280)])
    submit = SubmitField('Share Scripture')