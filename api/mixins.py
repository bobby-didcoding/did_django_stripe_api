from datetime import datetime, date, time, timedelta
from django.conf import settings
from users.models import UserProfile
from api.models import Invoicing
import stripe
stripe_key = settings.STRIPE_PUBLISHABLE
stripe.api_key = settings.STRIPE_SECRET
tax_id = settings.STRIPE_TAX




'''
Manages the creation of a Stripe user account
'''
class StripeAccount:

	def __init__(self, user):

		self.user = user

		#create Stripe account
		agent_account = stripe.Customer.create(
			email = self.user.username,
			address={
				"line1":self.user.userprofile.address,
				"city":self.user.userprofile.town,
				"state":self.user.userprofile.county,
				"postal_code": self.user.userprofile.post_code,
				},
			name=f'{self.user.first_name.capitalize()} {self.user.last_name.capitalize()}',
			phone= self.user.userprofile.telephone
			)
		up = self.user.userprofile
		up.agent_id = agent_account["id"]
		up.save()




'''
Manage payments
'''
class StripePayment:

	def __init__(self, *args, **kwargs):

		self.user = kwargs.get("user")
		self.agent_id = kwargs.get("agent_id")
		self.token = kwargs.get("token")
		self.amount = kwargs.get("amount")
		self.card_id = kwargs.get("card_id")
		self.description = kwargs.get("description")
		self.currency = kwargs.get("currency")
		self.set_default = kwargs.get("set_default")

	def create(self):

		try:
			#Create a source (new card)
			if self.token:
				card = stripe.Customer.create_source(
				  self.agent_id,
				  source=self.token
				)
			#Retreive a source (saved card)
			else:
				card = stripe.Customer.retrieve_source(
					self.agent_id,
					self.card_id
					)
			
			#Modify Stipes customer account with a default card
			if self.set_default or self.token:
				stripe.Customer.modify(
					self.agent_id, 
					default_source=card.id,
					)

			#Create an invoice items for the transaction
			invoice_item = stripe.InvoiceItem.create(
			  customer= self.agent_id,
			  amount= self.amount,
			  currency='gbp',
			  description= self.description
			)

			#Create invoice
			new_invoice = stripe.Invoice.create(
			  customer=self.agent_id,
			  # default_tax_rates=[tax_id],
			  collection_method="charge_automatically",
			)

			#Finalise the invoice for payment
			invoice = stripe.Invoice.finalize_invoice(new_invoice.id)

			#Pay the invoice 
			charge = stripe.Invoice.pay(
				invoice.id,
				source=card.id,
				)

			message = "Perfect"
			return {"message": message, "tran_id": charge["id"]}

		except stripe.error.CardError as e:
			message = "Card Error"
			return {"message": message, "tran_id": None}

		except stripe.error.RateLimitError as e:
			message = "Rate limit error"
			return {"message": message, "tran_id": None}
		
		except stripe.error.InvalidRequestError as e:
			message = "Invalid parameter"
			return {"message": message, "tran_id": None}
		
		except stripe.error.AuthenticationError as e:
			message = "Not authenticated"
			return {"message": message, "tran_id": None}

		except stripe.error.APIConnectionError as e:
			message = "Network error"
			return {"message": message, "tran_id": None}
		
		except stripe.error.StripeError as e:
			message = "Something went wrong, you were not charged"
			return {"message": message, "tran_id": None}
		
		except Exception as e:
			message = "Serious error, we have been notified"
			return {"message": message, "tran_id": None}



'''
Produces and returns a list of cards assigned to each user
'''
class StripeData:

	def __init__(self, user):
		self.user = user

	def cards(self):

		agent_id = self.user.userprofile.agent_id			
		
		try:
			#Query saved user cards
			cards = stripe.Customer.list_sources(
				  agent_id,
				  limit=3,
				  object='card'
				)

			#Create a list of cards
			card_list = [
			[c["id"], c["brand"],f'**** {c["last4"]}',f'{c["exp_month"]}/{c["exp_year"]}'] 
			for c in cards["data"]
			]

			if not card_list:
				return None
			return card_list
		except:
			return  None
		

	def invoices(self):

		agent_id = self.user.userprofile.agent_id

		try:

			#Query user invoices
			invoices = stripe.Invoice.list(
				customer = agent_id
				)	

			invoice_list = [
			[
				Invoicing.objects.get(tran_id = inv["id"]).id,
				datetime.fromtimestamp(int(inv["created"])).strftime('%d-%m-%Y'),
				inv["lines"]["data"][0]["description"],
				inv["amount_paid"]/100,			
				inv["hosted_invoice_url"],
				inv["invoice_pdf"]

			] 
			for inv in invoices["data"]]

			if not invoice_list:
				return None
			return  invoice_list		
		except:
			return None
				
		
		

