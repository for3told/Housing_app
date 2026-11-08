from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
import psycopg2.extras

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_cursach'

DB_HOST = "localhost"
DB_NAME = "housing_db"
DB_USER = "postgres"
DB_PASSWORD = "root" 

def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Получаем список активных голосований
    cursor.execute("SELECT * FROM polls WHERE is_active = TRUE ORDER BY id DESC;")
    polls = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('index.html', polls=polls)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['full_name'] = f"{user['last_name']} {user['first_name']} {user['middle_name'] or ''}".strip()
            session['role'] = user['role']
            session['apartment'] = user['apartment']
            session['entrance'] = user['entrance']
            return redirect(url_for('index'))
        else:
            error = 'Неверный логин или пароль!'
            
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/create_poll', methods=['GET', 'POST'])
def create_poll():
    # Проверяем, что зашел именно администратор
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        
        # Собираем варианты ответов, которые заполнил админ
        options = [
            request.form.get('option1'),
            request.form.get('option2'),
            request.form.get('option3')
        ]
        # Убираем пустые варианты, если вдруг какие-то не заполнили
        options = [opt.strip() for opt in options if opt and opt.strip()]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Создаем само голосование и получаем его ID
        cursor.execute(
            "INSERT INTO polls (title, description, is_active) VALUES (%s, %s, TRUE) RETURNING id;",
            (title, description)
        )
        poll_id = cursor.fetchone()[0]
        
        # 2. Записываем варианты ответов для этого голосования
        for opt_text in options:
            cursor.execute(
                "INSERT INTO poll_options (poll_id, option_text) VALUES (%s, %s);",
                (poll_id, opt_text)
            )
            
        conn.commit()
        cursor.close()
        conn.close()
        
        return redirect(url_for('index'))
        
    return render_template('create_poll.html')

@app.route('/vote/<int:poll_id>', methods=['GET', 'POST'])
def vote(poll_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # 1. Получаем информацию о самом голосовании
    cursor.execute("SELECT * FROM polls WHERE id = %s;", (poll_id,))
    poll = cursor.fetchone()
    
    if not poll:
        cursor.close()
        conn.close()
        return "Голосование не найдено", 404
        
    # 2. Проверяем, голосовал ли уже этот пользователь в данном опросе
    cursor.execute("SELECT * FROM votes WHERE poll_id = %s AND user_id = %s;", (poll_id, user_id))
    user_vote = cursor.fetchone()
    has_voted = (user_vote is not None)
    
    error = None
    
    # 3. Если пользователь отправил голос (метод POST)
    if request.method == 'POST' and not has_voted:
        option_id = request.form.get('option_id')
        if option_id:
            try:
                # Записываем голос в базу
                cursor.execute(
                    "INSERT INTO votes (poll_id, user_id, option_id) VALUES (%s, %s, %s);",
                    (poll_id, user_id, option_id)
                )
                conn.commit()
                has_voted = True
            except Exception as e:
                conn.rollback()
                error = "Произошла ошибка или вы уже проголосовали!"
        else:
            error = "Пожалуйста, выберите вариант ответа."

    # 4. Получаем варианты ответов и подсчитываем количество голосов для каждого
    cursor.execute("""
        SELECT po.id, po.option_text, 
               (SELECT COUNT(*) FROM votes v WHERE v.option_id = po.id) as vote_count
        FROM poll_options po
        WHERE po.poll_id = %s;
    """, (poll_id,))
    options = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('vote.html', poll=poll, options=options, has_voted=has_voted, error=error)

if __name__ == '__main__':
    app.run(debug=True)