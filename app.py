import os
from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index(methods=["GET"]):
    rows = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    held = db.execute("SELECT shares,symbol,original FROM holdings WHERE username = ?", rows[0]["username"])
    use = []
    gain = 0
    print(held)
    for i in range(len(held)):
        if int(held[i]["shares"]) != 0:
            value = int(held[i]["shares"])*float(lookup((held[i])["symbol"])["price"])
            held[i]["value"] = usd(float(lookup((held[i])["symbol"])["price"]))
            held[i]["totalvalue"] = usd(value)
            gain += value
            use.append(held[i])
        else:
            held.pop(i)
    cash = db.execute("select cash from users WHERE username = ?", rows[0]["username"])[0]["cash"]
    print(cash)
    use.append({"total account value": usd(float(cash)+float(gain)), "cash": usd(float(cash))})
    print(use)
    # return 2
    return render_template("holed.html", tabel=use)
    return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        try:
            d = int(request.form.get("shares"))
        except:
            return apology("not an integer amount of shares", 400)
        if not request.form.get("symbol") and lookup(request.form.get("symbol")) != None:
            return apology("must provide symbol or/and not valid symbol", 400)
        elif not request.form.get("shares"):
            return apology("must provide shares", 400)
        elif int(request.form.get("shares")) < 0:
            return apology("negitive shares not allowed", 400)
        elif lookup(request.form.get("symbol")) == None:
            return apology("not valid symbol", 400)
        else:
            rows = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
            print(rows)
            print(type((lookup(request.form.get("symbol"))["price"])))
            # return apology("down in the weeds", 403)
            cash = db.execute("select cash from users WHERE username = ?", rows[0]["username"])[0]["cash"]
            if cash-(int(request.form.get("shares"))*(lookup(request.form.get("symbol"))["price"])) < 0:
                return apology("you do not have enoght cash", 40)
            before = db.execute(" select shares from holdings where username=? and symbol=?",
                                rows[0]["username"], request.form.get("symbol"))
            print(before)
            if before == []:
                db.execute("INSERT INTO holdings (username,shares,symbol,original) VALUES (?,?,?,?)", 
                           rows[0]["username"], int(request.form.get("shares")), request.form.get("symbol"), float(lookup(request.form.get("symbol"))["price"]))
            else:
                db.execute("UPDATE holdings SET shares = ? WHERE username = ? and symbol=?", 
                           before[0]["shares"] + int(request.form.get("shares")), rows[0]["username"], request.form.get("symbol"))
            now = datetime.now()
            db.execute("INSERT INTO trans (username,shares,symbol,type,price,time) VALUES (?,?,?,?,?,?)", 
                       rows[0]["username"], int(request.form.get("shares")), request.form.get("symbol"), "buy", float(lookup(request.form.get("symbol"))["price"]), now)
            # print(cash)
            # print(type(request.form.get("shares")))
            db.execute("UPDATE users SET cash = ? WHERE username = ?", 
                       cash - (int(request.form.get("shares")) * (lookup(request.form.get("symbol"))["price"])), rows[0]["username"])
            return redirect("/")
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    rows = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
    held = db.execute("SELECT shares,symbol,price,type,time FROM trans WHERE username = ?", rows[0]["username"])
    print(held)
    return render_template("history.html", tabel=held)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

         # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

         # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["POST", "GET"])
@login_required
def quote():
    if request.method != "POST":
        return render_template("quote.html")
    print(request.form.get("symbol"))
    if (request.form.get("symbol")):
        if lookup(request.form.get("symbol")) != None:
            print("in - ready to reroute", lookup(request.form.get("symbol")))
            return render_template("quoted.html", result=usd(float(lookup(request.form.get("symbol"))["price"])), sy=lookup(request.form.get("symbol"))["symbol"], name=lookup(request.form.get("symbol"))["name"])
        else:
            return apology("not valid symbol", 400)
    else:
        return apology("no symbol", 400)

        
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if not request.form.get("username"):
            return apology("must provide username", 400)
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("must provide same password", 400)
        elif len(request.form.get("password")) < 3:
            return apology("password too short", 400)
        elif len(rows) == 1:
            return apology("sorry this username is taken", 400)
        else:
            hashed = generate_password_hash(request.form.get("password"), salt_length=len(request.form.get("password")))
            db.execute("INSERT INTO users (username,hash) VALUES (?,?)", request.form.get("username"), hashed)
            return redirect("login")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        if not request.form.get("symbol") and lookup(request.form.get("symbol")) != None:
            return apology("must provide symbol or not valid symbol", 400)
        elif not request.form.get("shares"):
            return apology("must provide shares", 400)
        else:
            rows = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
            held = db.execute("SELECT shares FROM holdings WHERE username = ? and symbol=?", 
                              rows[0]["username"], request.form.get("symbol"))
            if int(held[0]["shares"]) == (int(request.form.get("shares"))):
                db.execute("UPDATE holdings SET shares = 0 WHERE username = ? and symbol=?",
                           rows[0]["username"], request.form.get("symbol"))
                cash = db.execute("select cash from users WHERE username = ?", 
                                  rows[0]["username"])[0]["cash"]
                db.execute("UPDATE users SET cash = ? WHERE username = ?", 
                           cash + (int(request.form.get("shares")) * lookup(request.form.get("symbol"))["price"]), rows[0]["username"])
            elif int(held[0]["shares"]) > (int(request.form.get("shares"))):
                shares = db.execute("select shares from holdings WHERE username = ? and symbol=?", 
                                    rows[0]["username"], request.form.get("symbol"))
                db.execute("UPDATE holdings SET shares = ? WHERE username = ? and symbol=?", 
                           shares[0]["shares"] - int(request.form.get("shares")), rows[0]["username"], request.form.get("symbol"))
                cash = db.execute("select cash from users WHERE username = ?", rows[0]["username"])[0]["cash"]
                db.execute("UPDATE users SET cash = ? WHERE username = ?",
                           (cash + int(request.form.get("shares")) * lookup(request.form.get("symbol"))["price"]), rows[0]["username"])
            else:
                return apology("you do not have this many shares", 400)
            now = datetime.now()
            db.execute("INSERT INTO trans (username,shares,symbol,type,price,time) VALUES (?,?,?,?,?,?)", rows[0]["username"], int(
                request.form.get("shares")), request.form.get("symbol"), "sell", lookup(request.form.get("symbol"))["price"], now)
            return redirect("/")
    else:
        rows = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        held = db.execute("SELECT symbol FROM holdings WHERE username = ?", rows[0]["username"])
        print(held)
        return render_template("sell.html", trav=held)
    return apology("TODO")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
