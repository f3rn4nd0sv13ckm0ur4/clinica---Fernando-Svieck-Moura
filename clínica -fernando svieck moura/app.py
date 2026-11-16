import os, re, sqlite3
from datetime import timedelta
from functools import wraps
from flask import Flask, request, redirect, session, render_template, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "clinica.db")
KEYFILE = os.path.join(BASE, "chave.key")
if not os.path.exists(KEYFILE):
    with open(KEYFILE, "wb") as f:
        f.write(Fernet.generate_key())
fernet = Fernet(open(KEYFILE, "rb").read())

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
app.permanent_session_lifetime = timedelta(minutes=30)  # expiração da sessão

enc = lambda s: fernet.encrypt(s.encode()).decode()
dec = lambda s: fernet.decrypt(s.encode()).decode()

# ---------- banco ----------
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d: d.close()

def init_db():
    con = sqlite3.connect(DB)
    con.executescript(open(os.path.join(BASE, "schema.sql"), encoding="utf-8").read())
    if con.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
        for n, l, s in [("Administrador", "admin", "admin123"), ("Dra. Ana", "ana", "ana123"), ("Dr. Beto", "beto", "beto123")]:
            con.execute("INSERT INTO usuarios(nome,login,senha_hash) VALUES(?,?,?)", (n, l, generate_password_hash(s)))
        for n, c, t in [("Maria Silva", "52998224725", "41999990001"), ("João Souza", "11144477735", "41999990002"), ("Carla Lima", "39053344705", "41999990003")]:
            con.execute("INSERT INTO tutores(nome,cpf,telefone) VALUES(?,?,?)", (n, enc(c), t))
        for n, e, t in [("Rex", "Cachorro", 1), ("Mimi", "Gato", 2), ("Thor", "Cachorro", 3)]:
            con.execute("INSERT INTO pets(nome,especie,tutor_id) VALUES(?,?,?)", (n, e, t))
        for d, desc, p in [("2026-11-20T09:00", "Consulta", 1), ("2026-11-18T14:30", "Vacina", 2), ("2026-11-25T10:00", "Retorno", 3)]:
            con.execute("INSERT INTO agendamentos(data,descricao,pet_id) VALUES(?,?,?)", (d, desc, p))
    con.commit(); con.close()

# ---------- páginas ----------
def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if "uid" not in session:
            return redirect("/login")
        return f(*a, **k)
    return w

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = db().execute("SELECT * FROM usuarios WHERE login=?", (request.form["login"].strip(),)).fetchone()
        if u and check_password_hash(u["senha_hash"], request.form["senha"]):
            session.clear(); session.permanent = True
            session["uid"], session["nome"] = u["id"], u["nome"]
            return redirect("/")
        flash("Usuário ou senha inválidos.", "err")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); return redirect("/login")

@app.route("/")
@login_required
def home():
    return render_template("home.html")

# ---------- tutores ----------
def valida_cpf(c):
    return bool(re.fullmatch(r"\d{11}", c)) and len(set(c)) > 1
@app.route("/tutores", methods=["GET", "POST"])
@login_required
def tutores():
    con = db()
    if request.method == "POST":
        nome, tel = request.form["nome"].strip(), request.form["telefone"].strip()
        cpf = re.sub(r"\D", "", request.form["cpf"])
        if not nome or not valida_cpf(cpf):
            flash("Informe nome e um CPF válido (11 números).", "err")
            return redirect("/tutores")
        if any(dec(r["cpf"]) == cpf for r in con.execute("SELECT cpf FROM tutores")):
            flash("CPF já cadastrado.", "err")
            return redirect("/tutores")
        con.execute("INSERT INTO tutores(nome,cpf,telefone) VALUES(?,?,?)", (nome, enc(cpf), tel)); con.commit()
        flash("Tutor cadastrado com sucesso!", "msg")
        return redirect("/tutores?q=" + cpf)  # mostra a listagem filtrada pelo termo inserido
    q = request.args.get("q", "").strip().lower()
    lista = []
    for r in con.execute("SELECT * FROM tutores ORDER BY nome"):
        cpf = dec(r["cpf"])
        if not q or q in r["nome"].lower() or q in cpf or q in (r["telefone"] or ""):
            lista.append({"id": r["id"], "nome": r["nome"], "cpf": cpf, "telefone": r["telefone"]})
    return render_template("tutores.html", lista=lista, q=request.args.get("q", ""))
