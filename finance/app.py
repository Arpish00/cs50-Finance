import os
#export API_KEY=pk_01d917ba3d20450481b1927b2a60b50a

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]

    if not user_id:
        return render_template("login.html")

    stocks = db.execute("SELECT symbol, name , price, sum(shares) as totalshares FROM transactions WHERE user_id = ?", user_id)
    cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

    total = cash

    for stock in stocks:
        total += stock['price'] * stock['totalshares']

    return render_template("index.html", stocks = stocks, cash = cash, usd=usd)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        symbol = request.form.get("symbol").upper()
        item = lookup(symbol)

        if not symbol:
            return apology("enter a symbol")
        elif not item:
            return apology("cannot find a match")
        shares_count = request.form.get("shares")
        shares = int((shares_count))

        if shares <= 0:
            return apology("shares must be more than zero!")

        user_id = session["user_id"]
        cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

        item_name = item["name"]
        item_price =item["price"]
        total_price = item_price * shares

        if cash < total_price:
            return apology("Not enogh cash")
        else:
            db.execute("UPDATE users SET cash = ? WHERE id = ?", cash - total_price, user_id)
            db.execute("INSERT INTO transactions (user_id, name, shares, price, type, symbol) VALUES (?, ?, ?, ?, ?, ?)", user_id, item_name, shares, item_price, 'buy', symbol)

        return redirect("/")

    elif request.method == "GET":
        return render_template("buy.html")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    user_id = session["user_id"]
    transaction = db.execute("SELECT type, symbol, price, shares, time FROM transactions WHERE user_id = ?", user_id)

    return render_template("history.html", transaction=transaction, usd=usd)


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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol").upper()

        if not symbol:
            return apology("symbol required!")

        item = lookup(symbol)
        if not item:
            return apology("cannot find a match!")
        return render_template("quoted.html", item = item, usd_func = usd)
    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":


        if not request.form.get("username"):
            return apology("must provide a username!")

        elif not request.form.get("password") or not request.form.get("confirmation"):
            return apology("must provide a password!")

        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("password and password confirmation must match")

        hash = generate_password_hash(request.form.get("password"))
        username = request.form.get("username")
        #result =
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hash)
        return redirect('/')

        #if not result:
            #return apology("alredy ragistered!")
        #result = db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hash)

        #session["user_id"] = result



    return render_template("register.html")




@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":
        user_id = session["user_id"]
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))

        if shares <= 0:
            return apology("shares must be more then 0")

        item_price = lookup(symbol)["price"]
        item_name = lookup(symbol)["name"]
        price = shares * item_price

        shares_owned = db.execute("SELECT shares FROM transactions WHERE user_id = ? AND symbol = ? GROUP BY symbol", user_id, symbol)[0]["shares"]

        if shares_owned < shares:
            return apology("you don't have enough shares!")

        current_cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]

        db.execute("UPDATE users SET cash = ? WHERE id = ?", current_cash + price, user_id)
        db.execute("INSERT INTO transactions (user_id, name, shares, price, type, symbol) VALUES (?, ?, ?, ?, ?, ?)", user_id, item_name, shares, item_price, "sell", symbol)
        return redirect("/")


    else:
        user_id = session["user_id"]
        symbols = db.execute("SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol", user_id)
        return render_template("sell.html", symbols=symbols)


#CREATE TABLE transactions 
#(
#id INTEGER PRIMARY KEY,
 #   user_id INTEGER NOT NULL,
  #  name TEXT NOT NULL,
   # shares INTEGER NOT NULL,
   # price NUMERIC NOT NULL,
   # type TEXT NOT NULL,
   # symbol TEXT NOT NULL,
  #  time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
   # FOREIGN KEY(user_id) REFERENCES users(id)
#);