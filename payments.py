from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from flask_socketio import SocketIO

from square.client import Client
import string
import random

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*')

CORS(app)

CLIENT_EMAIL = "REPLACE_WITH_CLIENT_EMAIL"
AUTH_TOKEN = 'REPLACE_WITH_AUTH_TOKEN'
# change to production for client access and payments to work.
# CAUTION : This will access actual money and account data
DEV_ENV = 'sandbox' #"production" 
PAYMENT_AMOUNT = 1

def get_client_id(client):
   result = client.customers.search_customers(
      body = {
         "query": {
            "filter": {
            "email_address": {
               "exact": CLIENT_EMAIL
            }
            }
         },
         "count": True
      }
      )

   if result.is_success():
      print("Got client data")
      return [result.body["customers"][0]["id"], result.body["customers"][0]["cards"][0]["id"]]
   elif result.is_error():
      print(result.errors)

   return ""

def make_payment_worker(msg):
   client = Client(
      access_token=AUTH_TOKEN,
      environment=DEV_ENV, 
   )

   client_id, payment_card_id = get_client_id(client)
   if client_id == "":
       return
   
   unique_payment_id = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=36))

   print("Creating payment")

   result = client.payments.create_payment(
      body = {
         "source_id": payment_card_id,
         "customer_id": client_id,
         "idempotency_key": unique_payment_id,
         "amount_money": {
            "amount": PAYMENT_AMOUNT,
            "currency": "AUD"
         },
         "autocomplete": True,
         "accept_partial_authorization": False
      }
      )

   if result.is_success():
      print("Processing payment")
   elif result.is_error():
      print(result.errors)
      return
   
   created_payment_id = result.body["payment"]["id"]

   result = client.payments.complete_payment(
      payment_id = created_payment_id,
      body = {}
      )

   if result.is_success():
      print("Payment complete")
   elif result.is_error():
      print(result.errors)


#called when a client sends data
@socketio.on('make_payment')
def make_payment(message):
   print("--------")
   payment_desc = message['message']
   make_payment_worker(payment_desc)
   print("--------")

   

if __name__ == "__main__":
	socketio.run(app, host="0.0.0.0", debug=True,port=7777)