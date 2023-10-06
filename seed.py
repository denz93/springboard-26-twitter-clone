"""Seed database with sample data from CSV Files."""

from csv import DictReader
from models import db
from models import User, Message, Follows
def seed():

    db.drop_all()
    db.create_all()

    with open('generator/users.csv') as users:
        db.session.bulk_insert_mappings(User, DictReader(users))
    db.session.commit()

    users = db.session.query(User).add_column(User.id).all()

    with open('generator/messages.csv') as messages:
        messages_reader = DictReader(messages)
        final_list = []
        for m in messages_reader:
            m['user_id'] = users[int(m['user_id']) - 1].id
            final_list.append(m)
        db.session.bulk_insert_mappings(Message, final_list)

    db.session.commit()

    with open('generator/follows.csv') as follows:
        follows_reader = DictReader(follows)
        final_follows = []
        for f in follows_reader:
            f['user_being_followed_id'] = users[int(f['user_being_followed_id']) - 1].id
            f['user_following_id'] = users[int(f['user_following_id']) - 1].id
            final_follows.append(f)
        db.session.bulk_insert_mappings(Follows, final_follows)

    db.session.commit()
    

