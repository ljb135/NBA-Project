from flask import Flask, url_for, render_template, redirect
import Web_App.forms
import os

template_dir = os.path.abspath('../../NBAWebScrape/Web_App/templates')
print(template_dir)

app = Flask(__name__, template_folder=template_dir)
app.config['SECRET_KEY'] = 'any secret string'


@app.route('/', methods=('GET', 'POST'))
def contact():
    form = Web_App.forms.SelectionForm()
    if form.validate_on_submit():
        return redirect(url_for('success'))
    return render_template('request.html', form=form)


app.run(host='0.0.0.0', port=50000, debug=True)