@app.route("/tutores/<int:i>/editar", methods=["GET", "POST"])
@login_required
def editar_tutor(i):
    con = db()
    t = con.execute("SELECT * FROM tutores WHERE id=?", (i,)).fetchone()
    if not t: return redirect("/tutores")
    if request.method == "POST":
        cpf = re.sub(r"\D", "", request.form["cpf"])
        if not request.form["nome"].strip() or not valida_cpf(cpf):
            flash("Informe nome e um CPF válido.", "err"); return redirect(f"/tutores/{i}/editar")
        if any(dec(r["cpf"]) == cpf for r in con.execute("SELECT cpf FROM tutores WHERE id<>?", (i,))):
            flash("CPF já cadastrado em outro tutor.", "err"); return redirect(f"/tutores/{i}/editar")
        con.execute("UPDATE tutores SET nome=?,cpf=?,telefone=? WHERE id=?",
                    (request.form["nome"].strip(), enc(cpf), request.form["telefone"].strip(), i)); con.commit()
        flash("Tutor atualizado com sucesso!", "msg")
        return redirect("/tutores?q=" + cpf)
    return render_template("editar_tutor.html",
                t=t, cpf=dec(t["cpf"]))
@app.route("/tutores/<int:i>/excluir", methods=["POST"])
@login_required
def excluir_tutor(i):
    db().execute("DELETE FROM tutores WHERE id=?", (i,)); db().commit()
    flash("Tutor excluído.", "msg"); return redirect("/tutores")

# ---------- pets ----------
@app.route("/pets", methods=["GET", "POST"])
@login_required
def pets():
    con = db()
    if request.method == "POST":
        if request.form["nome"].strip():
            con.execute("INSERT INTO pets(nome,especie,tutor_id) VALUES(?,?,?)",
                        (request.form["nome"].strip(), request.form["especie"].strip() or "Outro", request.form["tutor_id"])); con.commit()
            flash("Pet cadastrado!", "msg")
        return redirect("/pets")
    return render_template("pets.html",
                tutores=con.execute("SELECT id,nome FROM tutores ORDER BY nome").fetchall(),
                pets=con.execute("SELECT p.*, t.nome AS tutor FROM pets p JOIN tutores t ON t.id=p.tutor_id ORDER BY p.nome").fetchall())

@app.route("/pets/<int:i>/excluir", methods=["POST"])
@login_required
def excluir_pet(i):
    db().execute("DELETE FROM pets WHERE id=?", (i,)); db().commit(); return redirect("/pets")

# ---------- agendamentos ----------
@app.route("/agendamentos", methods=["GET", "POST"])
@login_required
def agendamentos():
    con = db()
    if request.method == "POST":
        con.execute("INSERT INTO agendamentos(data,descricao,pet_id) VALUES(?,?,?)",
                    (request.form["data"], request.form["descricao"].strip(), request.form["pet_id"])); con.commit()
        flash("Agendamento cadastrado!", "msg"); return redirect("/agendamentos")
    return render_template("agendamentos.html",
                pets=con.execute("SELECT p.id,p.nome,t.nome AS tutor FROM pets p JOIN tutores t ON t.id=p.tutor_id ORDER BY p.nome").fetchall(),
                ags=con.execute("""SELECT a.*, p.nome AS pet, t.nome AS tutor, t.telefone FROM agendamentos a
                    JOIN pets p ON p.id=a.pet_id JOIN tutores t ON t.id=p.tutor_id ORDER BY a.data""").fetchall())

@app.route("/agendamentos/<int:i>/editar", methods=["POST"])
@login_required
def editar_ag(i):
    db().execute("UPDATE agendamentos SET data=? WHERE id=?", (request.form["data"], i)); db().commit()
    flash("Data atualizada!", "msg"); return redirect("/agendamentos")

@app.route("/agendamentos/<int:i>/excluir", methods=["POST"])
@login_required
def excluir_ag(i):
    db().execute("DELETE FROM agendamentos WHERE id=?", (i,)); db().commit(); return redirect("/agendamentos")

if __name__ == "__main__":
    init_db()
    app.run(debug=False)
