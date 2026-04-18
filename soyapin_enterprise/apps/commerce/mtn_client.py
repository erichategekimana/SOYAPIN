import requests
import uuid
import base64
from django.conf import settings
from datetime import datetime, timezone, timedelta

class MTNMoMoClient:
    """
    MTN Mobile Money API client (sandbox/production).
    Documentation: https://momodeveloper.mtn.com/
    """
    def __init__(self):
        self.subscription_key = settings.MTN_MOMO_SUBSCRIPTION_KEY
        self.api_user = settings.MTN_MOMO_API_USER
        self.api_key = settings.MTN_MOMO_API_KEY
        self.environment = settings.MTN_MOMO_ENVIRONMENT
        self.target_env = settings.MTN_MOMO_TARGET_ENVIRONMENT
        self.base_url = "https://sandbox.momodeveloper.mtn.com" if self.environment == 'sandbox' else "https://api.mtn.com"
        self.token = None
        self.token_expiry = None

    def _get_basic_auth(self):
        """Generate Basic Auth header for API user & key"""
        credentials = f"{self.api_user}:{self.api_key}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    def _get_headers(self, with_subscription=True):
        headers = {
            'X-Target-Environment': self.target_env,
            'Content-Type': 'application/json',
        }
        if with_subscription:
            headers['Ocp-Apim-Subscription-Key'] = self.subscription_key
        return headers

    def _get_token(self):
        """Obtain OAuth2 token from MTN"""
        if self.token and self.token_expiry and datetime.now(timezone.utc) < self.token_expiry:
            return self.token

        url = f"{self.base_url}/collection/token/"
        headers = self._get_headers(with_subscription=False)
        headers['Authorization'] = self._get_basic_auth()
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            self.token = data['access_token']
            expires_in = data.get('expires_in', 3600)
            self.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            return self.token
        else:
            raise Exception(f"Failed to get MTN token: {response.status_code} - {response.text}")

    def request_to_pay(self, amount, currency, phone_number, external_id=None, payer_message="Payment for order", payee_note="Soyapin order"):
        """
        Request a payment from a customer's mobile money account.
        Returns transaction reference if successful.
        """
        token = self._get_token()
        if not external_id:
            external_id = str(uuid.uuid4())

        url = f"{self.base_url}/collection/v1_0/requesttopay"
        headers = self._get_headers()
        headers['Authorization'] = f'Bearer {token}'
        headers['X-Reference-Id'] = external_id

        payload = {
            "amount": str(amount),
            "currency": currency,
            "externalId": external_id,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": phone_number
            },
            "payerMessage": payer_message,
            "payeeNote": payee_note
        }

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 202:
            # Accepted – payment request initiated
            return external_id
        else:
            error_msg = response.text
            raise Exception(f"MTN payment request failed: {response.status_code} - {error_msg}")

    def get_payment_status(self, reference_id):
        """Check status of a payment request"""
        token = self._get_token()
        url = f"{self.base_url}/collection/v1_0/requesttopay/{reference_id}"
        headers = self._get_headers()
        headers['Authorization'] = f'Bearer {token}'
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get payment status: {response.status_code} - {response.text}")