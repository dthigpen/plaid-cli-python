import argparse
import json
from pathlib import Path
from typing import Iterable

import plaid
from plaid.api import plaid_api

from importlib.resources import files

from .settings import (
    load_config,
    load_data,
    save_data,
)
from .linker import run_link_server

from .api import list_accounts, list_transactions

home_html_template_text = (
    files("plaid_cli_python.templates").joinpath("home.html").read_text()
)

import tabulate

output_format = "tabular"


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


def output_data(data: dict, keys: Iterable):
    rows = map(lambda t: (t[k] for k in keys), data)
    if output_format == "table" or output_format == "tabular":
        print(tabulate.tabulate(rows, keys))
    else:
        raise ValueError(f"Operation not supported: {output_format}")


def add_alias(item_id: str, alias_name: str):
    data = load_data()
    data["aliases"][alias_name] = item_id
    save_data(data)


def output_accounts(client: plaid_api.PlaidApi, access_token: str):
    accounts = list_accounts(client, access_token)
    header = ("type", "subtype", "name", "account_id")
    output_data(accounts, header)


def output_transactions(client: plaid_api.PlaidApi, access_token: str):
    transactions = list_transactions(client, access_token)

    header = ("date", "amount", "name", "pending")
    output_data(transactions, header)


def _main():
    parser = argparse.ArgumentParser("A command line interface for the Plaid API")
    parser.add_argument(
        "--output-format",
        type=str,
        default="tabular",
        help='Format to output the data in, "tabular" by default. Others include csv,json',
    )
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
    # could get rid of global by passing output options as arg
    global output_format
    output_format = args.output_format
    config = load_config()
    data = load_data()
    client = open_client(config)
    if args.command == "link":
        run_link_server(client, link_alias=args.alias, new_token=args.force)
    elif args.command == "accounts":
        access_token = resolve_alias(data, args.token_or_alias)
        output_accounts(client, access_token)
    elif args.command == "transactions":
        access_token = resolve_alias(data, args.token_or_alias)
        output_transactions(client, access_token)
    elif args.command == "alias":
        add_alias(args.item_id, args.name)
    else:
        raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    _main()
