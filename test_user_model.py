"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from models import FollowRequest, db, User, Message, Follows
from sqlalchemy.exc import IntegrityError
from flask_bcrypt import Bcrypt
# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "sqlite:///:memory:"


# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data
bcrypt = Bcrypt()
with app.app_context():
    db.create_all()
    bcrypt.init_app(app)

class UserModelTestCase(TestCase):
    """Test views for messages."""
    
    def setUp(self):
        """Create test client, add sample data."""
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.commit()
        self.client = app.test_client()

    def test_user_model(self):
        """Does basic model work?"""

        
        with app.app_context():
            u = User(
                email="test@test.com",
                username="testuser",
                password="HASHED_PASSWORD"
            )
            db.session.add(u)
            db.session.commit()

            # User should have no messages & no followers
            self.assertEqual(len(u.messages), 0)
            self.assertEqual(len(u.followers), 0)

    def test_user_following(self):
        """ Test if userA follow userB is successful"""

        with app.app_context():
            user1 = User(
                username="test1",
                email="test1@gmail.com",
                password="PASSWORD"
            )
            user2 = User(
                username="test2",
                email="test2@gmail.com",
                password="PASSWORD"
            )
            user1.following.append(user2)
            db.session.add(user1)
            db.session.add(user2)
            db.session.commit()

            self.assertEqual(user2.followers[0], user1)
            self.assertEqual(user1.following[0], user2)

            user1.following.remove(user2)
            db.session.commit()

            self.assertEqual(len(user1.following), 0)
            self.assertEqual(len(user2.followers), 0)


    def test_user_followed_by(self):
        with app.app_context():
            user1 = User(
                    username="test1",
                    email="test1@gmail.com",
                    password="PASSWORD"
                )
            user2 = User(
                username="test2",
                email="test2@gmail.com",
                password="PASSWORD"
            )
            user1.followers.append(user2)
            db.session.add(user1)
            db.session.add(user2)
            db.session.commit()

            self.assertEqual(user1.followers[0], user2)
            self.assertEqual(user2.following[0], user1)

    def test_user_create(self):
        """ 
            Test if user created with valid credenntials.

            Also test if email and username duplicated.
        """
        with app.app_context():
            user = User(
                email= "demo@gmail.com",
                username= "demo",
                password="123"
            )
            db.session.add(user)
            db.session.commit()
            self.assertIsInstance(user.id, int)
            self.assertEqual(user.id, 1)

            user2 = User(
                email= "demo@gmail.com",
                username= "demo2",
                password="123"
            )
            db.session.add(user2)
            self.assertRaises(IntegrityError, db.session.commit)
            self.assertEqual(user2.id, None)
            db.session.rollback()

            user3 = User(
                email= "demo3@gmail.com",
                username= "demo",
                password="123"
            )
            db.session.add(user3)
            self.assertRaises(IntegrityError, db.session.commit)
            db.session.rollback()

    def test_authenticate(self):
        with app.app_context():
            user = User(
                email='demo@gmail.com',
                username='demo',
                password= bcrypt.generate_password_hash('123123').decode('utf-8')
            )
            
            db.session.add(user)
            db.session.commit()
            new_user = User.authenticate('demo', '123123')
            self.assertIsInstance(new_user, User)
            self.assertEqual(new_user, user)

            bad_username_user = User.authenticate('demo2', '123123')
            self.assertEqual(bad_username_user, False)

            bad_password_user = User.authenticate('demo', '123123123')
            self.assertEqual(bad_password_user, False)
    def test_follow_private_user(self):
        with app.app_context():
            private_user = User(
                username='test1',
                email='test1@gmail.com',
                password='HASHED_PASSWORD',
                is_private=True
            )
            normal_user = User(
                username='test2',
                email='test2@gmail.com',
                password='HASHED_PASSWORD'
            )
            db.session.add(private_user)
            db.session.add(normal_user)
            db.session.commit()

            success = normal_user.follow(private_user)
            self.assertEqual(success, True)
            
            req = db.session.query(FollowRequest).filter(
                FollowRequest.user_being_followed_id == private_user.id,
                FollowRequest.user_follow_id == normal_user.id,
                FollowRequest.status == 'pending'
            ).first()
            self.assertIsNotNone(req)
    def test_accept_follow_request(self):
        with app.app_context():
            private_user = User(
                username='test1',
                email='test1@gmail.com',
                password='HASHED_PASSWORD',
                is_private=True
            )
            normal_user = User(
                username='test2',
                email='test2@gmail.com',
                password='HASHED_PASSWORD'
            )
            db.session.add(private_user)
            db.session.add(normal_user)
            db.session.commit()

            normal_user.follow(private_user)
            
            req = db.session.query(FollowRequest).filter(
                FollowRequest.requestee == private_user,
                FollowRequest.requester == normal_user,
                FollowRequest.status == 'pending'
            ).first()

            result = private_user.accept_request(req.id)

            self.assertEqual(result, True)
            self.assertIn(normal_user, private_user.followers)
            self.assertIn(private_user, normal_user.following)
            self.assertEqual(req.status, 'accepted')

    def test_deny_follow_request(self):
        with app.app_context():
            private_user = User(
                username='test1',
                email='test1@gmail.com',
                password='HASHED_PASSWORD',
                is_private=True
            )
            normal_user = User(
                username='test2',
                email='test2@gmail.com',
                password='HASHED_PASSWORD'
            )
            db.session.add(private_user)
            db.session.add(normal_user)
            db.session.commit()

            normal_user.follow(private_user)
            
            req = db.session.query(FollowRequest).filter(
                FollowRequest.requestee == private_user,
            ).first()
            result = private_user.deny_request(req.id)
            self.assertEqual(result, True)
            self.assertNotIn(normal_user, private_user.followers)
            self.assertNotIn(private_user, normal_user.following)
            self.assertEqual(req.status, 'denied')
    def test_cancel_follow_request(self):
        with app.app_context():
            private_user = User(
                username='test1',
                email='test1@gmail.com',
                password='HASHED_PASSWORD',
                is_private=True
            )
            normal_user = User(
                username='test2',
                email='test2@gmail.com',
                password='HASHED_PASSWORD'
            )
            db.session.add(private_user)
            db.session.add(normal_user)
            db.session.commit()

            normal_user.follow(private_user)

            req = db.session.query(FollowRequest).filter(
                FollowRequest.requestee == private_user,
            ).first()
            result = normal_user.cancel_request(req.id)
            self.assertEqual(result, True)
            self.assertNotIn(normal_user, private_user.followers)
            self.assertNotIn(private_user, normal_user.following)
            self.assertEqual(req.status, 'canceled')
    
    def test_block_user(self):
        with app.app_context():
            user1 = User(
                username='test1',
                email='test1@gmail.com',
                password='HASHED_PASSWORD'
            )
            user2 = User(
                username='test2',
                email='test2@gmail.com',
                password='HASHED_PASSWORD'
            )
            db.session.add(user1)
            db.session.add(user2)
            db.session.commit()

            user1.block(user2)
            self.assertIn(user2, user1.blocked_users)
            self.assertIn(user1, user2.blocking_users)
    def test_prevent_block_same_user(self):
        with app.app_context():
            user1 = User(
                username='test1',
                email='test1@gmail.com',
                password='HASHED_PASSWORD'
            )
            db.session.add(user1)
            db.session.commit()

            result = user1.block(user1)
            self.assertEqual(result, False)
            self.assertNotIn(user1, user1.blocked_users)
            self.assertNotIn(user1, user1.blocking_users)
    def test_unblock_user(self):
        with app.app_context():
            user1 = User(
                username='test1',
                email='test1@gmail.com',
                password='HASHED_PASSWORD'
            )
            user2 = User(
                username='test2',
                email='test2@gmail.com',
                password='HASHED_PASSWORD'
            )
            db.session.add(user1)
            db.session.add(user2)
            db.session.commit()

            user1.block(user2)
           
            user1.unblock(user2)
            self.assertNotIn(user2, user1.blocked_users)
            self.assertNotIn(user1, user2.blocking_users)
            



