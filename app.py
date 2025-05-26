import os
import random
import string
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
from datetime import datetime
from pymongo.mongo_client import MongoClient

# Initialize the Flask app
app = Flask(__name__)

# Set the path to store videos and allowed file extensions
UPLOAD_FOLDER = 'static/videos'
ALLOWED_EXTENSIONS = {'mp4'}

# Configure the Flask app
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'your-secret-key'

# MongoDB Atlas URI
uri = "mongodb+srv://bilelouelhazi:GM53gwbyL8Fra8iA@cluster0.pscy2as.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri)

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Initialize MongoDB database (🔁 Replace with your actual DB name)
mongo = client.get_database("YOUR_DB_NAME")

# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_id, username, email, role, points=0, referral_code=None, last_claimed=None):
        self.id = user_id
        self.username = username
        self.email = email
        self.role = role
        self.points = points
        self.referral_code = referral_code
        self.last_claimed = last_claimed  # Now it's initialized properly




def can_claim_daily_reward(last_claimed):
    if not last_claimed:
        return True
    last_claimed_date = last_claimed.date()
    today_date = datetime.today().date()
    return last_claimed_date < today_date

app.jinja_env.globals.update(can_claim_daily_reward=can_claim_daily_reward)



# Claim reward route
@app.route('/claim_reward', methods=['POST'])
@login_required
def claim_reward():
    user = mongo.db.users.find_one({'_id': ObjectId(current_user.id)})

    # Check if the user can claim their daily reward
    if can_claim_daily_reward(user.get('last_claimed')):
        # Add daily reward points (for example, 20 points)
        mongo.db.users.update_one(
            {'_id': ObjectId(current_user.id)},
            {'$inc': {'points': 20}, '$set': {'last_claimed': datetime.now()}}
        )
        return {"success": True, "message": "Daily reward claimed!"}
    else:
        return {"success": False, "message": "You have already claimed your daily reward."}




@login_manager.user_loader
def load_user(user_id):
    user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(
            str(user_data['_id']),
            user_data['username'],
            user_data['email'],
            user_data['role'],
            user_data['points'],
            user_data.get('referral_code', None),
            user_data.get('last_claimed', None)  # Ensure we get None if the field is missing
        )
    return None



# Helper function to check if the file extension is valid
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Helper function to generate a unique referral code
def generate_referral_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))


