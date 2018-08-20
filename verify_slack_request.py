import os
import time
import urllib
import hmac
import hashlib
import base64

def verify_slack_request(request):
	slack_signing_secret = os.environ.get('SLACK_SIGNING_SECRET', None)
	is_prod = os.environ.get('IS_HEROKU', None)

	if 'X-Slack-Request-Timestamp' not in request.headers:
		return 'Error'

	timestamp = request.headers['X-Slack-Request-Timestamp']

	if is_prod == 'True' and (time.time() - int(timestamp) > 60 * 5):
		return 'Error'

	form_data = request.form.to_dict()
	form_string = urllib.parse.urlencode(form_data)

	message = 'v0:' + str(timestamp) + ":" + str(form_string)
	message = message.encode('utf-8')

	slack_signing_secret = bytes(slack_signing_secret, 'utf-8')
	my_signature = 'v0=' + hmac.new(slack_signing_secret, msg=message, digestmod=hashlib.sha256).hexdigest()

	slack_signature = request.headers['X-Slack-Signature']

	if hmac.compare_digest(my_signature, slack_signature):
		print("Verification succeeded.")
		return True
	elif is_prod is None:
		print("Verification failed, but continuing anyway since this is test environment.")
		return True
	else:
		print("Verification failed")
		return False
