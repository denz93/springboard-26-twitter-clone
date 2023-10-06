from datetime import datetime, timedelta
import os
import bcrypt

from flask import Flask, render_template, request, flash, redirect, session, g, url_for
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError, DatabaseError
from sqlalchemy import or_
from auth import auth
from forms import ChangePasswordForm, ProfileForm, UserAddForm, LoginForm, MessageForm
from libs.time_relative import get_age
from models import db, connect_db, User, Message
from seed import seed

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
ENV = os.getenv('ENV', 'DEV')
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_ECHO'] = bool(os.environ.get('SQLALCHEMY_ECHO', False))
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
if ENV == 'DEV':
    toolbar = DebugToolbarExtension(app)

connect_db(app)

##############################################################################
# add custom filter to jinja
app.jinja_env.filters['get_age'] = get_age

##############################################################################
# flask helpers
def prohibit(message):
    return render_template('prohibited.html', message=message), 403

# bind MessageForm to g
@app.before_request
def add_message_form_across_requests():
    g.message_form = MessageForm()
##############################################################################
# User change password
@app.route('/change-password', methods=['GET', 'POST'])
@auth()
def change_password():
    form = ChangePasswordForm(g.user)
    user: User = g.user
    if not form.is_submitted():
        return render_template('users/change_password.html', form=form, user=user)
    
    if form.validate():
        user.update_password(form.new_password.data)
        db.session.add(user)
        db.session.commit()
        flash('Your password has been updated!', 'success')
        return render_template('users/change_password.html', form=form, user=user)

    
    return render_template('users/change_password.html', form=form, user=user), 404
     
    
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])
    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    # IMPLEMENT THIS
    do_logout()
    return redirect('/login')


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())
    return render_template('users/show.html', user=user, messages=messages)


@app.route('/users/<int:user_id>/following')
@auth()
def show_following(user_id):
    """Show list of people this user is following."""

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
@auth()
def users_followers(user_id):
    """Show list of followers of this user."""

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
@auth()
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    followed_user: User = User.query.get_or_404(follow_id)

    g.user.follow(followed_user)
    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
@auth()
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
@auth()
def profile():
    """Update profile for current user."""

    user: User = g.get('user')
    form = ProfileForm(obj=user)
    form_data = form.data
    if form.validate_on_submit():
        if not User.authenticate(user.username, form_data['password']):
            data = User.authenticate(user.username, form_data['password'])
            flash("Update profile failed due to incorrect password", "danger")
            return redirect("/")
        user.username = form_data['username']
        user.email = form_data['email']
        user.image_url = form_data['image_url']
        user.header_image_url = form_data['header_image_url']
        user.bio = form_data['bio']
        db.session.is_modified = True
        try:
            db.session.commit()
            return redirect(f'/users/{user.id}')
        except DatabaseError:
            db.session.rollback()
            flash('Username or email already exists', 'danger')
    return render_template("users/profile.html", user=user, form=form)


@app.route('/users/delete', methods=["POST"])
@auth()
def delete_user():
    """Delete user."""

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")

@app.route('/users/add_like/<int:message_id>', methods=['POST'])
@auth()
def toggle_like(message_id: int):
    if message_id in [message.id for message in g.user.likes]:
        message = [m for m in g.user.likes if m.id == message_id][0]
        g.user.likes.remove(message)
        flash(f'You just unlike wrabler #{message.id}', 'info')

    else:
        message = Message.query.get(message_id)
        g.user.likes.append(message)
        flash(f'You just like wrabler #{message.id}', 'success')
    db.session.commit()
    return redirect('/')

@app.route('/users/<int:user_id>/likes')
def users_likes(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('users/likes.html', user=user, messages=user.likes)

@app.route('/users/<int:user_id>/change-status', methods=["POST"])
@auth()
def user_change_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id != g.user.id:
        return prohibit('You can only change your own status.')
    
    user.is_private = request.form.get('is_private', False) in ('y', 'yes', 'True', 'true')
    db.session.commit()

    return redirect(f'/users/{user.id}')
@app.route('/follow-request/<int:request_id>/cancel', methods=["POST"])
@auth()
def cancel_follow_request(request_id):
    user:User = g.user
    result = user.cancel_request(request_id)
    if result:
        flash(f'Follow request canceled', 'success')
    else:
        flash(f'Follow request could not be canceled', 'danger')
    return redirect(url_for('show_following', user_id=user.id))
@app.route('/follow-request/<int:request_id>/accept', methods=["POST"])
@auth()
def accept_follow_request(request_id):
    user:User = g.user
    result = user.accept_request(request_id)
    if result:
        flash(f'Follow request accepted', 'success')
    else:
        flash(f'Follow request could not be accepted', 'danger')
    return redirect(url_for('users_followers', user_id=user.id)) 
@app.route('/follow-request/<int:request_id>/deny', methods=["POST"])
@auth()
def deny_follow_request(request_id):
    user:User = g.user
    result = user.deny_request(request_id)
    if result:
        flash(f'Follow request denied', 'success')
    else:
        flash(f'Follow request could not be denied', 'danger')
    return redirect(url_for('users_followers', user_id=user.id))

@app.route('/users/<int:user_id>/block', methods=["POST"])
@auth()
def block_user(user_id):
    user:User = g.user
    target_user = User.query.get_or_404(user_id)
    result = user.block(target_user)
    if result:
        flash(f'You\'ve blocked @{target_user.username}', 'success')
    else:
        flash(f'User @{target_user.username} could not be blocked', 'danger')
    return redirect(url_for('users_show', user_id=target_user.id))
@app.route('/users/<int:user_id>/unblock', methods=["POST"])
@auth()
def unblock_user(user_id):
    user:User = g.user
    target_user = User.query.get_or_404(user_id)
    result = user.unblock(target_user)
    if result:
        flash(f'You\'ve unblocked @{target_user.username}', 'success')
    else:
        flash(f'User @{target_user.username} could not be unblocked', 'danger')
    return redirect(url_for('users_show', user_id=target_user.id))

##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
@auth()
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
@auth()
def messages_destroy(message_id):
    """Delete a message."""

    msg = Message.query.get(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        following_user_ids = [ user.id for user in g.user.following]
        following_user_ids.append(g.user.id)
        messages = (Message
                    .query
                    .filter(Message.user_id.in_(following_user_ids))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())

        return render_template('home.html', messages=messages)

    else:
        return render_template('home-anon.html')


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req

##############################################################################
# Secret route for seeding
@app.post('/seed')
def seed_route():
    """Seeds the database."""
    password = request.get_json().get('password', '')
    PW = '$2b$12$MpLwNiNlwAi7Gc38nsSHjOHSDFroaFqt7HQdWYxSPG1NIi8ka/oMy'.encode('utf-8')
    is_valid = bcrypt.checkpw(password.encode('utf-8'), PW)

    if is_valid:
        seed()
    return 'OK', 200