@app.route('/admin_users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))

    users = mongo.db.users.find()
    users = [{**user, 'id': str(user['_id'])} for user in users]
    return render_template('admin_users.html', users=users)


# Delete user
@app.route('/admin_delete_user/<user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    mongo.db.users.delete_one({'_id': ObjectId(user_id)})
    flash('User deleted', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/delete_user/<user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))

    mongo.db.users.delete_one({'_id': ObjectId(user_id)})
    flash('User deleted', 'success')
    return redirect(url_for('admin_users'))


@app.route('/edit_video/<video_id>', methods=['GET', 'POST'])
@login_required
def edit_video(video_id):
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))

    video = mongo.db.trailers.find_one({'_id': ObjectId(video_id)})

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        mongo.db.trailers.update_one({'_id': ObjectId(video_id)}, {'$set': {
            'title': title,
            'description': description
        }})
        flash('Video updated', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_video.html', video=video)


@app.route('/admin_delete_video/<video_id>', methods=['POST'])
@login_required
def admin_delete_video(video_id):
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    mongo.db.trailers.delete_one({'_id': ObjectId(video_id)})
    flash('Video deleted', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/edit_game/<game_id>', methods=['GET', 'POST'])
@login_required
def edit_game(game_id):
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))

    game = mongo.db.games.find_one({'_id': ObjectId(game_id)})

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        game_link = request.form['game_link']
        mongo.db.games.update_one({'_id': ObjectId(game_id)}, {'$set': {
            'title': title,
            'description': description,
            'game_url': game_link
        }})
        flash('Game updated', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_game.html', game=game)






@app.route('/admin_delete_game/<game_id>', methods=['POST'])
@login_required
def admin_delete_game(game_id):
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    mongo.db.games.delete_one({'_id': ObjectId(game_id)})
    flash('Game deleted', 'info')
    return redirect(url_for('admin_dashboard'))





# Home route
@app.route('/')
def home():
    return redirect(url_for('login'))




# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user_data = mongo.db.users.find_one({'email': email})

        if user_data and bcrypt.check_password_hash(user_data['password'], password):
            user = User(str(user_data['_id']), user_data['username'], user_data['email'], user_data['role'],
                        user_data['points'], user_data.get('referral_code', None))
            login_user(user)
            flash('Login successful', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html')




@app.template_filter('datetimeformat')
def datetimeformat(value):
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    return value






# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    referral_code = request.args.get('referral_code', None)  # Get referral code from URL

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        # Generate a unique referral code for the new user
        new_referral_code = generate_referral_code()

        # By default, set the user role as 'user' and initialize referral_code
        user_data = {
            'username': username,
            'email': email,
            'password': password,
            'role': 'user',
            'points': 0,
            'referral_code': new_referral_code,  # Store referral_code when registering
            'last_claimed': None  # Initialize last_claimed as None
        }

        # Insert the new user into the database
        mongo.db.users.insert_one(user_data)

        # If there's a referral code and it's valid, give the referring user 50 points
        if referral_code:
            referred_user = mongo.db.users.find_one({'referral_code': referral_code})
            if referred_user:
                mongo.db.users.update_one({'_id': ObjectId(referred_user['_id'])}, {'$inc': {'points': 50}})

        flash('Account created successfully, please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', referral_code=referral_code)





# Admin dashboard route
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))

    trailers = list(mongo.db.trailers.find())
    games = list(mongo.db.games.find())
    users = list(mongo.db.users.find())

    # Format users/trailers/games
    for user in users:
        user['id'] = str(user['_id'])

    for trailer in trailers:
        trailer['id'] = str(trailer['_id'])

    for game in games:
        game['id'] = str(game['_id'])

    giftcards = list(mongo.db.giftcards.find())
    for gc in giftcards:
        gc['id'] = str(gc['_id'])

    return render_template('admin_dashboard.html', trailers=trailers, games=games, users=users, giftcards=giftcards)




# Add video route for admin
@app.route('/admin_add_video', methods=['POST'])
@login_required
def admin_add_video():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))

    title = request.form['title']
    description = request.form['description']

    video_file = request.files['video_file']
    image_file = request.files.get('image_file')  # get image if uploaded

    video_filename = None
    image_filename = None

    if video_file and allowed_file(video_file.filename):
        video_filename = secure_filename(video_file.filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
        video_file.save(video_path)

    if image_file and image_file.filename != '':
        image_filename = secure_filename(image_file.filename)
        image_path = os.path.join('static/uploads', image_filename)  # you can separate images and videos
        image_file.save(image_path)

    mongo.db.trailers.insert_one({
        'title': title,
        'video_url': f'/static/videos/{video_filename}',
        'description': description,
        'image': image_filename  # optional
    })

    flash('Video added successfully', 'success')
    return redirect(url_for('admin_dashboard'))






# Add game route for admin
@app.route('/admin_add_game', methods=['POST'])
@login_required
def admin_add_game():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))

    title = request.form['title']
    description = request.form['description']
    game_link = request.form['game_link']
    image = request.files.get('image')  # get the uploaded file

    image_filename = None
    if image and image.filename != '':
        filename = secure_filename(image.filename)
        image_path = os.path.join('static/uploads', filename)
        image.save(image_path)
        image_filename = filename

    # Save to database
    mongo.db.games.insert_one({
        'title': title,
        'game_url': game_link,
        'description': description,
        'image': image_filename  # store image filename in DB
    })

    flash('Game added successfully', 'success')
    return redirect(url_for('admin_dashboard'))





