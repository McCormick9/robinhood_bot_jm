import robin_stocks.robinhood as r
import pandas as pd
import numpy as np
import ta as ta
from pandas.plotting import register_matplotlib_converters
from ta import *
from misc import *
from tradingstats import *
from config import *

# Log in to Robinhood
# Put your username and password in a config.py file in the same directory (see sample file)
login = r.login(rh_username,rh_password)

# Safe divide by zero division function
def safe_division(n, d):
    return n / d if d else 0

def get_historicals(ticker, intervalArg, spanArg, boundsArg):
    # If it's a ticker in this program, then it must be a crypto ticker
    history = r.get_crypto_historicals(ticker,interval=intervalArg,span=spanArg,bounds=boundsArg)
    return history

def get_watchlist_symbols():
    """
    Returns: the symbol for each stock in your watchlist as a list of strings
    """
    my_list_names = set()
    symbols = set()

    watchlistInfo = r.get_all_watchlists()
    for watchlist in watchlistInfo['results']:
        listName = watchlist['display_name']
        my_list_names.add(listName)

    for listName in my_list_names:
        watchlist = r.get_watchlist_by_name(name=listName)
        for item in watchlist['results']:
            symbol = item['symbol']
            symbols.add(symbol)

    return symbols

def get_portfolio_symbols():
    """
    Returns: the symbol for each stock in your portfolio as a list of strings
    """
    symbols = []
    holdings_data = r.get_open_stock_positions()
    for item in holdings_data:
        if not item:
            continue
        instrument_data = r.get_instrument_by_url(item.get('instrument'))
        symbol = instrument_data['symbol']
        symbols.append(symbol)
    return symbols

def get_position_creation_date(symbol, holdings_data):
    """Returns the time at which we bought a certain stock in our portfolio

    Args:
        symbol(str): Symbol of the stock that we are trying to figure out when it was bought
        holdings_data(dict): dict returned by r.get_open_stock_positions()

    Returns:
        A string containing the date and time the stock was bought, or "Not found" otherwise
    """
    instrument = r.get_instruments_by_symbols(symbol)
    url = instrument[0].get('url')
    for dict in holdings_data:
        if(dict.get('instrument') == url):
            return dict.get('created_at')
    return "Not found"

def get_modified_holdings():
    """ Retrieves the same dictionary as r.build_holdings, but includes data about
        when the stock was purchased, which is useful for the read_trade_history() method
        in tradingstats.py

    Returns:
        the same dict from r.build_holdings, but with an extra key-value pair for each
        position you have, which is 'bought_at': (the time the stock was purchased)
    """
    holdings = r.build_holdings()
    holdings_data = r.get_open_stock_positions()
    for symbol, dict in holdings.items():
        bought_at = get_position_creation_date(symbol, holdings_data)
        bought_at = str(pd.to_datetime(bought_at))
        holdings[symbol].update({'bought_at': bought_at})
    return holdings

def sell_holdings(symbol, holdings_data):
    """ Place an order to sell all holdings of a stock.

    Args:
        symbol(str): Symbol of the stock we want to sell
        holdings_data(dict): dict obtained from get_modified_holdings() method
    """
    shares_owned = int(float(holdings_data[symbol].get("quantity")))
    if not debug:
        r.order_sell_market(symbol, shares_owned)
    print("####### Selling " + str(shares_owned) + " shares of " + symbol + " #######")

def buy_holdings(potential_buys, profile_data, holdings_data):
    """ Places orders to buy holdings of stocks. This method will try to order
        an appropriate amount of shares such that your holdings of the stock will
        roughly match the average for the rest of your portfoilio. If the share
        price is too high considering the rest of your holdings and the amount of
        buying power in your account, it will not order any shares.

    Args:
        potential_buys(list): List of strings, the strings are the symbols of stocks we want to buy
        symbol(str): Symbol of the stock we want to sell
        holdings_data(dict): dict obtained from r.build_holdings() or get_modified_holdings() method
    """
    cash = float(profile_data.get('cash'))
    portfolio_value = float(profile_data.get('equity')) - cash
    ideal_position_size = (safe_division(portfolio_value, len(holdings_data))+cash/len(potential_buys))/(2 * len(potential_buys))
    prices = r.get_latest_price(potential_buys)
    for i in range(0, len(potential_buys)):
        stock_price = float(prices[i])
        if(ideal_position_size < stock_price < ideal_position_size*1.5):
            num_shares = int(ideal_position_size*1.5/stock_price)
        elif (stock_price < ideal_position_size):
            num_shares = int(ideal_position_size/stock_price)
        else:
            print("####### Tried buying shares of " + potential_buys[i] + ", but not enough buying power to do so#######")
            break
        print("####### Buying " + str(num_shares) + " shares of " + potential_buys[i] + " #######")
        if not debug:
            r.order_buy_market(potential_buys[i], num_shares)



def scan_stocks():
    if debug:
        print("----- DEBUG MODE -----\n")
    print("----- Starting scan... -----\n")
    register_matplotlib_converters()
    watchlist_symbols = get_watchlist_symbols()
    portfolio_symbols = get_portfolio_symbols()
    holdings_data = get_modified_holdings()
    potential_buys = []
    sells = []
    print("Current Portfolio: " + str(portfolio_symbols) + "\n")
    print("Current Watchlist: " + str(watchlist_symbols) + "\n")
    print("----- Scanning portfolio for assets to sell -----\n")
    # Add your own selling logic here

    profile_data = r.build_user_profile()
    print("\n----- Scanning watchlist for assets to buy -----\n")
    # Add your own buying logic here

    if(len(potential_buys) > 0):
        buy_holdings(potential_buys, profile_data, holdings_data)
    if(len(sells) > 0):
        update_trade_history(sells, holdings_data, "tradehistory.txt")
    print("----- Scan over -----\n")
    if debug:
        print("----- DEBUG MODE -----\n")

# Execute the scan
# scan_stocks()
