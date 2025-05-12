from flask_sqlalchemy import SQLAlchemy

# Create a new SQLAlchemy object
db = SQLAlchemy()

class Meal(db.Model):
    """Model for unique meals from the XML data"""
    __tablename__ = 'meals'
    
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False, unique=True)
    category = db.Column(db.String(100))
    marking = db.Column(db.String(100))
    nutritional_values = db.Column(db.Text)
    co2_value = db.Column(db.Float)
    co2_rating = db.Column(db.String(10))
    co2_savings = db.Column(db.Float)
    water_value = db.Column(db.Float)
    water_rating = db.Column(db.String(10))
    animal_welfare = db.Column(db.String(10))
    rainforest = db.Column(db.String(10))
    
    def __repr__(self):
        return f'<Meal {self.description[:30]}...>'

class MensaMealOccurrence(db.Model):
    """Model to track when and where each meal is served"""
    __tablename__ = 'mensa_meal_occurrences'
    
    id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey('meals.id'), nullable=False)
    mensa_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    price_student = db.Column(db.Float)
    price_employee = db.Column(db.Float)
    price_guest = db.Column(db.Float)
    price_student_card = db.Column(db.Float)
    price_employee_card = db.Column(db.Float)
    price_guest_card = db.Column(db.Float)
    notes = db.Column(db.Text)
    
    # Relationship to the meal
    meal = db.relationship('Meal', backref=db.backref('occurrences', lazy=True))
    
    def __repr__(self):
        return f'<MensaMealOccurrence {self.mensa_name} {self.date} {self.meal_id}>'

class XXXLutzChangingMeal(db.Model):
    """Model for changing XXXLutz meals (weekly special dishes)"""
    __tablename__ = 'xxxlutz_changing_meals'
    
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False, unique=True)
    marking = db.Column(db.String(100))
    price_student = db.Column(db.Float)
    price_employee = db.Column(db.Float)
    price_guest = db.Column(db.Float)
    nutritional_values = db.Column(db.Text)
    
    def __repr__(self):
        return f'<XXXLutzChangingMeal {self.description[:30]}...>'

class XXXLutzFixedMeal(db.Model):
    """Model for fixed/permanent XXXLutz meals (standard menu)"""
    __tablename__ = 'xxxlutz_fixed_meals'
    
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False, unique=True)
    marking = db.Column(db.String(100))
    price_student = db.Column(db.Float)
    price_employee = db.Column(db.Float)
    price_guest = db.Column(db.Float)
    nutritional_values = db.Column(db.Text)
    
    def __repr__(self):
        return f'<XXXLutzFixedMeal {self.description[:30]}...>'
        
class MealVote(db.Model):
    """Model for meal votes (upvotes and downvotes)"""
    __tablename__ = 'meal_votes'
    
    id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey('meals.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    client_id = db.Column(db.String(100), nullable=False)  # Cookie-based identifier
    vote_type = db.Column(db.String(10), nullable=False)  # 'up' or 'down'
    
    # Add a unique constraint to prevent multiple votes from the same client for the same meal on the same day
    __table_args__ = (
        db.UniqueConstraint('meal_id', 'date', 'client_id', name='unique_vote_per_day'),
    )
    
    # Relationship to the meal
    meal = db.relationship('Meal', backref=db.backref('votes', lazy=True))
    
    def __repr__(self):
        return f'<MealVote {self.meal_id} {self.vote_type} {self.date}>'
        
class PageView(db.Model):
    """Model for tracking page views"""
    __tablename__ = 'page_views'
    
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<PageView {self.count}>'