from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        # Demo only: authentication not configured
        return render_template(
            "login.html",
            error="Login system is not connected yet."
        )

    return render_template("login.html")

if __name__ == "__main__":
    app.run(debug=True)