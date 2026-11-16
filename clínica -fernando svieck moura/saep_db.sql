
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS usuarios (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT NOT NULL,
    login      TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL            
);

CREATE TABLE IF NOT EXISTS tutores (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    nome     TEXT NOT NULL,
    cpf      TEXT NOT NULL,
    telefone TEXT
);

CREATE TABLE IF NOT EXISTS pets (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    nome     TEXT NOT NULL,
    especie  TEXT NOT NULL,
    tutor_id INTEGER NOT NULL,
    FOREIGN KEY (tutor_id) REFERENCES tutores(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS agendamentos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    data      TEXT NOT NULL,
    descricao TEXT,
    pet_id    INTEGER NOT NULL,
    FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE
);
