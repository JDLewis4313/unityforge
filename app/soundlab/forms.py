from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, URL

class AudioUploadForm(FlaskForm):
    audio = FileField('Audio File', validators=[
        FileRequired(),
        FileAllowed(['mp3', 'wav', 'm4a', 'ogg', 'flac'], 'Audio files only!')
    ])
    submit = SubmitField('Upload')

class YouTubeForm(FlaskForm):
    youtube_url = StringField('YouTube URL', validators=[DataRequired(), URL()])
    submit = SubmitField('Download')

class SuggestForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=128)])
    link = StringField('Link/URL', validators=[Optional(), Length(max=512)])
    file = FileField('File', validators=[
        FileAllowed(['mp3', 'wav', 'm4a', 'ogg', 'flac'], 'Audio files only!')
    ])
    submit = SubmitField('Submit Suggestion')

class ShortClipForm(FlaskForm):
    clip = FileField('Short Clip', validators=[
        FileRequired(),
        FileAllowed(['mp3', 'wav', 'm4a'], 'Audio files only!')
    ])
    title = StringField('Title', validators=[DataRequired(), Length(max=128)])
    submit = SubmitField('Upload Clip')