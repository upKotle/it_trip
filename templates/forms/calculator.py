from flask_wtf import FlaskForm
from wtforms import SubmitField
from wtforms.validators import DataRequired

class WasteCalculatorForm(FlaskForm):
    submit = SubmitField('Рассчитать стоимость')