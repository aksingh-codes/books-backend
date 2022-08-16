import datetime
from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

app = Flask(__name__)

mongodb_uri = os.getenv('MONGODB_URI')

client = MongoClient(mongodb_uri)

db = client.library_db

books_collection = db.books
transactions_collection = db.transactions

books_collection.create_index([('name', 'text')])


@app.route('/')
def index():
    return jsonify({
        "success": True,
        "message": "Welcome to the book database!"
    })


@app.route('/books')
def books():
    content_type = request.headers.get('Content-Type')
    if content_type == 'application/json':
        try:
            json = request.get_json()
            name = json.get('name')
            category = json.get('category')
            rent_per_day = json.get('rent_per_day')
            lt = None
            gt = None
            if (rent_per_day):
                lt = rent_per_day[0]
                gt = rent_per_day[1]

            if (name and category and rent_per_day):
                book_list = books_collection.find({
                    "$text": {"$search": name},
                    "category": category,
                    "rent_per_day": {"$lt": lt, "$gt": gt}
                })
            elif (name and category):
                book_list = books_collection.find({
                    "$text": {"$search": name},
                    "category": category
                })
            elif (name and rent_per_day):
                book_list = books_collection.find({
                    "$text": {"$search": name},
                    "rent_per_day": {"$lt": lt, "$gt": gt}
                })
            elif (category and rent_per_day):
                book_list = books_collection.find({
                    "category": category,
                    "rent_per_day": {"$lt": lt, "$gt": gt}
                })
            elif (name):
                book_list = books_collection.find({"$text": {"$search": name}})
            elif (category):
                book_list = books_collection.find({"category": category})
            elif (rent_per_day):
                book_list = books_collection.find(
                    {"rent_per_day": {"$lt": lt, "$gt": gt}})
            else:
                book_list = books_collection.find({})

            output = []

            for book in book_list:
                output.append(
                    {'name': book['name'], 'category': book['category'], 'rent_per_day': book['rent_per_day']})

            return jsonify(output)

        except:
            return jsonify({
                "success": False,
                "message": "Something went wrong!"
            })

    else:
        return jsonify({
            "success": False,
            "message": "ContentType is not supported!"
        })


@app.route('/transactions')
def transactions():
    output = []
    try:
        for transaction in transactions_collection.find():
            output.append({'book_name': transaction['book_name'], 'person_name': transaction['person_name'],
                           'book_id': str(transaction['book_id']), 'issue_date': transaction['issue_date']})
        return jsonify({
            "success": True,
            "results": output
        })

    except Exception:
        return jsonify({
            "success": False,
            "message": "Something went wrong!"
        })


@app.route('/transactions/book')
def book():
    content_type = request.headers.get('Content-Type')
    if content_type == 'application/json':
        try:
            json = request.get_json()
            book_name = json.get('book_name')

            transactions = transactions_collection.find(
                {"book_name": book_name})

            list_transactions = list(transactions)
            if (len(list_transactions) == 0):
                return jsonify("ERROR: No transactions found for book")

            book_id = list_transactions[0]['book_id']

            count = 0
            people = []
            rent = books_collection.find_one({"_id": ObjectId(book_id)})[
                'rent_generated']

            for transaction in transactions:
                count += 1
                people.append(transaction['person_name'])

            return jsonify(
                {
                    "success": True,
                    "results": {
                        "count": count,
                        "issued_by": people,
                        "total_rent_generated": rent
                    }
                })

        except Exception:
            return jsonify({
                "success": False,
                "message": "Something went wrong!"
            })

    else:
        return jsonify({
            "success": False,
            "message": "ContentType is not supported!"
        })


@app.route('/transactions/person')
def person():
    content_type = request.headers.get('Content-Type')
    if content_type == 'application/json':
        try:
            json = request.json
            person_name = json['person_name']

            transactions = transactions_collection.find(
                {"person_name": person_name})

            count = 0
            book_list = []

            for transaction in transactions:
                count += 1
                book_list.append(transaction['book_name'])

            return jsonify({
                "success": True,
                "results": {
                    "count": count,
                    "books_issued": book_list
                }
            })

        except Exception:
            return jsonify({
                "success": False,
                "message": "Something went wrong!"
            })

    else:
        return jsonify({
            "success": False,
            "message": "ContentType is not supported!"
        })


@app.route('/transactions/bydate')
def bydate():
    json = request.json
    greater_than = json['greater_than']
    less_than = json['less_than']

    try:
        transactions = transactions_collection.find(
            {
                "issue_date": {
                    "$gt": datetime.datetime.strptime(greater_than, "%Y-%m-%d"),
                    "lt": datetime.datetime.strptime(less_than, "%Y-%m-%d")}
            })

        output = []
        for transaction in transactions:
            output.append({
                "book_name": transaction['book_name'],
                "person_name": transaction['person_name'],
                "issue_date": transaction['issue_date'],
            })

        return jsonify({
            "success": True,
            "results": output
        })

    except:
        return jsonify({
            "success": False,
            "message": "Something went wrong!"
        })


@app.route('/transactions/issue', methods=['POST'])
def issue_book():
    content_type = request.headers.get('Content-Type')
    if content_type == 'application/json':
        try:
            json = request.json
            book_name = json['book_name']
            person_name = json['person_name']
            issue_date = datetime.datetime.now()

            # Check if already taken the book
            already_taken = transactions_collection.find_one(
                {"person_name": person_name, "book_name": book_name})

            if already_taken:
                return jsonify(f"ERROR: This book has already been taken by {person_name}")

            # Find Book in Database
            book_in_db = books_collection.find_one({"name": book_name})

            if book_in_db['name'] == book_name:
                transaction_id = transactions_collection.insert_one(
                    {"book_id": str(book_in_db["_id"]), "book_name": book_name, "person_name": person_name, "issue_date": issue_date})
                return jsonify({
                    "success": True,
                    "message": "Successfully issued book"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "Failed to find book"
                })

        except Exception:
            return jsonify({
                "success": False,
                "message": "Something went wrong"
            })

    else:
        return jsonify({
            "success": False,
            "message": "ContentType is not supported!"
        })


@app.route('/transactions/return', methods=['POST'])
def return_book():
    content_type = request.headers.get('Content-Type')
    if content_type == 'application/json':
        try:
            json = request.json
            book_name = json['book_name']
            person_name = json['person_name']

            # Find and delete Transaction
            found_transaction = transactions_collection.find_one(
                {"person_name": person_name, "book_name": book_name})

            if found_transaction:
                book = books_collection.find_one(
                    {"_id": ObjectId(found_transaction['book_id'])})
                rent_per_sec = book['rent_per_day'] / \
                    86400  # convert to seconds

                date_difference = datetime.datetime.now(
                ) - found_transaction['issue_date']
                seconds = date_difference.seconds

                rent_generated = book['rent_generated'] + \
                    (seconds * rent_per_sec)

                # Update rent_generated and delete transaction
                book = books_collection.update_one({"_id": ObjectId(found_transaction['book_id'])}, {
                    "$set": {"rent_generated": rent_generated}})
                transactions_collection.delete_one(
                    {"_id": ObjectId(found_transaction["_id"])})

                return jsonify({
                    "success": True,
                    "message": "Returned book successfully"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "No transaction found"
                })

        except Exception:
            return jsonify({
                "success": False,
                "message": "Something went wrong!"
            })

    else:
        return jsonify({
            "success": False,
            "message": "ContentType is not supported!"
        })


@app.errorhandler(404)
def page_not_found(e):
    return jsonify({
        "success": False,
        "message": "The requested page does not exist."
    }), 404


if __name__ == "__main__":
    app.run()
