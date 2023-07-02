from flask import Flask, render_template, redirect, request, session, send_file
from flask_session import Session
from urllib import request
from flask import Flask, render_template
from flask import Flask, redirect, url_for, render_template, request
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime
import pandas as pd
import csv
import json
import urllib.parse
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
firebase_key = os.environ.get('FIREBASE_KEY')
if firebase_key is None:
    raise ValueError('FIREBASE_KEY environment variable is not set.')

firebase_key_dict = json.loads(firebase_key)
cred = credentials.Certificate(firebase_key_dict)
firebase_admin.initialize_app(cred)

# Get a reference to the Firestore database
db = firestore.client()
# Now you can use the 'db' object to interact with the Firestore database

app = Flask(__name__)

app.config['SESSION_TYPE'] = 'memcached'
app.config['SECRET_KEY'] = 'super secret key'
sess = Session()

visitedFlag = 2

@app.route('/')
def home():
    return render_template('index.html')

#visualize the expenses in pie chart
from collections import defaultdict

@app.route('/chart/<expenses>', methods=["GET"])
def show_chart(expenses):
    decoded_expenses = urllib.parse.unquote(expenses)
    expenses_list = eval(decoded_expenses)

    category_amounts = defaultdict(int)

    for expense in expenses_list:
        category = expense['category']
        amount = expense['amount']
        category_amounts[category] += amount

    chart_data = [{'category': category, 'amount': amount} for category, amount in category_amounts.items()]

    return render_template('chart.html', expenses=chart_data)


