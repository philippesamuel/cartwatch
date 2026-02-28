import os
from app.flows.ingest import ingest_receipts


# integration test
# prefect flow to ingest receipts from gmail
# need to generate google access token:
# https://developers.google.com/oauthplayground/?iss=https://accounts.google.com&scope=https://www.googleapis.com/auth/gmail.readonly
#
# run local prefect server: uv run prefect server start
# 
def test_ingest_receipts():
    user_id = os.environ["SUPABASE_TEST_USER_ID"]  # your user id from supabase
    access_token = os.environ["GMAIL_ACCESS_TOKEN"]

    result = ingest_receipts(user_id=user_id, access_token=access_token)
    print(f"Processed {len(result)} emails: {result}")
    assert isinstance(result, list)