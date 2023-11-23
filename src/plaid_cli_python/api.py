import json
import plaid
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from datetime import date

def list_accounts(client: plaid_api.PlaidApi, access_token: str) -> dict:
    request = AccountsGetRequest(access_token=access_token)
    response = client.accounts_get(request)
    accounts = response["accounts"]
    return accounts


def list_transactions(client: plaid_api.PlaidApi, access_token: str,start=None, end=None) -> list:
    request = TransactionsSyncRequest(
        access_token=access_token,
    )
    response = client.transactions_sync(request)
    response = json.loads(json.dumps(response.to_dict(), default=str))
    transactions = []
    
    # the transactions in the response are paginated, so make multiple calls while incrementing the cursor to
    # retrieve all transactions
    while response["has_more"]:
        for t in response["added"]:
            t_date = date.fromisoformat(t["date"])
            if (end and t_date > end) or (start and  t_date < start):
                continue
            transactions.append(t)
        request = TransactionsSyncRequest(
            access_token=access_token, cursor=response["next_cursor"]
        )
        response = client.transactions_sync(request)
        response = json.loads(json.dumps(response.to_dict(), default=str))
    return transactions


def remove_item(client: plaid_api.PlaidApi, access_token: str):
    request = ItemRemoveRequest(access_token=access_token)
    client.item_remove(request)