@app.route('/user_dashboard')
@login_required
def user_dashboard():
    trailers = mongo.db.trailers.find()
    games = mongo.db.games.find()

    referral_link = url_for('register', referral_code=current_user.referral_code, _external=True)
    giftcards = list(mongo.db.giftcards.find({'claimed': False}))

    # Get user's last claimed time from DB
    user = mongo.db.users.find_one({'_id': ObjectId(current_user.id)})
    can_claim = can_claim_daily_reward(user.get('last_claimed'))

    # Fetch full gift card details for purchased gift cards
    purchased_giftcards = []
    for card_id in user.get('purchased_giftcards', []):
        giftcard = mongo.db.giftcards.find_one({"_id": ObjectId(card_id)})
        if giftcard:
            purchased_giftcards.append(giftcard)

    return render_template(
        'user_dashboard.html',
        trailers=trailers,
        games=games,
        referral_link=referral_link,
        can_claim=can_claim,
        giftcards=giftcards,
        purchased_giftcards=purchased_giftcards
    )




@app.route('/buy_giftcard/<giftcard_id>', methods=['POST'])
@login_required
def buy_giftcard(giftcard_id):
    user = mongo.db.users.find_one({'_id': ObjectId(current_user.id)})
    giftcard = mongo.db.giftcards.find_one({"_id": ObjectId(giftcard_id)})

    if not giftcard:
        flash("Giftcard not found.", "error")
        return redirect(url_for('user_dashboard'))

    if giftcard.get('claimed', False):
        flash("Giftcard has already been claimed.", "error")
        return redirect(url_for('user_dashboard'))

    if user['points'] < giftcard['cost']:
        flash("You don't have enough points to purchase this giftcard.", "error")
        return redirect(url_for('user_dashboard'))

    # Deduct points and update user data
    mongo.db.users.update_one(
        {'_id': ObjectId(current_user.id)},
        {
            '$inc': {'points': -giftcard['cost']},
            '$push': {'purchased_giftcards': giftcard_id}
        }
    )

    # Mark giftcard as claimed
    mongo.db.giftcards.update_one(
        {'_id': ObjectId(giftcard_id)},
        {'$set': {'claimed': True, 'claimed_by': current_user.username, 'claimed_at': datetime.utcnow()}}
    )

    flash("Giftcard purchased successfully!", "success")
    return redirect(url_for('user_dashboard'))



# Watch trailer route
@app.route('/watch_trailer/<trailer_id>', methods=['GET'])
@login_required
def watch_trailer(trailer_id):
    trailer = mongo.db.trailers.find_one({'_id': ObjectId(trailer_id)})
    if trailer:
        return render_template('watch_trailer.html', trailer=trailer)
    return redirect(url_for('user_dashboard'))




# Play game route
@app.route('/play_game/<game_id>', methods=['GET'])
@login_required
def play_game(game_id):
    game = mongo.db.games.find_one({'_id': ObjectId(game_id)})
    if game:
        return render_template('play_game.html', game=game)
    return redirect(url_for('user_dashboard'))





@app.route('/admin_add_giftcard', methods=['POST'])
@login_required
def admin_add_giftcard():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))

    name = request.form['name']
    code = request.form['code']
    cost = int(request.form['cost'])

    mongo.db.giftcards.insert_one({
        'name': name,
        'code': code,
        'cost': cost,
        'claimed': False
    })

    flash('Gift card added successfully!', 'success')
    return redirect(url_for('admin_dashboard'))




# Claim reward after watching video
@app.route('/claim_video_reward', methods=['POST'])
@login_required
def claim_video_reward():
    mongo.db.users.update_one({'_id': ObjectId(current_user.id)}, {'$inc': {'points': 20}})
    return {"success": True}




@app.route('/claim_play_reward', methods=['POST'])
@login_required
def claim_play_reward():
    # Increment the points by 30 for the logged-in user
    mongo.db.users.update_one({'_id': ObjectId(current_user.id)}, {'$inc': {'points': 30}})
    return {"success": True}




@app.route('/test')
def test():
    return render_template('test.html')


# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)