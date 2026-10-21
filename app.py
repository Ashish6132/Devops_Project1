from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        return render_template(
            "login.html",
            error="Login database is not configured yet."
        )

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        student_id = request.form.get("student_id", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password", ""
        )

        if password != confirm_password:
            return render_template(
                "register.html",
                error="Passwords do not match!"
            )

        if len(password) < 8:
            return render_template(
                "register.html",
                error="Password must be at least 8 characters."
            )

        return render_template(
            "register.html",
            error="Database is not connected yet."
        )

    return render_template("register.html")


if __name__ == "__main__":
    app.run(debug=True)