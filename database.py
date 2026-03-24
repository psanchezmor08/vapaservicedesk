import sqlite3
import bcrypt
from config import DB_PATH


def run_query(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(query, params)
        if query.strip().upper().startswith(("SELECT", "PRAGMA")):
            return c.fetchall()
        else:
            conn.commit()
            return c.lastrowid


def hash_pass(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_pass(password, hashed):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        print(f"Error al verificar contraseña: {e}")
        return False


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS usuarios
            (username TEXT PRIMARY KEY, password TEXT, rol TEXT, estado TEXT,
             email TEXT, debe_cambiar_pass INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS incidencias
            (id INTEGER PRIMARY KEY, titulo TEXT, descripcion TEXT,
             usuario_reporte TEXT, tecnico_asignado TEXT, estado TEXT, fecha TEXT,
             archivo TEXT, informe_tecnico TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS comentarios_incidencia
            (id INTEGER PRIMARY KEY AUTOINCREMENT, incidencia_id INTEGER,
             autor TEXT, fecha TEXT, comentario TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS slas
            (prioridad TEXT PRIMARY KEY, horas INTEGER)''')

        # Migraciones
        c.execute("PRAGMA table_info(incidencias)")
        cols_inc = [col[1] for col in c.fetchall()]
        if 'prioridad'        not in cols_inc: c.execute("ALTER TABLE incidencias ADD COLUMN prioridad TEXT DEFAULT 'Media'")
        if 'categoria'        not in cols_inc: c.execute("ALTER TABLE incidencias ADD COLUMN categoria TEXT DEFAULT 'Otros'")
        if 'fecha_limite'     not in cols_inc: c.execute("ALTER TABLE incidencias ADD COLUMN fecha_limite TEXT")
        if 'fecha_resolucion' not in cols_inc: c.execute("ALTER TABLE incidencias ADD COLUMN fecha_resolucion TEXT")

        c.execute("PRAGMA table_info(usuarios)")
        cols_usr = [col[1] for col in c.fetchall()]
        if 'debe_cambiar_pass' not in cols_usr:
            c.execute("ALTER TABLE usuarios ADD COLUMN debe_cambiar_pass INTEGER DEFAULT 0")

        # Datos iniciales
        c.execute('SELECT count(*) FROM usuarios')
        if c.fetchone()[0] == 0:
            usuarios = [
                ('admin', hash_pass('admin'), 'Administrador', 'Activo', 'admin@empresa.com',     0),
                ('tec1',  hash_pass('tec1'),  'Tecnico',       'Activo', 'tecnico1@ejemplo.com',  0),
                ('tec2',  hash_pass('tec2'),  'Tecnico',       'Activo', 'tecnico2@ejemplo.com',  0),
                ('user1', hash_pass('user1'), 'Usuario',       'Activo', 'user1@ejemplo.com',     0),
            ]
            c.executemany("INSERT INTO usuarios VALUES (?,?,?,?,?,?)", usuarios)

        c.execute('SELECT count(*) FROM slas')
        if c.fetchone()[0] == 0:
            c.executemany("INSERT INTO slas VALUES (?,?)",
                          [('Baja', 120), ('Media', 72), ('Alta', 24), ('Urgente', 4)])
