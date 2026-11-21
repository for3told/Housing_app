from flask import Flask, render_template, request, redirect, url_for, session
import psycopg2
import psycopg2.extras
import re
from werkzeug.security import generate_password_hash, check_password_hash

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

    user_id = session['user_id']
    user_role = session.get('role')

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    # Закрываем просроченные голосования, если такие есть
    cursor.execute("""
        UPDATE polls
        SET is_active = FALSE
        WHERE is_active = TRUE
          AND expires_at IS NOT NULL
          AND expires_at <= CURRENT_TIMESTAMP;
    """)

    # Получаем доступные пользователю голосования
    if user_role in ['admin', 'dispatcher']:
        cursor.execute("""
            SELECT p.*, b.address AS building_address
            FROM polls p
            JOIN buildings b ON p.building_id = b.id
            ORDER BY p.id DESC;
        """)
    else:
        cursor.execute("""
            SELECT p.*, b.address AS building_address
            FROM polls p
            JOIN buildings b ON p.building_id = b.id
            JOIN apartments a ON a.building_id = b.id
            JOIN users u ON u.apartment_id = a.id
            WHERE u.id = %s
            ORDER BY p.id DESC;
        """, (user_id,))
    polls = cursor.fetchall()

    # Получаем входящие запросы на привязку к квартире для текущего собственника
    cursor.execute("""
        SELECT r.id, r.requester_id, r.target_apartment_id, r.requested_owner_status, r.created_at,
               u.last_name, u.first_name, u.middle_name,
               b.address, a.entrance, a.apartment_number
        FROM address_change_requests r
        JOIN users u ON r.requester_id = u.id
        JOIN apartments a ON r.target_apartment_id = a.id
        JOIN buildings b ON a.building_id = b.id
        WHERE r.owner_id = %s AND r.status = 'pending'
        ORDER BY r.created_at DESC;
    """, (user_id,))
    address_requests = cursor.fetchall()

    conn.commit()
    cursor.close()
    conn.close()

    return render_template('index.html', polls=polls, address_requests=address_requests)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        last_name = request.form.get('last_name', '').strip()
        first_name = request.form.get('first_name', '').strip()
        no_middle_name = request.form.get('no_middle_name') == '1'
        raw_middle = request.form.get('middle_name', '')

        if no_middle_name or not raw_middle.strip():
            middle_name = ' '
        else:
            middle_name = raw_middle.strip()

        full_name = " ".join(part for part in [last_name, first_name, middle_name.strip()] if part)

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        apartment_id = request.form.get('apartment_id')
        is_owner_requested = True if request.form.get('is_owner') == 'true' else False
        
        # Бэкенд-валидация сложности пароля
        if len(password) < 6 or not re.search(r'\d', password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            error = "Пароль не соответствует требованиям безопасности (мин. 6 символов, цифры, спецсимволы)."
        else:
            # Проверяем, не занят ли логин
            cursor.execute("SELECT id FROM users WHERE username = %s;", (username,))
            if cursor.fetchone():
                error = "Пользователь с таким логином уже существует!"
            else:
                # Получаем role_id для жильца ('resident')
                cursor.execute("SELECT id FROM roles WHERE role_name = 'resident';")
                role_row = cursor.fetchone()
                role_id = role_row['id'] if role_row else 3
                
                # Хэшируем пароль
                password_hash = generate_password_hash(password)
                
                # Вставляем нового пользователя с учетом статуса собственника
                cursor.execute("""
                    INSERT INTO users (last_name, first_name, middle_name, username, password_hash, apartment_id, role_id, is_owner_requested, is_owner_verified)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, FALSE) RETURNING id;
                """, (last_name, first_name, middle_name, username, password_hash, apartment_id, role_id, is_owner_requested))
                
                new_user_id = cursor.fetchone()[0]
                
                # Записываем событие в аудит
                cursor.execute("""
                    INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
                    VALUES (%s, %s, %s, %s, %s);
                """, (new_user_id, f"{last_name} {first_name}", "REGISTER", "Успешная регистрация нового жильца", request.remote_addr))
                
                conn.commit()
                cursor.close()
                conn.close()
                return redirect(url_for('login'))

    # Получаем список квартир для выпадающего списка (выполняется как при GET, так и если при POST была ошибка)
    cursor.execute("""
        SELECT a.id, b.address, a.entrance, a.apartment_number 
        FROM apartments a
        JOIN buildings b ON a.building_id = b.id
        ORDER BY b.address, a.entrance, a.apartment_number;
    """)
    apartments = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('register.html', apartments=apartments, error=error)


# --- МАРШРУТ ВХОДА ( с проверкой хэша и аудитом) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        # Ищем пользователя и подтягиваем название его роли
        cursor.execute("""
            SELECT U.id, U.last_name, U.first_name, U.middle_name, U.username, U.password_hash, R.role_name
            FROM users U
            JOIN roles R ON U.role_id = R.id
            WHERE U.username = %s;
        """, (username,))
        user = cursor.fetchone()
        
        # Проверяем пароль через check_password_hash
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['full_name'] = f"{user['last_name']} {user['first_name']}"
            session['role'] = user['role_name']
            
            # Пишем лог успешного входа
            cursor.execute("""
                INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
                VALUES (%s, %s, %s, %s, %s);
            """, (user['id'], session['full_name'], "LOGIN", "Успешная авторизация в системе", request.remote_addr))
            conn.commit()
            
            cursor.close()
            conn.close()
            return redirect(url_for('index'))
        else:
            error = 'Неверный логин или пароль!'
            cursor.close()
            conn.close()
            
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/users')
def admin_users():
    if session.get('role') not in ['admin', 'dispatcher']:
        return "Доступ запрещен", 403

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute("""
        SELECT u.id, u.last_name, u.first_name, u.middle_name, u.username,
               u.is_owner_requested, u.is_owner_verified,
               r.role_name, b.address, a.entrance, a.apartment_number
        FROM users u
        JOIN roles r ON u.role_id = r.id
        LEFT JOIN apartments a ON u.apartment_id = a.id
        LEFT JOIN buildings b ON a.building_id = b.id
        ORDER BY u.id;
    """)
    users = cursor.fetchall()

    cursor.execute("SELECT * FROM roles ORDER BY id;")
    roles = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin_users.html', users=users, roles=roles)


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if session.get('role') != 'admin':
        return "Доступ запрещен: удалять пользователей может только администратор.", 403

    if user_id == session.get('user_id'):
        return "Нельзя удалить собственного пользователя во время активной сессии.", 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute("SELECT id, last_name, first_name, middle_name, username FROM users WHERE id = %s;", (user_id,))
    target_user = cursor.fetchone()

    if not target_user:
        cursor.close()
        conn.close()
        return "Пользователь не найден", 404

    deleted_fio = " ".join(
        part for part in [
            target_user['last_name'] or '',
            target_user['first_name'] or '',
            (target_user['middle_name'] or '').strip()
        ] if part
    )

    cursor.execute("DELETE FROM users WHERE id = %s;", (user_id,))

    cursor.execute("""
        INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
        VALUES (%s, %s, %s, %s, %s);
    """, (
        session['user_id'],
        session['full_name'],
        "DELETE_USER",
        f"Удален пользователь {deleted_fio} (логин: {target_user['username']}, ID {user_id})",
        request.remote_addr
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('admin_users'))

@app.route('/admin/users/update_role/<int:user_id>', methods=['POST'])
def update_user_role(user_id):
    if session.get('role') != 'admin':
        return "Доступ запрещен", 403
        
    new_role_id = request.form['role_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role_id = %s WHERE id = %s;", (new_role_id, user_id))
    
    # Пишем в аудит информацию о смене роли
    cursor.execute("""
        INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
        VALUES (%s, %s, %s, %s, %s);
    """, (session['user_id'], session['full_name'], "CHANGE_ROLE", f"Изменена роль для пользователя ID {user_id}", request.remote_addr))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('admin_users'))

# --- ПАНЕЛЬ АДМИНИСТРАТОРА: Просмотр всех квартир ---
@app.route('/admin/apartments')
def admin_apartments():
    if session.get('role') not in ['admin', 'dispatcher']:
        return "Доступ запрещен", 403
        
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Делаем JOIN с buildings, чтобы получить адрес и правильно отсортировать
    cursor.execute("""
        SELECT a.*, b.address 
        FROM apartments a
        JOIN buildings b ON a.building_id = b.id
        ORDER BY b.address, a.entrance, a.apartment_number;
    """)
    apartments = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin_apartments.html', apartments=apartments)

# --- ПАНЕЛЬ АДМИНИСТРАТОРА: Журнал аудита безопасности ---
@app.route('/admin/audit')
def admin_audit():
    if session.get('role') != 'admin':
        return "Доступ запрещен", 403
        
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 100;")
    logs = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin_audit.html', logs=logs)

from datetime import datetime

@app.route('/create_poll', methods=['GET', 'POST'])
def create_poll():
    if session.get('role') not in ['admin', 'dispatcher']:
        return "Доступ запрещен", 403
        
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        building_id = request.form['building_id']
        expires_at = request.form['expires_at']
        is_anonymous = True if request.form.get('is_anonymous') == 'true' else False
        
        options = request.form.getlist('options')
        options = [opt.strip() for opt in options if opt and opt.strip()]
        
        # 1. Создаем голосование
        cursor.execute("""
            INSERT INTO polls (title, description, building_id, created_by, expires_at, is_anonymous, is_active, is_closed) 
            VALUES (%s, %s, %s, %s, %s, %s, TRUE, FALSE) RETURNING id;
        """, (title, description, building_id, session['user_id'], expires_at, is_anonymous))
        poll_id = cursor.fetchone()[0]
        
        # 2. Записываем варианты
        for opt_text in options:
            cursor.execute("INSERT INTO poll_options (poll_id, option_text) VALUES (%s, %s);", (poll_id, opt_text))
            
        # Логируем в аудит
        cursor.execute("""
            INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
            VALUES (%s, %s, %s, %s, %s);
        """, (session['user_id'], session['full_name'], "CREATE_POLL", f"Создано голосование ID {poll_id}", request.remote_addr))
        
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('index'))
        
    cursor.execute("SELECT * FROM buildings ORDER BY address;")
    buildings = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('create_poll.html', buildings=buildings)

@app.route('/poll/action/<int:poll_id>/<action>', methods=['POST'])
def poll_action(poll_id, action):
    if session.get('role') not in ['admin', 'dispatcher']:
        return "Доступ запрещен", 403
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if action == 'close':
        cursor.execute("UPDATE polls SET is_active = FALSE, is_closed = TRUE WHERE id = %s;", (poll_id,))
    elif action == 'delete':
        cursor.execute("DELETE FROM polls WHERE id = %s;", (poll_id,))
        
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/vote/<int:poll_id>', methods=['GET', 'POST'])
def vote(poll_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # 1. Получаем опрос вместе с адресом дома
    cursor.execute("""
        SELECT p.*, b.address as building_address 
        FROM polls p 
        JOIN buildings b ON p.building_id = b.id 
        WHERE p.id = %s;
    """, (poll_id,))
    poll = cursor.fetchone()

    if session.get('role') not in ['admin', 'dispatcher']:
        cursor.execute("""
            SELECT a.building_id 
            FROM users u
            JOIN apartments a ON u.apartment_id = a.id
            WHERE u.id = %s;
        """, (user_id,))
        user_building = cursor.fetchone()
        
        if not user_building or user_building['building_id'] != poll['building_id']:
            cursor.close()
            conn.close()
            return "Доступ запрещен: это голосование относится к другому дому.", 403
        
    if not poll:
        cursor.close()
        conn.close()
        return "Голосование не найдено", 404
        
    # Проверка просрочки на лету
    if poll['is_active'] and poll['expires_at'] < datetime.now():
        cursor.execute("UPDATE polls SET is_active = FALSE WHERE id = %s;", (poll_id,))
        conn.commit()
        poll['is_active'] = False

    # 2. Проверяем, голосовал ли уже пользователь
    cursor.execute("SELECT * FROM votes WHERE poll_id = %s AND user_id = %s;", (poll_id, user_id))
    user_vote = cursor.fetchone()
    has_voted = (user_vote is not None)
    
    error = None
    
    # 3. Обработка отправки голоса
    if request.method == 'POST' and not has_voted and poll['is_active'] and not poll['is_closed']:
        option_id = request.form.get('option_id')
        if option_id:
            try:
                cursor.execute(
                    "INSERT INTO votes (poll_id, user_id, option_id) VALUES (%s, %s, %s);",
                    (poll_id, user_id, option_id)
                )
                conn.commit()
                has_voted = True
                
                # Логируем голос в аудит
                cursor.execute("""
                    INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
                    VALUES (%s, %s, %s, %s, %s);
                """, (user_id, session['full_name'], "VOTE", f"Участие в голосовании ID {poll_id}", request.remote_addr))
                conn.commit()
            except Exception as e:
                conn.rollback()
                error = "Ошибка при фиксации голоса!"
        else:
            error = "Выберите вариант ответа."

    # 4. Подсчет голосов по вариантам
    cursor.execute("""
        SELECT po.id, po.option_text, 
               (SELECT COUNT(*) FROM votes v WHERE v.option_id = po.id) as vote_count
        FROM poll_options po
        WHERE po.poll_id = %s;
    """, (poll_id,))
    options = cursor.fetchall()
    
    # 5. Получение списка проголосовавших (учитывая новую связь через раздельную таблицу apartments)
    voters = []
    if not poll['is_anonymous']:
        cursor.execute("""
            SELECT u.last_name, u.first_name, a.apartment_number, po.option_text
            FROM votes v
            JOIN users u ON v.user_id = u.id
            LEFT JOIN apartments a ON u.apartment_id = a.id
            JOIN poll_options po ON v.option_id = po.id
            WHERE v.poll_id = %s;
        """, (poll_id,))
        voters = cursor.fetchall()

    cursor.close()
    conn.close()
    
    return render_template('vote.html', poll=poll, options=options, voters=voters, has_voted=has_voted, error=error)

@app.route('/polls/delete/<int:poll_id>', methods=['POST'])
def delete_poll(poll_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session.get('role') not in ['admin', 'dispatcher']:
        return "Доступ запрещен: удалять голосования могут только администратор и диспетчер.", 403

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute("""
        SELECT p.id, p.title, p.is_active, p.is_closed, p.expires_at, b.address
        FROM polls p
        LEFT JOIN buildings b ON p.building_id = b.id
        WHERE p.id = %s;
    """, (poll_id,))
    poll = cursor.fetchone()

    if not poll:
        cursor.close()
        conn.close()
        return "Голосование не найдено", 404

    cursor.execute("SELECT CURRENT_TIMESTAMP AS now_ts;")
    now_ts = cursor.fetchone()['now_ts']

    is_finished = (
        not poll['is_active']
        or bool(poll['is_closed'])
        or (poll['expires_at'] is not None and poll['expires_at'] <= now_ts)
    )

    if not is_finished:
        cursor.close()
        conn.close()
        return "Удалить можно только завершенное голосование.", 400

    cursor.execute("DELETE FROM polls WHERE id = %s;", (poll_id,))

    cursor.execute("""
        INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
        VALUES (%s, %s, %s, %s, %s);
    """, (
        session['user_id'],
        session['full_name'],
        "DELETE_POLL",
        f"Удалено завершенное голосование «{poll['title']}» (ID {poll_id}, дом: {poll['address'] or 'не указан'})",
        request.remote_addr
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('index'))

# --- УПРАВЛЕНИЕ ЗДАНИЯМИ И АВТОМАТИЧЕСКАЯ ГЕНЕРАЦИЯ КВАРТИР ---

@app.route('/admin/buildings')
def admin_buildings():
    if session.get('role') not in ['admin', 'dispatcher']:
        return "Доступ запрещен", 403
        
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM buildings ORDER BY address;")
    buildings = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin_buildings.html', buildings=buildings)

@app.route('/admin/buildings/add', methods=['GET', 'POST'])
def add_building():
    if session.get('role') not in ['admin', 'dispatcher']:
        return "Доступ запрещен", 403
        
    error = None
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        address = request.form['address'].strip()
        floors_count = int(request.form['floors_count'])
        entrances_count = int(request.form['entrances_count'])
        
        # Проверяем, включена ли галочка автоматической генерации
        auto_generate = True if request.form.get('auto_generate') == 'true' else False
        
        if auto_generate:
            apartments_count = int(request.form['apartments_count'])
            
            # Считаем сумму квартир по подъездам из формы
            sum_entrance_aps = 0
            entrance_data = []
            for ent in range(1, entrances_count + 1):
                aps = int(request.form.get(f'entrance_aps_{ent}', 0))
                entrance_data.append(aps)
                sum_entrance_aps += aps
                
            # Проверка: сумма должна строго равняться общему числу квартир
            if sum_entrance_aps != apartments_count:
                error = f"Ошибка валидации: Сумма квартир по подъездам ({sum_entrance_aps}) не равна общая сумма ({apartments_count})!"
        else:
            apartments_count = 0 # Без генерации пока 0 квартир (появятся при ручном добавлении)

        if not error:
            try:
                # 1. Создаем здание
                cursor.execute("""
                    INSERT INTO buildings (address, floors_count, entrances_count, apartments_count)
                    VALUES (%s, %s, %s, %s) RETURNING id;
                """, (address, floors_count, entrances_count, apartments_count))
                building_id = cursor.fetchone()[0]
                
                # 2. Если включена генерация — создаем квартиры
                if auto_generate:
                    current_apt_number = 1
                    for ent_idx, aps_in_entrance in enumerate(entrance_data, start=1):
                        aps_per_floor = max(1, aps_in_entrance // floors_count)
                        
                        for apt_index in range(aps_in_entrance):
                            floor = (apt_index // aps_per_floor) + 1
                            if floor > floors_count:
                                floor = floors_count
                            
                            apt_num_str = str(current_apt_number)
                            
                            cursor.execute("""
                                INSERT INTO apartments (building_id, entrance, floor, apartment_number)
                                VALUES (%s, %s, %s, %s);
                            """, (building_id, ent_idx, floor, apt_num_str))
                            
                            current_apt_number += 1
                            
                    # Синхронизируем реальное количество квартир
                    cursor.execute("""
                        UPDATE buildings 
                        SET apartments_count = (SELECT COUNT(*) FROM apartments WHERE building_id = %s)
                        WHERE id = %s;
                    """, (building_id, building_id))

                # Логируем действие в аудит
                cursor.execute("""
                    INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
                    VALUES (%s, %s, %s, %s, %s);
                """, (session['user_id'], session['full_name'], "ADD_BUILDING", f"Добавлен дом '{address}' (генерация квартир: {auto_generate})", request.remote_addr))
                
                conn.commit()
                cursor.close()
                conn.close()
                return redirect(url_for('admin_buildings'))
                
            except Exception as e:
                conn.rollback()
                error = f"Ошибка базы данных: {str(e)}"

    cursor.close()
    conn.close()
    return render_template('add_building.html', error=error)

# --- РЕДАКТИРОВАНИЕ ЗДАНИЯ И ЕГО КВАРТИР ---

@app.route('/admin/buildings/edit/<int:building_id>', methods=['GET', 'POST'])
def edit_building(building_id):
    if session.get('role') not in ['admin', 'dispatcher']:
        return "Доступ запрещен", 403
        
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    error = None
    success = None
    
    if request.method == 'POST':
        address = request.form['address'].strip()
        floors_count = int(request.form['floors_count'])
        entrances_count = int(request.form['entrances_count'])
        
        try:
            cursor.execute("""
                UPDATE buildings 
                SET address = %s, floors_count = %s, entrances_count = %s
                WHERE id = %s;
            """, (address, floors_count, entrances_count, building_id))
            
            # Логируем действие
            cursor.execute("""
                INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
                VALUES (%s, %s, %s, %s, %s);
            """, (session['user_id'], session['full_name'], "EDIT_BUILDING", f"Обновлены данные дома ID {building_id}", request.remote_addr))
            
            conn.commit()
            success = "Данные дома успешно обновлены!"
        except Exception as e:
            conn.rollback()
            error = f"Ошибка при обновлении: {str(e)}"

    # Получаем информацию о здании
    cursor.execute("SELECT * FROM buildings WHERE id = %s;", (building_id,))
    building = cursor.fetchone()
    
    if not building:
        cursor.close()
        conn.close()
        return "Здание не найдено", 404

    # Получаем список всех квартир этого дома, отсортированных по подъездам и этажам
    cursor.execute("""
        SELECT * FROM apartments 
        WHERE building_id = %s 
        ORDER BY entrance, floor, apartment_number;
    """, (building_id,))
    apartments = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('edit_building.html', building=building, apartments=apartments, error=error, success=success)

# Ручное добавление квартиры к дому
@app.route('/admin/apartments/add/<int:building_id>', methods=['POST'])
def add_apartment_manual(building_id):
    if session.get('role') not in ['admin', 'dispatcher']:
        return "Доступ запрещен", 403
        
    entrance = int(request.form['entrance'])
    floor = int(request.form['floor'])
    apartment_number = request.form['apartment_number'].strip()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Добавляем квартиру
        cursor.execute("""
            INSERT INTO apartments (building_id, entrance, floor, apartment_number, resident_count)
            VALUES (%s, %s, %s, %s, 0);
        """, (building_id, entrance, floor, apartment_number))
        
        # Автоматически пересчитываем и обновляем apartments_count в таблице buildings
        cursor.execute("""
            UPDATE buildings 
            SET apartments_count = (SELECT COUNT(*) FROM apartments WHERE building_id = %s)
            WHERE id = %s;
        """, (building_id, building_id))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        
    cursor.close()
    conn.close()
    return redirect(url_for('edit_building', building_id=building_id))

@app.route('/admin/apartments/delete/<int:apartment_id>', methods=['POST'])
def delete_apartment(apartment_id):
    if session.get('role') not in ['admin', 'dispatcher']:
        return "Доступ запрещен", 403
        
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # 1. Получаем квартиру и узнаем ее building_id
    cursor.execute("SELECT * FROM apartments WHERE id = %s;", (apartment_id,))
    apt = cursor.fetchone()
    
    if not apt:
        cursor.close()
        conn.close()
        return "Квартира не найдена", 404
        
    building_id = apt['building_id']
    
    # 2. Проверяем, есть ли жильцы
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE apartment_id = %s;", (apartment_id,))
    users_in_apt = cursor.fetchone()['count']
    
    if apt['resident_count'] > 0 or users_in_apt > 0:
        cursor.close()
        conn.close()
        session['apt_delete_error'] = f"Невозможно удалить кв. {apt['apartment_number']}: в ней зарегистрированы жильцы ({users_in_apt} чел.). Сначала удалите жильцов или смените их адрес!"
        return redirect(url_for('edit_building', building_id=building_id))
        
    # 3. Если жильцов нет — удаляем квартиру
    cursor.execute("DELETE FROM apartments WHERE id = %s;", (apartment_id,))
    
    # Обновляем общее число квартир в здании
    cursor.execute("""
        UPDATE buildings 
        SET apartments_count = (SELECT COUNT(*) FROM apartments WHERE building_id = %s)
        WHERE id = %s;
    """, (building_id, building_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('edit_building', building_id=building_id))
#Профиль
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    error = None
    success = None
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        # 1. Смена адреса / квартиры и статуса собственника
# 1. Смена адреса / квартиры и статуса собственника
        if action == 'update_address':
            new_apartment_id = request.form.get('apartment_id', type=int)
            is_owner_req = True if request.form.get('is_owner') == 'true' else False

            if not new_apartment_id:
                error = "Выберите корректную квартиру из выпадающего списка."
            else:
                cursor.execute("SELECT id FROM apartments WHERE id = %s;", (new_apartment_id,))
                apt_exists = cursor.fetchone()

                if not apt_exists:
                    error = "Выбранная квартира не найдена."
                else:
                    cursor.execute("SELECT apartment_id FROM users WHERE id = %s;", (user_id,))
                    current_apt = cursor.fetchone()['apartment_id']

                    # Ищем подтвержденного собственника целевой квартиры (исключая самого пользователя)
                    cursor.execute("""
                        SELECT id, last_name, first_name, middle_name
                        FROM users
                        WHERE apartment_id = %s
                          AND is_owner_verified = TRUE
                          AND id != %s
                        ORDER BY id ASC
                        LIMIT 1;
                    """, (new_apartment_id, user_id))
                    verified_owner = cursor.fetchone()

                    if verified_owner and current_apt != new_apartment_id:
                        # Проверяем, нет ли уже активного ожидающего запроса на эту квартиру от этого пользователя
                        cursor.execute("""
                            SELECT id FROM address_change_requests
                            WHERE requester_id = %s
                              AND target_apartment_id = %s
                              AND status = 'pending';
                        """, (user_id, new_apartment_id))
                        existing_req = cursor.fetchone()

                        if existing_req:
                            success = "Запрос на смену адреса уже отправлен собственнику квартиры и ожидает ответа."
                        else:
                            cursor.execute("""
                                INSERT INTO address_change_requests
                                    (requester_id, owner_id, target_apartment_id, requested_owner_status, status)
                                VALUES (%s, %s, %s, %s, 'pending');
                            """, (user_id, verified_owner['id'], new_apartment_id, is_owner_req))

                            cursor.execute("""
                                INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
                                VALUES (%s, %s, %s, %s, %s);
                            """, (
                                user_id,
                                session['full_name'],
                                "REQUEST_ADDRESS_CHANGE",
                                f"Запрошена смена адреса на квартиру ID {new_apartment_id} (ожидает подтверждения собственника ID {verified_owner['id']})",
                                request.remote_addr
                            ))
                            conn.commit()
                            success = "У этой квартиры есть подтверждённый собственник. Запрос отправлен ему — адрес изменится после его подтверждения."
                    else:
                        # Собственника нет (или квартира та же) — обновляем адрес напрямую
                        if current_apt != new_apartment_id:
                            cursor.execute("""
                                UPDATE users
                                SET apartment_id = %s, is_owner_requested = %s, is_owner_verified = FALSE
                                WHERE id = %s;
                            """, (new_apartment_id, is_owner_req, user_id))
                        else:
                            cursor.execute("""
                                UPDATE users
                                SET is_owner_requested = %s
                                WHERE id = %s;
                            """, (is_owner_req, user_id))

                        cursor.execute("""
                            INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
                            VALUES (%s, %s, %s, %s, %s);
                        """, (user_id, session['full_name'], "UPDATE_PROFILE", "Обновлен адрес проживания / статус владельца", request.remote_addr))

                        conn.commit()
                        success = "Данные об адресе успешно обновлены!"
                
        # 2. Смена пароля
        elif action == 'change_password':
            old_password = request.form['old_password']
            new_password = request.form['new_password']
            
            cursor.execute("SELECT password_hash FROM users WHERE id = %s;", (user_id,))
            user_row = cursor.fetchone()
            
            if not check_password_hash(user_row['password_hash'], old_password):
                error = "Текущий пароль введен неверно!"
            elif len(new_password) < 6 or not re.search(r'\d', new_password) or not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
                error = "Новый пароль должен содержать минимум 6 символов, цифры и спецсимволы."
            else:
                new_hash = generate_password_hash(new_password)
                cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s;", (new_hash, user_id))
                
                cursor.execute("""
                    INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
                    VALUES (%s, %s, %s, %s, %s);
                """, (user_id, session['full_name'], "CHANGE_PASSWORD", "Пользователь сменил пароль в профиле", request.remote_addr))
                
                conn.commit()
                success = "Пароль успешно изменен!"

    # Получаем актуальные данные пользователя для отображения
    cursor.execute("""
        SELECT u.*, r.role_name, b.address, a.entrance, a.apartment_number
        FROM users u
        JOIN roles r ON u.role_id = r.id
        LEFT JOIN apartments a ON u.apartment_id = a.id
        LEFT JOIN buildings b ON a.building_id = b.id
        WHERE u.id = %s;
    """, (user_id,))
    user = cursor.fetchone()
    
    # Список квартир для формы смены адреса
    cursor.execute("""
        SELECT a.id, b.address, a.entrance, a.apartment_number 
        FROM apartments a
        JOIN buildings b ON a.building_id = b.id
        ORDER BY b.address, a.entrance, a.apartment_number;
    """)
    apartments = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('profile.html', user=user, apartments=apartments, error=error, success=success)


# --- МОДУЛЬ ЧАТА (ОБЩЕДОМОВЫЕ И ЛИЧНЫЕ СООБЩЕНИЯ) ---

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    user_role = session.get('role')
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # 1. Получаем доступные пользователю общедомовые чаты
    if user_role in ['admin', 'dispatcher']:
        # Сотрудники УК видят чаты всех домов
        cursor.execute("SELECT id, address FROM buildings ORDER BY address;")
        available_buildings = cursor.fetchall()
    else:
        # Жилец видит только чат своего дома
        cursor.execute("""
            SELECT b.id, b.address 
            FROM users u
            JOIN apartments a ON u.apartment_id = a.id
            JOIN buildings b ON a.building_id = b.id
            WHERE u.id = %s;
        """, (user_id,))
        available_buildings = cursor.fetchall()

    # 2. Получаем список всех пользователей для личных сообщений (кроме самого себя)
    cursor.execute("""
        SELECT u.id, u.last_name, u.first_name, r.role_name, b.address, a.apartment_number
        FROM users u
        JOIN roles r ON u.role_id = r.id
        LEFT JOIN apartments a ON u.apartment_id = a.id
        LEFT JOIN buildings b ON a.building_id = b.id
        WHERE u.id != %s
        ORDER BY r.id, u.last_name, u.first_name;
    """, (user_id,))
    all_users = cursor.fetchall()

    # 3. Определяем, какой чат сейчас открыт (дом или личка)
    selected_building_id = request.args.get('building_id', type=int)
    selected_user_id = request.args.get('user_id', type=int)
    
    # Если ничего не выбрано, открываем первый доступный домовой чат (если есть)
    if not selected_building_id and not selected_user_id and available_buildings:
        selected_building_id = available_buildings[0]['id']

    messages = []
    chat_title = "Выберите чат из списка слева"
    chat_type = None
    target_id = None

    # Загружаем историю общедомового чата
    if selected_building_id:
        # Проверяем, имеет ли жилец доступ к этому дому
        allowed_ids = [b['id'] for b in available_buildings]
        if selected_building_id not in allowed_ids:
            cursor.close()
            conn.close()
            return "Доступ к чату этого дома запрещен", 403
            
        chat_type = 'building'
        target_id = selected_building_id
        
        cursor.execute("SELECT address FROM buildings WHERE id = %s;", (selected_building_id,))
        b_row = cursor.fetchone()
        chat_title = f"🏢 Общий чат дома: {b_row['address']}" if b_row else "Чат дома"
        
        cursor.execute("""
            SELECT m.*, u.last_name, u.first_name, r.role_name, a.apartment_number
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            JOIN roles r ON u.role_id = r.id
            LEFT JOIN apartments a ON u.apartment_id = a.id
            WHERE m.building_id = %s
            ORDER BY m.created_at ASC;
        """, (selected_building_id,))
        messages = cursor.fetchall()

    # Загружаем историю личной переписки
    elif selected_user_id:
        chat_type = 'direct'
        target_id = selected_user_id
        
        cursor.execute("""
            SELECT u.last_name, u.first_name, r.role_name, b.address, a.apartment_number
            FROM users u
            JOIN roles r ON u.role_id = r.id
            LEFT JOIN apartments a ON u.apartment_id = a.id
            LEFT JOIN buildings b ON a.building_id = b.id
            WHERE u.id = %s;
        """, (selected_user_id,))
        u_row = cursor.fetchone()
        
        if not u_row:
            cursor.close()
            conn.close()
            return "Пользователь не найден", 404
            
        info = f" ({u_row['address']}, кв. {u_row['apartment_number']})" if u_row['address'] else " (Сотрудник УК)"
        chat_title = f"💬 Диалог: {u_row['last_name']} {u_row['first_name']}{info}"
        
        cursor.execute("""
            SELECT m.*, u.last_name, u.first_name, r.role_name, a.apartment_number
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            JOIN roles r ON u.role_id = r.id
            LEFT JOIN apartments a ON u.apartment_id = a.id
            WHERE (m.sender_id = %s AND m.recipient_id = %s)
               OR (m.sender_id = %s AND m.recipient_id = %s)
            ORDER BY m.created_at ASC;
        """, (user_id, selected_user_id, selected_user_id, user_id))
        messages = cursor.fetchall()

    cursor.close()
    conn.close()
    
    return render_template('chat.html', 
                           available_buildings=available_buildings,
                           all_users=all_users,
                           messages=messages,
                           chat_title=chat_title,
                           chat_type=chat_type,
                           target_id=target_id)


@app.route('/chat/send', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    user_role = session.get('role')
    chat_type = request.form.get('chat_type')
    target_id = request.form.get('target_id', type=int)
    content = request.form.get('content', '').strip()
    
    if not content or not target_id or chat_type not in ['building', 'direct']:
        return redirect(url_for('chat'))
        
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if chat_type == 'building':
        # Проверка прав на отправку в чат дома
        if user_role not in ['admin', 'dispatcher']:
            cursor.execute("""
                SELECT a.building_id FROM users u
                JOIN apartments a ON u.apartment_id = a.id
                WHERE u.id = %s;
            """, (user_id,))
            row = cursor.fetchone()
            if not row or row['building_id'] != target_id:
                cursor.close()
                conn.close()
                return "Доступ запрещен", 403
                
        cursor.execute("""
            INSERT INTO messages (sender_id, building_id, content)
            VALUES (%s, %s, %s);
        """, (user_id, target_id, content))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('chat', building_id=target_id))
        
    else: # direct
        cursor.execute("""
            INSERT INTO messages (sender_id, recipient_id, content)
            VALUES (%s, %s, %s);
        """, (user_id, target_id, content))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('chat', user_id=target_id))


@app.route('/chat/edit/<int:message_id>', methods=['POST'])
def edit_message(message_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    new_content = request.form.get('content', '').strip()
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cursor.execute("SELECT * FROM messages WHERE id = %s;", (message_id,))
    msg = cursor.fetchone()
    
    if not msg:
        cursor.close()
        conn.close()
        return "Сообщение не найдено", 404
        
    # Редактировать может ТОЛЬКО автор сообщения
    if msg['sender_id'] != user_id:
        cursor.close()
        conn.close()
        return "Доступ запрещен: вы можете редактировать только свои сообщения.", 403
        
    if new_content and new_content != msg['content']:
        cursor.execute("""
            UPDATE messages 
            SET content = %s, is_edited = TRUE 
            WHERE id = %s;
        """, (new_content, message_id))
        conn.commit()
        
    cursor.close()
    conn.close()
    
    if msg['building_id']:
        return redirect(url_for('chat', building_id=msg['building_id']))
    else:
        other_user = msg['recipient_id']
        return redirect(url_for('chat', user_id=other_user))


@app.route('/chat/delete/<int:message_id>', methods=['POST'])
def delete_message(message_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    user_role = session.get('role')
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    cursor.execute("SELECT * FROM messages WHERE id = %s;", (message_id,))
    msg = cursor.fetchone()
    
    if not msg:
        cursor.close()
        conn.close()
        return "Сообщение не найдено", 404
        
    # Проверка прав на удаление
    can_delete = False
    if msg['sender_id'] == user_id:
        can_delete = True
    elif msg['building_id'] is not None and user_role in ['admin', 'dispatcher']:
        # В общедомовом чате админ и диспетчер могут удалять любые сообщения
        can_delete = True
        
    if not can_delete:
        cursor.close()
        conn.close()
        return "Доступ запрещен: недостаточно прав для удаления сообщения.", 403
        
    cursor.execute("DELETE FROM messages WHERE id = %s;", (message_id,))
    
    # Если модератор удалил чужое сообщение в общем чате — фиксируем в аудит
    if msg['sender_id'] != user_id:
        cursor.execute("""
            INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
            VALUES (%s, %s, %s, %s, %s);
        """, (user_id, session['full_name'], "DELETE_MESSAGE", f"Удалено сообщение ID {message_id} в чате дома ID {msg['building_id']}", request.remote_addr))
        
    conn.commit()
    cursor.close()
    conn.close()
    
    if msg['building_id']:
        return redirect(url_for('chat', building_id=msg['building_id']))
    else:
        other_user = msg['recipient_id'] if msg['sender_id'] == user_id else msg['sender_id']
        return redirect(url_for('chat', user_id=other_user))

@app.route('/admin/users/owner/<int:user_id>/<decision>', methods=['POST'])
def process_owner_request(user_id, decision):
    if session.get('role') not in ['admin', 'dispatcher']:
        return "Доступ запрещен", 403

    if decision not in ['approve', 'reject']:
        return "Некорректное действие", 400

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute("""
        SELECT u.id, u.last_name, u.first_name, u.middle_name, u.is_owner_requested,
               b.address, a.apartment_number
        FROM users u
        LEFT JOIN apartments a ON u.apartment_id = a.id
        LEFT JOIN buildings b ON a.building_id = b.id
        WHERE u.id = %s;
    """, (user_id,))
    target_user = cursor.fetchone()

    if not target_user:
        cursor.close()
        conn.close()
        return "Пользователь не найден", 404

    target_fio = " ".join(
        part for part in [
            target_user['last_name'] or '',
            target_user['first_name'] or '',
            (target_user['middle_name'] or '').strip()
        ] if part
    )
    apt_info = f"{target_user['address']}, кв. {target_user['apartment_number']}" if target_user['address'] else "без адреса"

    if decision == 'approve':
        cursor.execute("""
            UPDATE users
            SET is_owner_verified = TRUE, is_owner_requested = FALSE
            WHERE id = %s;
        """, (user_id,))
        action_type = "OWNER_REQUEST_APPROVED"
        description = f"Одобрена заявка на статус собственника для {target_fio} (ID {user_id}, {apt_info})"
    else:
        cursor.execute("""
            UPDATE users
            SET is_owner_verified = FALSE, is_owner_requested = FALSE
            WHERE id = %s;
        """, (user_id,))
        action_type = "OWNER_REQUEST_REJECTED"
        description = f"Отклонена заявка на статус собственника для {target_fio} (ID {user_id}, {apt_info})"

    cursor.execute("""
        INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
        VALUES (%s, %s, %s, %s, %s);
    """, (session['user_id'], session['full_name'], action_type, description, request.remote_addr))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('admin_users'))

@app.route('/address_request/<int:req_id>/<decision>', methods=['POST'])
def resolve_address_request(req_id, decision):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if decision not in ['approve', 'reject']:
        return "Некорректное действие", 400

    owner_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute("""
        SELECT r.*, b.address, a.entrance, a.apartment_number
        FROM address_change_requests r
        JOIN apartments a ON r.target_apartment_id = a.id
        JOIN buildings b ON a.building_id = b.id
        WHERE r.id = %s AND r.owner_id = %s AND r.status = 'pending';
    """, (req_id, owner_id))
    req_row = cursor.fetchone()

    if not req_row:
        cursor.close()
        conn.close()
        return "Запрос не найден или уже обработан", 404

    apt_label = f"{req_row['address']}, под. {req_row['entrance']}, кв. {req_row['apartment_number']}"

    if decision == 'approve':
        # Меняем адрес заявителю на квартиру собственника; статус собственника автоматически не выдаём
        cursor.execute("""
            UPDATE users
            SET apartment_id = %s,
                is_owner_verified = FALSE,
                is_owner_requested = %s
            WHERE id = %s;
        """, (req_row['target_apartment_id'], bool(req_row['requested_owner_status']), req_row['requester_id']))

        cursor.execute("""
            UPDATE address_change_requests
            SET status = 'approved', resolved_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        """, (req_id,))

        cursor.execute("""
            INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
            VALUES (%s, %s, %s, %s, %s);
        """, (
            owner_id,
            session['full_name'],
            "ADDRESS_REQUEST_APPROVED",
            f"Собственник одобрил смену адреса пользователя ID {req_row['requester_id']} на ({apt_label})",
            request.remote_addr
        ))
    else:
        cursor.execute("""
            UPDATE address_change_requests
            SET status = 'rejected', resolved_at = CURRENT_TIMESTAMP
            WHERE id = %s;
        """, (req_id,))

        cursor.execute("""
            INSERT INTO audit_logs (user_id, user_name_snapshot, action_type, description, ip_address)
            VALUES (%s, %s, %s, %s, %s);
        """, (
            owner_id,
            session['full_name'],
            "ADDRESS_REQUEST_REJECTED",
            f"Собственник отклонил смену адреса пользователя ID {req_row['requester_id']} на ({apt_label})",
            request.remote_addr
        ))

    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)