# downloading the expense data into csv format (not working )
@app.route('/download/<expenses>', methods=["GET"])
def download(expenses):
    expenses = expenses.replace("'", "\"")

    # Save the table data to a CSV file
    with open('expenses.csv', 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        # Write the header row
        writer.writerow(['Date', 'Expense Name', 'Amount', 'Category'])

        docs_list = json.loads(expenses)

        for row in docs_list:
            # Write each row of data
            writer.writerow([row["date"], row["name"],
                            row["amount"], row["category"]])

    # Replace with the path to your local file
    filename = 'C:\\Users\\hp\\Documents\\python api projects\\Finance Tracker\\expenses.csv'
    return send_file(filename, as_attachment=True)

# show all the expenses between start date and end date
@app.route('/show-all-expenses', methods=["GET", "POST"])
def showAll():
    global visitedFlag
    visitedFlag = 3
    if request.method == "GET":
        return render_template('showall.html')
    else:
        s_date = request.form["start_date"]
        e_date = request.form["end_date"]
        start_date = datetime.strptime(s_date, "%Y-%m-%d")
        end_date = datetime.strptime(e_date, "%Y-%m-%d")

        if(start_date > end_date):
            success_message = "Start date should be less than end date"
            return render_template('showall.html', success_message=success_message)

        month_list = pd.period_range(start=s_date, end=e_date, freq='M')
        month_list = [month.strftime("%m-%Y") for month in month_list]

        # list of months containing all the elements except 1st and last element
        new_list = month_list[1:-1]
        all_expenses = []
        expenses = []
        current_user = session.get('current_user', None)

        # for the starting and ending month compare with the actual dates
        # if it is greater than or equal to start_date and less than or equal to end_date
        # add the expense to a list
        start_mon_ref = db.collection(f"{current_user}").document(
            f"{month_list[0]}").collection('expenses')
        transactions = start_mon_ref.get()
        for t in transactions:
            cur_trans = t.to_dict()
            date = cur_trans["date"]
            cur_date = datetime.strptime(date, "%Y-%m-%d")
            if(cur_date >= start_date and cur_date <= end_date):
                all_expenses.append(t)
                expenses.append(cur_trans)

        # for the rest of the months in between add all the transactions as it is
        for mon in new_list:
            doc_ref = db.collection(f"{current_user}").document(
                f"{mon}").collection('expenses')
            month_transactions = doc_ref.get()
            for mon in month_transactions:
                all_expenses.append(mon)
                expenses.append(mon.to_dict())

        end_mon_ref = db.collection(f"{current_user}").document(
            f"{month_list[-1]}").collection('expenses')
        transactions = end_mon_ref.get()
        for t in transactions:
            cur_trans = t.to_dict()
            date = cur_trans["date"]
            cur_date = datetime.strptime(date, "%Y-%m-%d")
            if(cur_date >= start_date and cur_date <= end_date):
                all_expenses.append(t)
                expenses.append(cur_trans)

        return render_template('showall.html', all_expenses=all_expenses, date="Date", name="Name", category="Category", amount="Amount", edit="Edit", delete="Delete", expenses=expenses)

# deleting the current transaction
@app.route('/delete/<date>/<docid>', methods=["GET"])
def delete(date, docid):
    current_user = session.get('current_user', None)
    d = date.split('-')
    # taking month from the date
    month = d[1]+"-"+d[0]

    doc_ref = db.collection(f"{current_user}").document(
        f"{month}").collection("expenses").document(docid)
    doc_ref.delete()

    success_message = "Your expense was deleted successfully!"
    if(visitedFlag == 1):
        return render_template('showdaily.html', success_message=success_message)
    if (visitedFlag == 3):
        return render_template('showall.html', success_message=success_message)
    return render_template('show.html', success_message=success_message)

# editing the current transaction
@app.route('/edit/<date>/<docid>', methods=["GET"])
def edit(date, docid):
    if request.method == "GET":
        # get the data
        global editDate
        editDate = date
        global editDocId
        editDocId = docid
        current_user = session.get('current_user', None)
        d = date.split('-')
        # taking month from the date
        month = d[1]+"-"+d[0]
        global doc_ref
        doc_ref = db.collection(f"{current_user}").document(
            f"{month}").collection("expenses").document(docid)
        doc_snapshot = doc_ref.get()

        global data
        # Check if the document exists
        if doc_snapshot.exists:
            data = doc_snapshot.to_dict()
            # Use the data retrieved from Firestore
            print(data)
        else:
            print(f'Document with ID {docid} does not exist')
        # show on the form
        return render_template('edit.html', data=data)

# updating the changes
@app.route('/edit', methods=["POST"])
def editExpense():
    referer = request.headers.get('Referer')
    print(referer)

    # post request
    # let the user make changes
    # update the values
    current_user = session.get('current_user', None)

    d = editDate.split('-')
    # taking month from the date
    month = d[1]+"-"+d[0]

    doc_ref = db.collection(f"{current_user}").document(
        f"{month}").collection("expenses").document(editDocId)
    doc_ref.update({
        'name': request.form["name"],
        'amount': request.form["amount"],
        'date': request.form["date"],
        'category': request.form.get("category")
    })
    doc_snapshot = doc_ref.get()

    global data
    # Check if the document exists
    if doc_snapshot.exists:
        data = doc_snapshot.to_dict()
        # Use the data retrieved from Firestore
        print(data)
    else:
        print(f'Document with ID {editDocId} does not exist')

    success_message = "Your expense was updated successfully!"
    if(visitedFlag == 1):
        return render_template('showdaily.html', success_message=success_message)

    return render_template('show.html', success_message=success_message)

# reset the password
@app.route('/reset-password', methods=["POST", "GET"])
def reset_password():
    if request.method == "GET":
        return render_template('forgot.html')
    else:
        # get the username, new password
        username = request.form["username"]
        new_password = request.form["new_password"]

        doc_ref = db.collection('users')
        users = doc_ref.get()
        flag = 0

        # check if the user exists in the database
        for user in users:
            current_user = user.to_dict()
            if(username == current_user['username']):
                flag = 1
                break

        # if the username is correct, update the password and display the success message
        if flag == 1:
            # update the password in the firestore database and display the message

            # get the document refernce for the particular user
            user_ref = db.collection('users').where(
                "username", "==", f"{username}").get()

            # grab the document id
            global doc_id
            for user in user_ref:
                doc_id = user.id

            # update the password
            user = db.collection('users').document(f"{doc_id}")
            user.update({"password": new_password})

            # ender the page
            message = "Password updated successfully!!!"
            return render_template('forgot.html', message=message)
        else:
            # the user does not exist
            # display the appropriate message and render the page
            message = "No such user exists!!!"
            return render_template('forgot.html', message=message)

# show-daily-expenses
@app.route('/show-daily-expenses', methods=["POST", "GET"])
def daily():
    global visitedFlag
    visitedFlag = 1
    if request.method == "GET":
        return render_template('showdaily.html')
    else:
        # get the current user from the session
        current_user = session.get('current_user', None)

        # take the respective date
        date = request.form["date"]  # yyyy-mm-dd

        d = date.split('-')
        # taking month from the date
        month = d[1]+"-"+d[0]

        flag = 0
        sum = 0
        # selecting all the data of a particular date
        docs = db.collection(f"{current_user}").document(f"{month}").collection(
            "expenses").where("date", "==", f"{date}").get()

        expenses = []
        for doc in docs:
            flag = 1
            record = doc.to_dict()
            expenses.append(record)
            sum = sum + int(record["amount"])
        print("Daily expense is: ", sum)

        return render_template('showdaily.html', date="Date", name="Expense name", amount="Amount", edit="Edit", delete="Delete", category="Category", docs=docs, flag=flag, sum=sum, expenses=expenses)

# monthly expenses
@app.route('/show-monthly-expenses', methods=["POST", "GET"])
def show():
    global visitedFlag
    visitedFlag = 2

    if request.method == "GET":
        return render_template('show.html')
    else:
        # get the current user from the session
        current_user = session.get('current_user', None)

        # take the respective date
        month = request.form["month"]  # 2022-05
        monthID = month.split('-')
        month = monthID[1]+"-"+monthID[0]
        flag = 0
        # if there is a transaction of the user, show it
        doc_ref = db.collection(f"{current_user}").document(
            f"{month}").collection('expenses')
        month_transactions = doc_ref.get()

        expenses = []
        # calculate monthly total expense
        sum = 0
        for mon in month_transactions:
            flag = 1
            cur_data = mon.to_dict()
            expenses.append(cur_data)
            sum = sum + int(cur_data["amount"])
        print("Total is: ", sum)

        # return the page with the data
        return render_template('show.html', date="Date", name="Expense name", amount="Amount", category="Category", edit="Edit", delete="Delete", month_transactions=month_transactions, flag=flag, sum=sum, expenses=expenses)

# adding a transaction
@app.route('/add-transaction', methods=["POST", "GET"])
def transactions():
    if request.method == "POST":
        # take the transaction name, date and amount
        name = request.form["name"]
        amount = request.form["amount"]

        # getting the category of the expense
        category = request.form.get("category")

        # converting the string into integer
        amount = int(amount)

        date = request.form["date"]

        # take the username from the login page (use session to retrive the username)
        current_user = session.get('current_user', None)

        # add it to the respective user's collection in the appropriate month
        l = date.split('-')
        monthID = l[1]+"-" + l[0]

        db.collection(f"{current_user}").document(f"{monthID}").collection('expenses').add({
            "name": name,
            "amount": amount,
            "date": date,
            "category": category
        })

        success_message = 'Your expense was added successfully!'
        # show the message when data is added successfully
        return render_template('transaction.html', success_message=success_message)
    if request.method == "GET":
        return render_template('transaction.html')

# login and signup form
@app.route('/get-started', methods=["GET", "POST"])
def getStarted():
    if request.method == "POST":
        if "login" in request.form:
            # take the entered username and password by the user
            username_login = request.form["username_login"]
            password_login = request.form["password_login"]
            doc_ref = db.collection('users')
            users = doc_ref.get()
            flag = 0

            # check if the user exists in the database
            for user in users:
                current_user = user.to_dict()
                if(username_login == current_user['username'] and password_login == current_user['password']):
                    flag = 1
                    break
            # if user exists, direct them to the transaction page
            if flag == 1:
                session['current_user'] = username_login
                return render_template('transaction.html')
            # if no such user exists, show the appropriate message
            else:
                message = "No such user exists. Please click on Sign-up to register"
                return render_template('start.html', message=message)

        if "signup" in request.form:
            # take the username, password and confirm password
            username = request.form["username"]
            password = request.form["password"]
            confirmpass = request.form["confirmpass"]
            # first check if the same user exists in the database or not
            doc_ref = db.collection('users')
            users = doc_ref.get()
            flag = 0
            for user in users:
                current_user = user.to_dict()
                if(username == current_user['username']):
                    flag = 1
                    break
            if flag == 1:
                message = "User already exists. Please use a different username"
                return render_template('start.html', message=message)

            # add the username and password to the firebase
            db.collection('users').add(
                {'username': username, 'password': password})

            # display the message to login
            message = "User created successfully. Please now login with your username and password"
            return render_template('start.html', message=message)
    else:
        return render_template('start.html')

if __name__ == '__main__':
    app.run(debug=True)
    sess.init_app(app)