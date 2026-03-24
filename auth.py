from database import run_query, check_pass


def login(username, password):
    """
    Autenticación local contra la base de datos SQLite con bcrypt.
    Devuelve (rol, debe_cambiar_pass) o (None, None) si falla.
    """
    result = run_query(
        "SELECT password, rol, debe_cambiar_pass FROM usuarios WHERE username = ?",
        (username,)
    )
    if result:
        db_hash, rol, debe_cambiar = result[0]
        if check_pass(password, db_hash):
            return (rol, debe_cambiar)
    return (None, None)
