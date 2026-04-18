import os

# MTN Mobile Money API (Sandbox)
MTN_MOMO_ENVIRONMENT = 'sandbox'
MTN_MOMO_SUBSCRIPTION_KEY = os.getenv('MTN_MOMO_SUBSCRIPTION_KEY')
MTN_MOMO_API_USER = os.getenv('MTN_MOMO_API_USER')
MTN_MOMO_API_KEY = os.getenv('MTN_MOMO_API_KEY')
MTN_MOMO_TARGET_ENVIRONMENT = 'sandbox'
MTN_MOMO_CALLBACK_URL = 'https://your-domain.com/api/v1/commerce/payments/mtn-callback/'