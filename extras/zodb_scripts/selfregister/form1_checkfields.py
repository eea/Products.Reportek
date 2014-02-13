## Script (Python) "form1_checkfields"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Check fields, return dict
##
request = container.REQUEST

errors = {}
# Check if form is submitted, by checking if a text field is present
if not request.has_key('organisation'):
    return errors

if len(request.get('organisation','')) == 0:
    errors['organisation'] = "Company name is mandatory"

if len(request.get('orgstreet','')) == 0:
    errors['orgstreet'] = "Company street is mandatory"

if len(request.get('orgmunicipality','')) == 0:
    errors['orgmunicipality'] = "Place 1 is mandatory"

if len(request.get('orgpostcode','')) == 0:
    errors['orgpostcode'] = "Postal code is mandatory"

if len(request.get('orgcountry','')) == 0:
    errors['orgcountry'] = "Country is mandatory"

# First contact person
if len(request.get('surname1','')) == 0:
    errors['surname1'] = "Surname is mandatory"

if len(request.get('givenname1','')) == 0:
    errors['givenname1'] = "First name is mandatory"

if request.get('email1','').find('@') < 0 or request.get('email1','').find('.') < 0:
    errors['email1'] = "Email for first contact must contain an @-sign and one or more periods"

if len(request.get('email1','')) == 0:
    errors['email1'] = "Email for first contact is mandatory"

if len(request.get('phone1','')) == 0:
    errors['phone1'] = "Phone for first contact is mandatory"

if len(request.get('euterms','')) == 0:
    errors['euterms'] = "You can't report to BDR unless you agree to the privacy statement"

# Check age
#agestr = request.get('age','')
#if agestr != '':
#    try: age = int(agestr)
#    except: age = 0
#    if age < 18 or age > 65:
#        errors['age'] = "Age must be a number between 18 and 65"

# Check gender - cannot be undecided
obligation = request.get('obligation','undecided')
if obligation == 'undecided':
    errors['obligation'] = "You must select an obligation"

return errors
