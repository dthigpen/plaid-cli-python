import json
import plaid
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest



def list_accounts(client: plaid_api.PlaidApi, access_token: str) -> dict:
    request = AccountsGetRequest(access_token=access_token)
    response = client.accounts_get(request)
    accounts = response["accounts"]
    return accounts

def list_transactions(client: plaid_api.PlaidApi, access_token: str) -> list:
    request = TransactionsSyncRequest(
        access_token=access_token,
    )
    response = client.transactions_sync(request)
    response = json.loads(json.dumps(response.to_dict(), default=str))
    transactions = response["added"]

    # the transactions in the response are paginated, so make multiple calls while incrementing the cursor to
    # retrieve all transactions
    while response["has_more"]:
        request = TransactionsSyncRequest(
            access_token=access_token, cursor=response["next_cursor"]
        )
        response = client.transactions_sync(request)
        response = json.loads(json.dumps(response.to_dict(), default=str))
        transactions += response["added"]
    return transactions
