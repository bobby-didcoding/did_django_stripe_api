from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.http import HttpResponse
import json

from api.mixins import (
	StripeAccount,
	StripePayment,
	StripeData,
	)

from api.models import (
	Invoicing
	)

import stripe
stripe_key = settings.STRIPE_PUBLISHABLE
stripe.api_key = settings.STRIPE_SECRET


'''
Cart view for Stripe payment
'''
@login_required
def cart(request):

	user = request.user
	stripe_data = StripeData(user)

	context = {
		"stripe_key": stripe_key,
		"cards": stripe_data.cards(),
	}
	return render(request,'api/cart.html', context)


'''
AJAX function to handle a Stripe payment
'''
@login_required
def payment(request):

	if request.method == "POST":

		user = request.user
		token = request.POST.get('stripeToken',None)
		card_id = request.POST.get("card_id", None)
		paymentMethodNonce = request.POST.get("paymentMethodNonce", None)
		description = request.POST.get("description", None)
		currency = request.POST.get("currency", None)
		set_default = request.POST.get("set_default", None)

		amount = request.POST.get('amount')
		stripe_amount = int(float(amount)*100)
		

		agent_id = user.userprofile.agent_id

		if not agent_id:
			StripeAccount(request.user)

		payment = StripePayment(
			user=user,
			agent_id=agent_id,
			token=token,
			card_id=card_id,
			amount=stripe_amount,
			description = description,
			currency=currency,
			set_default=set_default
			).create()

		if payment["message"] == "Perfect":

			invoice = Invoicing(
				user = user,
				tran_id = payment["tran_id"],
				amount = float(amount)
				)
			invoice.save()
			user = user

			return HttpResponse(
					json.dumps({"result": "okay"}),
					content_type="application/json"
					)
		else:
			return HttpResponse(
					json.dumps({"result": "error", "message":payment["message"] }),
					content_type="application/json"
					)
	else:
		return HttpResponse(
			json.dumps({"result": "error"}),
			content_type="application/json"
			)

