from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, Email, Length

from models import User

def MatchValidator(target_field_name, msg):
    def MatchValidator(form: FlaskForm, field):
        if field.data != getattr(form, target_field_name).data:
            raise ValidationError(msg)
    return MatchValidator

class MessageForm(FlaskForm):
    """Form for adding/editing messages."""

    text = TextAreaField('text', validators=[DataRequired()])


class UserAddForm(FlaskForm):
    """Form for adding users."""

    username = StringField('Username', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Length(min=6)])
    image_url = StringField('(Optional) Image URL')


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[Length(min=6)])

class ProfileForm(FlaskForm):
    """Form for update user profile"""

    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    image_url = StringField('(Optional) Image URL')
    header_image_url = StringField('(Optional) Header image URL')
    bio = StringField('Biography', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])

class ChangePasswordForm(FlaskForm):
    """Form for changing password"""
    def __init__(self, user: User, **kwargs):
        self.user = user 
        super().__init__(**kwargs)

    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[Length(min=6)])
    retype_password = PasswordField('Retype New Password', validators=[MatchValidator('new_password', 'New password and Retype new password should match'), Length(min=6)])
    def validate_current_password(self, *args, **kwargs):
        print('VALIDATE PASSWORD')
        user: User = self.user
        if not user.authenticate(user.username, self.current_password.data):
            raise ValidationError('Current password is incorrect')