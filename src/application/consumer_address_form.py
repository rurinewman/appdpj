# xu yong lin
from wtforms import Form, validators, TextAreaField, SelectField


class ConsumerAddressForm(Form):
    # addressType = SelectField('Restaurant', choices=[('', '---'), (1, 'Home'), (2, 'Workplace'), (3, '3: Others')])
    consumer_homeAddress = TextAreaField('Home Address', [validators.optional(), validators.length(max=200)])
    consumer_workAddress = TextAreaField('Work Address', [validators.optional(), validators.length(max=200)])
    consumer_otherAddress = TextAreaField('Other Address', [validators.optional(), validators.length(max=200)])
