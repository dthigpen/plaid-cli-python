import argparse
from typing import Iterable
import plaid
from plaid.api import plaid_api

from .settings import (
    load_config,
    load_data,
    save_data,
)
from .linker import run_link_server

from .api import list_accounts, list_transactions

import tabulate

OUTPUT_FORMATS = ("table", "json", "csv")
output_format = "table"


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
    links = data["links"]
    matching_link = next(
        (
            l
            for l in links
            if l["access_token"] == token_or_alias
            or l.get("alias", None) == token_or_alias
        ),
        None,
    )
    if matching_link:
        return matching_link["access_token"]
    else:
        raise ValueError(f"Token or alias does not exist for {token_or_alias}.")


def get_link_data(data: dict, token_or_alias: str) -> str:
    links = data["links"]
    matching_link = next(
        (
            l
            for l in links
            if l["access_token"] == token_or_alias
            or l.get("alias", None) == token_or_alias
        ),
        None,
    )
    if matching_link:
        return matching_link
    else:
        raise ValueError(f"Token or alias does not exist for {token_or_alias}.")


def output_data(data: list, keys: Iterable, default=None):
    rows = map(lambda t: (t.get(k, default) for k in keys), data)
    if output_format == "table":
        print(tabulate.tabulate(rows, keys))
    else:
        raise ValueError(f"Operation not supported: {output_format}")


def add_alias(data: dict, item_id: str, alias_name: str):
    found = False
    for link in data["links"]:
        if link["access_token"] == item_id:
            link["alias"] = alias_name
            found = True
            print(f'Adding alias "{item_id}" for token {item_id}')
            break
        for account in link.get("accounts", []):
            if account["id"] == item_id:
                account["alias"] = alias_name
                print(f'Adding alias "{item_id}" for account {item_id}')
                found = True
                break
    if not found:
        raise ValueError(f"Could not find item with id: {item_id}")
    save_data(data)


def output_accounts(client: plaid_api.PlaidApi, access_token: str):
    accounts = list_accounts(client, access_token)
    header = ("type", "subtype", "name", "account_id")
    output_data(accounts, header)


def output_transactions(client: plaid_api.PlaidApi, access_token: str):
    transactions = list_transactions(client, access_token)

    header = ("date", "amount", "name", "pending")
    output_data(transactions, header)


def output_links(links: list[dict]):
    header = ("access_token", "alias")
    output_data(links, header)


def _main():
    parser = argparse.ArgumentParser("A command line interface for the Plaid API")
    parser.add_argument(
        "-o",
        "--output-format",
        type=str,
        default="table",
        help=f'Format to output the data in, "table" by default. {OUTPUT_FORMATS}',
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    # for linking institutions
    link_parser = subparsers.add_parser("link")
    link_parser.add_argument("alias", type=str, help="Alias for this institution")
    link_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force a new token instead of refreshing the existing token",
    )
    # for printing all linked institutions
    links_parser = subparsers.add_parser("links")
    # for account details
    accounts_parser = subparsers.add_parser("accounts")
    accounts_parser.add_argument("token_or_alias")
    # for transactions
    transactions_parser = subparsers.add_parser("transactions")
    transactions_parser.add_argument("token_or_alias")
    # for adding aliases
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
    elif args.command == "links":
        output_links(data["links"])
    elif args.command == "accounts":
        link_data = get_link_data(data, args.token_or_alias)
        output_accounts(client, link_data["access_token"])
    elif args.command == "transactions":
        link_data = get_link_data(data, args.token_or_alias)
        output_transactions(client, link_data["access_token"])
    elif args.command == "alias":
        add_alias(data, args.item_id, args.name)
    else:
        raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    _main()
