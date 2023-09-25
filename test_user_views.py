from unittest import TestCase

from flask.testing import FlaskClient
from models import db, User 
from os import environ
environ['DATABASE_URL'] = 'sqlite:///:memory:'
from app import app, CURR_USER_KEY
from flask import session, g
from flask_bcrypt import Bcrypt
from bs4 import BeautifulSoup

with app.app_context():
  db.create_all()
  app.config["WTF_CSRF_ENABLED"] = False
bcrypt = Bcrypt(app)

class UserViewTest(TestCase):
  def setUp(self) -> None:
    with app.app_context():
      User.query.delete()
      user = User(
        username='testuser',
        email='test@test.com',
        password= bcrypt.generate_password_hash('123123').decode('utf-8')
      )
      db.session.add(user)
      db.session.commit()
      self.user_id = user.id

  def login(self, client: FlaskClient):
    with client.session_transaction() as sess:
      sess[CURR_USER_KEY] = self.user_id

  def test_login(self):
    with app.test_client() as client:
      resp = client.post('/login', data={'username': 'testuser', 'password': '123123'}, follow_redirects=True)

      self.assertEqual(resp.status_code, 200)
      self.assertEqual(session[CURR_USER_KEY], self.user_id)
      self.assertEqual(len(resp.history), 1)

      
  def test_allow_seeing_following_follower(self):
    with app.test_client() as client:
      self.login(client)

      res = client.get(f'/users/{self.user_id}/following', follow_redirects=True)
      self.assertEqual(len(res.history), 0)
      self.assertEqual(res.status_code, 200)

      res = client.get(f'/users/{self.user_id}/followers', follow_redirects=True)
      self.assertEqual(len(res.history), 0)
      self.assertEqual(res.status_code, 200)
  def test_disallow_seeing_following_follower(self):
    with app.test_client() as client:
      res = client.get(f'/users/{self.user_id}/following', follow_redirects=True)
      self.assertEqual(len(res.history), 1)
      self.assertEqual(res.request.path, '/')
      res = client.get(f'/users/{self.user_id}/followers', follow_redirects=True)
      self.assertEqual(len(res.history), 1)
      self.assertEqual(res.request.path, '/')

