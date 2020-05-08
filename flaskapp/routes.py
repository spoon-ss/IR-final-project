import os
import secrets
from PIL import Image
from flask import *
from flaskapp import app, db, bcrypt
from flaskapp.forms import RegistrationForm, LoginForm, UpdateAccountForm
from flaskapp.models import User, Doc
from flask_login import login_user, current_user, logout_user, login_required
from flaskapp.service import GeneralQueryService, TranslateService
from datetime import date
from flaskapp.index import INDEX_NAME



@app.route("/home")
def home():
    return render_template('home.html')


# display query page
@app.route("/")
def show_index_page():
    return render_template('index.html')


# display results page for first set of results and "next" sets.
@app.route("/results", methods=['GET'])
def results():
    query_str = request.args.get('query')
    author_str = request.args.get('author')
    min_time_str = request.args.get('mintime')
    max_time_str = request.args.get('maxtime')
    page_num = int(request.args.get('page'))

    query_option = None
    if request.args.get('type') == 'conjunctive':
        query_option = GeneralQueryService.CONJUNCTIVE_OPTION
    elif request.args.get('type') == 'disjunctive':
        query_option = GeneralQueryService.DISJUNCTIVE_OPTION
    else:
        raise RuntimeError("Illegal Request")

    max_date = date.max
    if len(max_time_str) != 0:
        max_date = date.fromisoformat(max_time_str)

    min_date = date.min
    if len(min_time_str) != 0:
        min_date = date.fromisoformat(min_time_str)

    translate_service = TranslateService()
    translated_query_str = translate_service.translate(query_str, TranslateService.CHINESE_OPTION,
                                                       TranslateService.ENGLISH_OPTION)

    query_service = GeneralQueryService(INDEX_NAME)
    result = query_service.query(query_str, author_str, min_date, max_date, query_option, page_num)

    result_dict = result['result_dict']
    stops_words_included = result['stop_words_included']
    synonyms = result['synonyms']
    total_hits = result['total_hits']

    queries = request.args.to_dict()
    queries.pop('page')
    return render_template('result.html', stop_len=len(stops_words_included), stops=stops_words_included,
                           results=result_dict, res_num=total_hits,
                           page_num=page_num, queries=queries, synonyms=synonyms)



# display suggestion for autocompletion
@app.route("/autocomplete", methods=['GET'])
def autocomplete():
    text = request.args.getlist('search[term]')
    general_query_service = GeneralQueryService("sample_covid_19_index").autocomplete(text)
    return jsonify(general_query_service)


# display a particular document given a result number
@app.route("/documents/<res>", methods=['GET'])
def documents(res):
    article_dic, more_like_this_dic = GeneralQueryService("sample_covid_19_index").doc_result(res)
    return render_template('article.html',doc_id=res, article=article_dic, more_like_this=more_like_this_dic)


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)


@app.route("/doc/new/<int:doc_id>", methods=['GET', 'POST'])
@login_required
def new_post(doc_id):
    if Doc.query.filter_by(user_id=current_user.get_id(), doc_id=doc_id).all() != []:
        doc = Doc.query.get_or_404(Doc.query.filter_by(user_id=current_user.get_id(), doc_id=doc_id).first().id)
        db.session.delete(doc)
        db.session.commit()
        flash('Your favorite has been canceled!', 'success')
        return documents(str(doc_id))
    doc = Doc(doc_id=doc_id, author=current_user, user_id=current_user.get_id())
    db.session.add(doc)
    db.session.commit()
    flash('Your favorite has been saved!', 'success')
    return documents(str(doc_id))


@app.route("/my_favorite")
@login_required
def my_doc():
    docs = Doc.query.filter_by(user_id=current_user.get_id()).all()
    return render_template('my_favorite.html', docs=docs)



@app.route("/doc/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(doc_id):
    doc = Doc.query.get_or_404(doc_id)
    if doc.author != current_user:
        abort(403)
    db.session.delete(doc)
    db.session.commit()
    flash('Your favorite has been deleted!', 'success')
    return redirect(url_for('home'))
