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
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Автоматическое закрытие просроченных голосований
    cursor.execute("""
        UPDATE polls 
        SET is_active = FALSE 
        WHERE is_active = TRUE AND expires_at < CURRENT_TIMESTAMP;
    """)
    conn.commit()
    
    user_role = session.get('role')
    user_id = session['user_id']
    polls = []
    
    if user_role in ['admin', 'dispatcher']:
        cursor.execute("""
            SELECT p.*, b.address as building_address 
            FROM polls p 
            JOIN buildings b ON p.building_id = b.id 
            ORDER BY p.id DESC;
        """)
        polls = cursor.fetchall()
    else:
        # Безопасно проверяем, привязана ли вообще квартира к пользователю
        cursor.execute("""
            SELECT a.building_id 
            FROM users u
            JOIN apartments a ON u.apartment_id = a.id
            WHERE u.id = %s;
        """, (user_id,))
        user_building = cursor.fetchone()
        
        # Проверяем не просто наличие объекта, а то, что он содержит building_id
        if user_building and user_building['building_id']:
            cursor.execute("""
                SELECT p.*, b.address as building_address 
                FROM polls p 
                JOIN buildings b ON p.building_id = b.id 
                WHERE p.building_id = %s AND p.is_active = TRUE AND p.is_closed = FALSE
                ORDER BY p.id DESC;
            """, (user_building['building_id'],))
            polls = cursor.fetchall()
            
    cursor.close()
    conn.close()
    return render_template('index.html', polls=polls)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if request.method == 'POST':
        last_name = request.form['last_name'].strip()
        first_name = request.form['first_name'].strip()
        middle_name = request.form.get('middle_name', '').strip()
        username = request.form['username'].strip()
        password = request.form['password']
        apartment_id = request.form['apartment_id']
        
        # Получаем статус чекбокса "Я собственник" (True, если отмечен, иначе False)
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
    if session.get('role') != 'admin':
        return "Доступ запрещен", 403
        
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Делаем JOIN с таблицей buildings через apartments, чтобы получить address
    cursor.execute("""
        SELECT u.id, u.last_name, u.first_name, u.middle_name, u.username, 
               r.role_name, b.address, a.entrance, a.apartment_number
        FROM users u
        JOIN roles r ON u.role_id = r.id
        LEFT JOIN apartments a ON u.apartment_id = a.id
        LEFT JOIN buildings b ON a.building_id = b.id
        ORDER BY u.id;
    """)
    users = cursor.fetchall()
    
    # Получаем список всех ролей для выпадающего списка
    cursor.execute("SELECT * FROM roles;")
    roles = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin_users.html', users=users, roles=roles)

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
        if action == 'update_address':
            new_apartment_id = request.form.get('apartment_id')
            is_owner_req = True if request.form.get('is_owner') == 'true' else False
            
            if not new_apartment_id:
                error = "Выберите корректную квартиру из выпадающего списка."
            else:
                cursor.execute("SELECT apartment_id FROM users WHERE id = %s;", (user_id,))
                current_apt = cursor.fetchone()['apartment_id']
                
                # Если квартира изменилась, сбрасываем подтверждение владельца
                if str(current_apt) != str(new_apartment_id):
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

if __name__ == '__main__':
    app.run(debug=True)