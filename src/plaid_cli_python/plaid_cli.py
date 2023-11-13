import argparse
import json
from string import Template
from pathlib import Path
from multiprocessing import Process

import plaid
from plaid.api import plaid_api
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.country_code import CountryCode
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.transactions_sync_request import TransactionsSyncRequest

from flask import Flask
from flask import request

DEFAULT_APP_DIR = Path.home() / ".plaid-cli-python"
DEFAULT_APP_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_CONFIG = {
    "PORT": 8080,
    "PLAID_ENV": "sandbox",
    "PLAID_CLIENT_ID": None,
    "PLAID_SECRET": None,
    "PLAID_SANDBOX_REDIRECT_URI": None,
    "PLAID_API_VERSION": "2020-09-14",
}

DEFAULT_DATA = {
    "tokens": [],
    "items": [],
    "token_aliases": {},
    "item_aliases": {},
    "aliases": {},
}

from importlib.resources import files

home_html_template_text = (
    files("plaid_cli_python.templates").joinpath("home.html").read_text()
)


def __merge(source, destination):
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            __merge(value, node)
        else:
            destination[key] = value

    return destination


def load_json_file(config_path: Path, default_json: dict) -> dict:
    config = default_json.copy()
    if config_path.is_file():
        with open(config_path) as f:
            config = __merge(json.load(f), config)
    return config


def write_json_file(config_path: Path, content: dict):
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(content, indent=True, sort_keys=True))


def get_plaid_env(env_str: str):
    if env_str == "sandbox":
        return plaid.Environment.Sandbox
    if env_str == "development":
        return plaid.Environment.Development
    if env_str == "production":
        return plaid.Environment.Production
    raise ValueError(
        "Expected one of [sandbox|development|production] as an environment."
    )


def open_client(config: dict):
    plaid_env = get_plaid_env(config.get("PLAID_ENV"))
    plaid_client_id = config.get("PLAID_CLIENT_ID")
    plaid_secret = config.get("PLAID_SECRET")
    plaid_version = config.get("PLAID_API_VERSION")

    configuration = plaid.Configuration(
        host=plaid_env,
        api_key={
            "clientId": plaid_client_id,
            "secret": plaid_secret,
            "plaidVersion": plaid_version,
        },
    )
    api_client = plaid.ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)


def resolve_alias(data: dict, token_or_alias: str) -> str:
    if token_or_alias in data["tokens"]:
        return token_or_alias
    elif token_or_alias in data["token_aliases"]:
        return data["token_aliases"][token_or_alias]
    elif token_or_alias in data["item_aliases"]:
        return data["item_aliases"][token_or_alias]
    else:
        raise ValueError(f"Token or alias does not exist for {token_or_alias}.")


def save_data(data: dict, path: Path = None):
    if not path:
        path = DEFAULT_APP_DIR / "data.json"
    write_json_file(path, data)


def load_data(path: Path = None) -> dict:
    if not path:
        path = DEFAULT_APP_DIR / "data.json"
    return load_json_file(path, DEFAULT_DATA)


def save_config(config: dict, path: Path = None):
    if not path:
        path = DEFAULT_APP_DIR / "config.json"
    write_json_file(path, config)


def load_config(path: Path = None) -> dict:
    if not path:
        path = DEFAULT_APP_DIR / "config.json"
    return load_json_file(path, DEFAULT_CONFIG)


def run_link_server(
    client: plaid_api.PlaidApi, link_alias: str = None, new_token=False
):
    config = load_config()
    data = load_data()
    if link_alias in data["tokens"]:
        raise ValueError(f"Cannot use token string as an alias")
    existing_token = ""
    if not new_token and link_alias in data["token_aliases"]:
        existing_token = data["token_aliases"][link_alias]

    app = Flask("Plaid Account Linker")
    server = Process(target=app.run, kwargs={"port": config["PORT"]})

    @app.route("/", methods=["GET"])
    def create_link():
        t = Template(home_html_template_text)
        return t.safe_substitute(existing_token=existing_token)

    @app.route("/relink", methods=["GET"])
    def relink():
        server.terminate()

    @app.route("/api/exchange-public-token", methods=["POST"])
    def exchange_public_token():
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=request.json["public_token"]
        )
        exchange_response = client.item_public_token_exchange(exchange_request)
        access_token = exchange_response["access_token"]
        data["tokens"].append(access_token)
        if link_alias:
            data["token_aliases"][link_alias] = access_token

        save_data(data)
        server.terminate()  # to terminate the server
        return f"Access token written to: {DEFAULT_APP_DIR / 'data.json'}"

    @app.route("/api/create-link-token", methods=["GET"])
    def create_link_token():
        print("HIT /api/create-link-token")
        redirect_uri = (
            config["PLAID_SANDBOX_REDIRECT_URI"]
            if "PLAID_SANDBOX_REDIRECT_URI" in config
            else None
        )
        req = LinkTokenCreateRequest(
            products=[Products("transactions")],
            client_name="Plaid Account Linker",
            country_codes=[CountryCode("US")],
            language="en",
            user=LinkTokenCreateRequestUser(client_user_id="absent-user"),
            # redirect_uri=redirect_uri
        )
        try:
            response = client.link_token_create(req)
            print("post res")
            return response.to_dict()
        except Exception as e:
            print(f"Encountered exception: {e}")
            return "Encountered an error", 500

    server.start()


def list_accounts(client: plaid_api.PlaidApi, access_token: str):
    request = AccountsGetRequest(access_token=access_token)
    response = client.accounts_get(request)
    accounts = response["accounts"]

    print("Account:Subaccount\tAccountName\tAcctNum\tAcctID")
    for a in accounts:
        print(
            "%s:%s\t%s\t%s\t%s"
            % (a["type"], a["subtype"], a["name"], a["mask"], a["account_id"])
        )


def list_transactions(client: plaid_api.PlaidApi, access_token: str):
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
    print(json.dumps(transactions))


def add_alias(item_id: str, alias_name: str):
    data = load_data()
    data["aliases"][alias_name] = item_id
    save_data(data)


def _main():
    parser = argparse.ArgumentParser("A command line interface for the Plaid API")
    subparsers = parser.add_subparsers(dest="command")
    link_parser = subparsers.add_parser("link")
    link_parser.add_argument("alias", type=str, help="Alias for this institution")
    link_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force a new token instead of refreshing the existing token",
    )

    accounts_parser = subparsers.add_parser("accounts")
    accounts_parser.add_argument("token_or_alias")

    transactions_parser = subparsers.add_parser("transactions")
    transactions_parser.add_argument("token_or_alias")

    alias_parser = subparsers.add_parser("alias")
    alias_parser.add_argument(
        "item_id", type=str, help="The item id you want to add an alias for"
    )
    alias_parser.add_argument(
        "name", type=str, help="The alias you want to refer to the item id with"
    )
    args = parser.parse_args()
    config = load_config()
    data = load_data()
    client = open_client(config)
    if args.command == "link":
        run_link_server(client, link_alias=args.alias, new_token=args.force)
    elif args.command == "accounts":
        access_token = resolve_alias(data, args.token_or_alias)
        list_accounts(client, access_token)
    elif args.command == "transactions":
        access_token = resolve_alias(data, args.token_or_alias)
        list_transactions(client, access_token)
    elif args.command == "alias":
        add_alias(args.item_id, args.name)
    else:
        raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    _main()
