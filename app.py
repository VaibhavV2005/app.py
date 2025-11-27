from flask import Flask, render_template_string, request, redirect, session
import sqlite3, os

app = Flask(__name__)
app.secret_key = "secret123"

# ---------- DATABASE SETUP ----------
if not os.path.exists("social.db"):
    conn = sqlite3.connect("social.db")
    c = conn.cursor()
    c.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    c.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER, content TEXT)")
    c.execute("CREATE TABLE comments (id INTEGER PRIMARY KEY, post_id INTEGER, user_id INTEGER, text TEXT)")
    c.execute("CREATE TABLE likes (id INTEGER PRIMARY KEY, post_id INTEGER, user_id INTEGER)")
    conn.commit()
    conn.close()

def db():
    return sqlite3.connect("social.db", check_same_thread=False)

# ---------- HTML TEMPLATE (Single File) ----------
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Mini Social Media</title>
    <style>
        body { font-family: Arial; width: 600px; margin: auto; }
        .post, .comment { border: 1px solid #ddd; padding: 10px; margin: 10px 0; }
        .nav { margin-bottom: 20px; }
        input, textarea { width: 100%; padding: 8px; margin: 8px 0; }
        button { padding: 8px 15px; }
    </style>
</head>
<body>

<div class="nav">
    {% if session.get('user') %}
        Logged in as <b>{{ session['user'] }}</b> |
        <a href="/logout">Logout</a> |
        <a href="/">Home</a> |
        <a href="/post">Create Post</a>
    {% else %}
        <a href="/login">Login</a> |
        <a href="/register">Register</a>
    {% endif %}
</div>

<h2>{{ title }}</h2>

{{ content }}

</body>
</html>
"""

# ---------- ROUTES ----------

@app.route("/")
def home():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT posts.id, users.username, posts.content FROM posts JOIN users ON users.id=posts.user_id ORDER BY posts.id DESC")
    posts = c.fetchall()

    content = ""
    for p in posts:
        post_id, user, text = p

        # likes
        c.execute("SELECT COUNT(*) FROM likes WHERE post_id=?", (post_id,))
        likes = c.fetchone()[0]

        # comments
        c.execute("SELECT users.username, comments.text FROM comments JOIN users ON users.id=comments.user_id WHERE post_id=?", (post_id,))
        comments = c.fetchall()

        content += f"""
        <div class='post'>
            <b>{user}</b><br>{text}<br>
            <a href='/like/{post_id}'>❤️ Like ({likes})</a> |
            <a href='/comment/{post_id}'>💬 Comment</a>
            <div>
        """

        for com_user, com_text in comments:
            content += f"<div class='comment'><b>{com_user}</b>: {com_text}</div>"

        content += "</div></div>"

    return render_template_string(TEMPLATE, title="Social Feed", content=content)

# ---------- REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form["user"]
        pwd = request.form["pwd"]

        conn = db()
        c = conn.cursor()
        c.execute("INSERT INTO users(username, password) VALUES (?,?)", (user, pwd))
        conn.commit()

        return redirect("/login")

    content = """
    <form method="POST">
        <input name="user" placeholder="Username">
        <input name="pwd" type="password" placeholder="Password">
        <button>Register</button>
    </form>
    """
    return render_template_string(TEMPLATE, title="Register", content=content)

# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form["user"]
        pwd = request.form["pwd"]

        conn = db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pwd))
        account = c.fetchone()

        if account:
            session["user"] = user
            session["user_id"] = account[0]
            return redirect("/")
        else:
            return "Invalid login!"

    content = """
    <form method="POST">
        <input name="user" placeholder="Username">
        <input name="pwd" type="password" placeholder="Password">
        <button>Login</button>
    </form>
    """
    return render_template_string(TEMPLATE, title="Login", content=content)

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- CREATE POST ----------
@app.route("/post", methods=["GET", "POST"])
def create_post():
    if not session.get("user"):
        return redirect("/login")

    if request.method == "POST":
        content = request.form["content"]
        conn = db()
        c = conn.cursor()
        c.execute("INSERT INTO posts(user_id, content) VALUES (?,?)", (session["user_id"], content))
        conn.commit()
        return redirect("/")

    content = """
    <form method="POST">
        <textarea name="content" placeholder="Write something..."></textarea>
        <button>Post</button>
    </form>
    """
    return render_template_string(TEMPLATE, title="Create Post", content=content)

# ---------- LIKE ----------
@app.route("/like/<int:id>")
def like(id):
    if not session.get("user"):
        return redirect("/login")

    conn = db()
    c = conn.cursor()

    # avoid duplicate likes
    c.execute("SELECT * FROM likes WHERE post_id=? AND user_id=?", (id, session["user_id"]))
    if not c.fetchone():
        c.execute("INSERT INTO likes(post_id, user_id) VALUES (?,?)", (id, session["user_id"]))
        conn.commit()

    return redirect("/")

# ---------- COMMENT ----------
@app.route("/comment/<int:id>", methods=["GET", "POST"])
def comment(id):
    if request.method == "POST":
        text = request.form["text"]
        conn = db()
        c = conn.cursor()
        c.execute("INSERT INTO comments(post_id, user_id, text) VALUES (?,?,?)", (id, session["user_id"], text))
        conn.commit()
        return redirect("/")

    content = """
    <form method="POST">
        <input name="text" placeholder="Write comment...">
        <button>Comment</button>
    </form>
    """

    return render_template_string(TEMPLATE, title="Comment", content=content)

# ---------- RUN APP ----------
app.run(debug=True)
