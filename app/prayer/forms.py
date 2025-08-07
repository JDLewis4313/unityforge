from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField, DateField
from wtforms.validators import DataRequired, Length, Optional

class SharePrayerForm(FlaskForm):
    title = StringField('Prayer Title', validators=[DataRequired(), Length(1, 200)])
    description = TextAreaField('Prayer Description', validators=[Optional(), Length(0, 500)])
    
    prayer_type = SelectField('Prayer Type', choices=[
        ('personal', '🙏 Personal Prayer'),
        ('pastoral', '⛪ Pastoral Prayer'),
        ('worship', '🎵 Worship Prayer'),
        ('scripture', '📖 Scripture Prayer'),
        ('congregational', '💒 Congregational Prayer'),
        ('daily', '🌅 Daily Devotion')
    ], default='personal')
    
    spiritual_focus = SelectField('Spiritual Focus', choices=[
        ('', 'Select Focus...'),
        ('healing', 'Healing'),
        ('gratitude', 'Gratitude'),
        ('guidance', 'Guidance'),
        ('peace', 'Peace'),
        ('strength', 'Strength'),
        ('forgiveness', 'Forgiveness'),
        ('protection', 'Protection'),
        ('worship', 'Worship'),
        ('thanksgiving', 'Thanksgiving'),
        ('intercession', 'Intercession')
    ], validators=[Optional()])
    
    scripture_reference = StringField('Scripture Reference (Optional)', 
                                    validators=[Optional(), Length(0, 100)],
                                    render_kw={"placeholder": "e.g., Psalm 23:1"})
    
    church_service_date = DateField('Church Service Date (Optional)', validators=[Optional()])
    
    file = FileField('Prayer Audio File', 
                    validators=[FileRequired(), FileAllowed(['mp3', 'wav', 'm4a', 'ogg'], 'Audio files only!')])
    
    is_public = BooleanField('Share with Community', default=True)
    
    submit = SubmitField('Share Prayer')

class CraftPrayerForm(FlaskForm):
    title = StringField('Prayer Title', validators=[DataRequired(), Length(1, 200)])
    prayer_text = TextAreaField('Written Prayer', validators=[DataRequired(), Length(1, 2000)],
                               render_kw={"rows": 8, "placeholder": "Dear Lord..."})
    
    prayer_type = SelectField('Prayer Type', choices=[
        ('personal', '🙏 Personal Prayer'),
        ('scripture', '📖 Scripture-Based Prayer'),
        ('gratitude', '🙏 Gratitude Prayer'),
        ('intercession', '🤲 Intercessory Prayer')
    ], default='personal')
    
    spiritual_focus = SelectField('Spiritual Focus', choices=[
        ('', 'Select Focus...'),
        ('healing', 'Healing'),
        ('gratitude', 'Gratitude'),
        ('guidance', 'Guidance'),
        ('peace', 'Peace'),
        ('strength', 'Strength'),
        ('forgiveness', 'Forgiveness'),
        ('family', 'Family'),
        ('ministry', 'Ministry'),
        ('growth', 'Spiritual Growth')
    ], validators=[Optional()])
    
    scripture_reference = StringField('Related Scripture (Optional)', 
                                    validators=[Optional(), Length(0, 100)],
                                    render_kw={"placeholder": "e.g., Matthew 6:9-13"})
    
    is_public = BooleanField('Share with Community', default=False)
    
    submit = SubmitField('Save Prayer')