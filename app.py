from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tripfront.db'
db = SQLAlchemy(app)

class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    goal_amount = db.Column(db.Float, nullable=False)
    max_participants = db.Column(db.Integer, nullable=False)
    details = db.Column(db.Text, nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    creator_id = db.Column(db.String(100), nullable=False)

class Commitment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    user_id = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    trip = db.relationship('Trip', backref=db.backref('commitments', lazy=True))

def init_db():
    with app.app_context():
        # This will create all tables
        db.drop_all()  # Drop all existing tables
        db.create_all()  # Create all tables fresh

# Initialize database
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=['GET', 'POST'])
def create_trip():
    if request.method == 'POST':
        name = request.form.get('name')
        goal_amount = float(request.form.get('goal_amount'))
        max_participants = int(request.form.get('max_participants'))
        details = request.form.get('details')
        deadline = datetime.strptime(request.form.get('deadline'), '%Y-%m-%d')
        
        code = secrets.token_urlsafe(6)
        trip = Trip(
            name=name,
            code=code,
            goal_amount=goal_amount,
            max_participants=max_participants,
            details=details,
            deadline=deadline,
            creator_id=request.remote_addr  # In a real app, use proper user authentication
        )
        
        db.session.add(trip)
        db.session.commit()
        
        return redirect(url_for('view_trip', code=code))
    
    return render_template('create_trip.html')

@app.route('/join', methods=['GET', 'POST'])
def join():
    if request.method == 'POST':
        code = request.form.get('code')
        trip = Trip.query.filter_by(code=code).first()
        if trip:
            return redirect(url_for('view_trip', code=code))
        flash('Invalid trip code')
    return render_template('join.html')

@app.route('/trip/<code>')
def view_trip(code):
    trip = Trip.query.filter_by(code=code).first_or_404()
    total_committed = sum(c.amount for c in trip.commitments)
    num_participants = len(trip.commitments)
    
    # Sort commitments by name for consistent display
    sorted_commitments = sorted(trip.commitments, key=lambda x: x.name.lower())
    
    return render_template('view_trip.html', 
                         trip=trip, 
                         total_committed=total_committed,
                         num_participants=num_participants,
                         commitments=sorted_commitments)

@app.route('/commit/<code>', methods=['POST'])
def commit_to_trip(code):
    trip = Trip.query.filter_by(code=code).first_or_404()
    name = request.form.get('name')
    amount = float(request.form.get('amount'))
    
    # Check if this name already has a commitment
    existing_commitment = Commitment.query.filter_by(
        trip_id=trip.id,
        name=name
    ).first()
    
    if existing_commitment:
        # Update existing commitment
        existing_commitment.amount = amount
        flash(f'Updated contribution for {name}!')
    else:
        # Check if we have room for a new participant
        if len(trip.commitments) >= trip.max_participants:
            flash('Trip is already full')
            return redirect(url_for('view_trip', code=code))
            
        # Create new commitment
        commitment = Commitment(
            trip_id=trip.id,
            user_id=request.remote_addr,  # Keep for tracking purposes
            name=name,
            amount=amount
        )
        db.session.add(commitment)
        flash(f'Added new contribution from {name}!')
    
    db.session.commit()
    return redirect(url_for('view_trip', code=code))

if __name__ == '__main__':
    app.run(debug=True, port=5004)
