from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, URL

class AudioUploadForm(FlaskForm):
    """Form for uploading audio files"""
    audio = FileField('Audio File', validators=[
        FileRequired(),
        FileAllowed(['mp3', 'wav', 'm4a', 'ogg', 'flac'], 'Audio files only!')
    ])
    notes = TextAreaField('Notes (Optional)', validators=[
        Optional(), 
        Length(max=500)
    ])
    submit = SubmitField('Upload')

class YouTubeForm(FlaskForm):
    """Form for downloading audio from YouTube"""
    youtube_url = StringField('YouTube URL', validators=[
        DataRequired(),
        URL(message='Please enter a valid URL')
    ])
    start_time = StringField('Start Time (Optional)', validators=[Optional()])
    end_time = StringField('End Time (Optional)', validators=[Optional()])
    submit = SubmitField('Download Audio')

class SuggestForm(FlaskForm):
    """Form for suggesting content"""
    title = StringField('Title', validators=[
        DataRequired(), 
        Length(min=3, max=128, message='Title must be between 3 and 128 characters')
    ])
    description = TextAreaField('Description', validators=[
        DataRequired(),  # Make description required to avoid NULL constraint error
        Length(max=280, message='Description must be less than 280 characters')
    ])
    link = StringField('Link/URL (Optional)', validators=[
        Optional(), 
        Length(max=512)
    ])
    file = FileField('Audio File (Optional)', validators=[
        Optional(),
        FileAllowed(['mp3', 'wav', 'm4a', 'ogg', 'flac'], 'Audio files only!')
    ])
    submit = SubmitField('Submit Suggestion')

class TrimForm(FlaskForm):
    """Form for trimming audio"""
    start_time = StringField('Start Time', validators=[
        DataRequired()
    ])
    end_time = StringField('End Time', validators=[
        Optional()
    ])
    submit = SubmitField('Trim Audio')