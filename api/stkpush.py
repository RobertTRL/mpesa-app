import requests
import base64
import os
from datetime import datetime
from lib.accesstoken import AccessToken
from dotenv import load_dotenv

load_dotenv()

class STKPush:
    """Handles M-Pesa STK Push (Lipa na M-Pesa Online) requests."""

    def __init__(self, auth):
        self.auth         = auth
        self.shortcode    = os.environ.get("PRODUCTION_SHORTCODE")
        self.passkey      = os.environ.get("PRODUCTION_PASSKEY")
        self.callback_url = os.environ.get("PRODUCTION_CALLBACK_URL")
        self.till_number = os.getenv("PRODUCTION_TILL_NUMBER")
        self.base_url = "https://api.safaricom.co.ke"

    def _generate_password(self):
        timestamp  = datetime.now().strftime("%Y%m%d%H%M%S")
        raw_string = f"{self.shortcode}{self.passkey}{timestamp}"
        password   = base64.b64encode(raw_string.encode("utf-8")).decode("utf-8")
        return password, timestamp

    def _normalize_phone(self, phone: str):
        """Normalize phone to 2547XXXXXXXX format."""
        phone = phone.strip().replace(" ", "")
        if phone.startswith("+"): phone = phone[1:]
        if phone.startswith("0"): phone = "254" + phone[1:]

        if not phone.startswith("254") or len(phone) != 12:
            raise ValueError(f"Invalid phone number: {phone}. Expected format: 254XXXXXXXXX")
        return phone

    def initiate(self, phone_number='254791154865', amount=1, account_reference="BOBTOROITICH", transaction_description = "Payment"):
        """
        Initiate an STK Push payment request.

        Args:
            phone_number: Customer's phone (any common format)
            amount: Amount in KES (whole number, min 1)
            account_reference: Your order/invoice reference (max 12 chars)
            transaction_description: Brief description (max 13 chars)
        """
        if amount < 1:
            raise ValueError("Amount must be at least KES 1")
        if len(account_reference) > 12:
            raise ValueError("AccountReference must be 12 characters or fewer")
        if len(transaction_description) > 13:
            raise ValueError("TransactionDesc must be 13 characters or fewer")

        normalized_phone      = self._normalize_phone(phone_number)
        password, timestamp   = self._generate_password()
        access_token          = self.auth.get_access_token()

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password":          password,
            "Timestamp":         timestamp,
            "TransactionType":   "CustomerBuyGoodsOnline",
            "Amount":            amount,
            "PartyA":            normalized_phone,
            "PartyB":            self.till_number,
            "PhoneNumber":       normalized_phone,
            "CallBackURL":       self.callback_url,
            "AccountReference":  account_reference,
            "TransactionDesc":   transaction_description,
        }

        try:
            response = requests.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type":  "application/json",
                },
                timeout=30,
            )
            data = response.json()

            if data.get("ResponseCode") == "0":
                return {
                    "success":              True,
                    "checkout_request_id":  data["CheckoutRequestID"],
                    "merchant_request_id":  data["MerchantRequestID"],
                    "response_description": data["ResponseDescription"],
                    "customer_message":     data["CustomerMessage"],
                }
            else:
                return {
                    "success": False,
                    "error":   data.get("ResponseDescription", "Unknown error"),
                    "raw":     data,
                }

        except requests.exceptions.Timeout:
            raise Exception("STK Push request timed out.")
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to Safaricom API.")

    def query_status(self, checkout_request_id: str):
        """Query the status of a pending STK Push request."""
        password, timestamp = self._generate_password()
        access_token        = self.auth.get_access_token()

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password":          password,
            "Timestamp":         timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        response = requests.post(
            f"{self.base_url}/mpesa/stkpushquery/v1/query",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            },
            timeout=30,
        )
        return response.json()
    
auth = AccessToken()
push = STKPush(auth)
push.initiate()
