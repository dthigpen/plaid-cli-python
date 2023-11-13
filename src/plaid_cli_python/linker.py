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

from importlib.resources import files

from .settings import (
    load_config,
    load_data,
    save_data,
    DEFAULT_APP_DIR
)
home_html_template_text = (
    files("plaid_cli_python.templates").joinpath("home.html").read_text()
)


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

