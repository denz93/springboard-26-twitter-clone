"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
from unittest import TestCase
from flask import session
from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "sqlite:///:memory:"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data
with app.app_context():
    db.create_all()


# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""
        with app.app_context():
            User.query.delete()
            Message.query.delete()

            self.client = app.test_client()

            testuser = User.signup(username="testuser",
                                        email="test@test.com",
                                        password="testuser",
                                        image_url=None)
            db.session.commit()
            self.testuser = User(id=testuser.id, username=testuser.username, email=testuser.email, password=testuser.password)

    def test_add_message(self):
        """Can use add a message?"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test
            resp = c.post("/messages/new", data={"text": "Hello"})
            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            with app.app_context():
                msg = db.session.query(Message).one()
                self.assertEqual(msg.text, "Hello")
    def test_del_message(self):
        msg_id = None
        with app.app_context():
            msg = Message(text='test message', user_id=self.testuser.id)
            db.session.add(msg)
            db.session.commit()
            msg_id = msg.id

        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
        res = client.post(f'/messages/{msg_id}/delete')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.location, f'/users/{self.testuser.id}')

    def test_prevent_add_del_message_from_unauthorized(self):
        msg_id = None
        with app.app_context():
            msg = Message(text='test message', user_id=self.testuser.id)
            db.session.add(msg)
            db.session.commit()
            msg_id = msg.id

        with self.client as client:
            res = client.post('/messages/new', data={"text": "Hello"})
            self.assertEqual(res.status_code, 401)

            res = client.post(f'/messages/{msg_id}/delete')
            self.assertEqual(res.status_code, 401)
