# plaid-cli-python

A CLI tool for interacting with the Plaid API, inspired by https://github.com/ebridges/plaid2qif and https://github.com/landakram/plaid-cli

## Installation

Install the Python package

```bash
pip install git+https://github.com/dthigpen/plaid-cli-python
```

Setup your Plaid variables by creating the following config file at `~/.plaid-cli-python/config.json`

```json
{
  "PLAID_ENV": "sandbox",
  "PLAID_CLIENT_ID": "<your-client-id>",
  "PLAID_SECRET": "<your-secret",
}
```

## Usage

Link a financial institution

```
python -m plaid-cli-python link my-bank
```

View accounts for a linked institution

```
$ python -m plaid-cli-python accounts my-bank
Account:Subaccount      AccountName     AcctNum AcctID
depository:checking     Plaid Checking  0000    <long-account-id>
```

Add an alias for an item, such as an account-id

```
python -m plaid-cli-python alias <long-account-id> chase_checking
```
