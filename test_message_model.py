from unittest import TestCase
from models import db, Message, User
from sqlalchemy.exc import IntegrityError
from os import environ
from datetime import datetime

environ['DATABASE_URL'] = 'sqlite:///:memory:'
from app import app

with app.app_context(): 
  db.create_all()

class MessageModelTest(TestCase):
  def setUp(self) -> None:
    with app.app_context():
      Message.query.delete()
      User.query.delete()

      self.user = User(
        username='testuser',
        email='test@test.com',
        password='HASHED_PASSWORD'
      )
      db.session.add(self.user)
      db.session.commit()

  
  def test_message_model(self):
    with app.app_context():
      message = Message(
        text='test message',
        user=self.user,
      )
      db.session.add(message)
      db.session.commit()
      self.assertEqual(message.text, 'test message')
      self.assertEqual(message.user, self.user)
      self.assertEqual(message.id, 1)
      self.assertEqual(message.timestamp.date(), datetime.utcnow().date())
