# plaid-cli-python

A CLI tool for interacting with the Plaid API, inspired by https://github.com/ebridges/plaid2qif and https://github.com/landakram/plaid-cli

## Installation

Install the Python package

```bash
pip install git+https://github.com/dthigpen/plaid-cli-python
```

Setup your Plaid variables by creating a `.env` file in your working directory or at `~/.plaid-cli-python/.env`

```env
PLAID_ENV="development"
PLAID_CLIENT_ID="<your-client-id>"
PLAID_SECRET="<your-secret"
```

## Usage

Link a financial institution

```
plaid-cli-python link my-bank
```

View accounts for a linked institution

```
$ plaid-cli-python accounts my-bank
type        subtype    name            account_id
----------  ---------  --------------  -------------------------------------
depository  checking   Plaid Checking  7DbD5aGADeILMKMJNJErFvVX3MlxPxF8n9jBN
```

Add an alias for an item, such as an account-id

```
plaid-cli-python alias my-bank <long-account-id> chase_checking
```

View transactions for a given account

```
$ plaid-cli-python transactions --account chase_checking --start 2023-10-08 --end 2023-11-30
date          amount  name                    pending
----------  --------  ----------------------  ---------
2023-11-09      6.33  Uber 072515 SF**POOL**  False
2023-10-27      5.4   Uber 063015 SF**POOL**  False
2023-10-25   -500     United Airlines         False
2023-10-24     12     McDonald's              False
2023-10-24      4.33  Starbucks               False
...
```