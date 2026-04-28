import tkinter as tk
from tkinter import simpledialog, Toplevel, Text, Checkbutton, IntVar, ttk, messagebox, font
import requests
import winreg
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta
import numpy as np
import ctypes
import matplotlib.dates as mdates
import sys
import threading
import queue
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import math
import random
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands
import warnings
warnings.filterwarnings('ignore')

# Dateien für Einstellungen
WINDOW_POSITION_FILE = "window_position.txt"
BTC_VALUE_FILE = "btc_value.txt"
THEME_COLOR_FILE = "theme_color.txt"
NOTEBOOK_FILE = "notes.txt"
AVG_PRICE_FILE = "avg_price.txt"
OPTIONS_FILE = "options.txt"
WALLET_ADDRESSES_FILE = "wallet_addresses.txt"
INDICATORS_WINDOW_POS_FILE = "indicators_window_pos.txt"
WALLET_WINDOW_POS_FILE = "wallet_window_pos.txt"
TRADES_FILE = "trades.txt"
PORTFOLIO_WINDOW_POS_FILE = "portfolio_window_pos.txt"
AVG_WINDOW_POS_FILE = "avg_window_pos.txt"

# Define the path to this script for startup
APP_NAME = "BTC Pracker"
APP_PATH = os.path.abspath(__file__)

# Globale Variablen
CURRENCY = "EUR"
preset_colors = ["#DAA520", "#62ffc2", "#62edff", "#ff6294", "#ff7e62"]
custom_colors = ["#F7931A", "#3AF23A", "#D4B461", "#3178C6", "#35B454"] * 5
theme_color = preset_colors[0]
bullish_color = "#82ef82"
bearish_color = "#ff4d4d"
HOVER_COLOR = "#D3D3D3"
HOVER_DARK = "#404040"

# Portfolio Tracker Variablen
trades = []
portfolio_data = {
    'total_invested': 0.0,
    'total_value': 0.0,
    'total_pnl': 0.0,
    'pnl_percentage': 0.0,
    'total_btc': 0.0,
    'avg_buy_price': 0.0,
    'num_trades': 0,
    'winning_trades': 0,
    'losing_trades': 0,
    'largest_win': 0.0,
    'largest_loss': 0.0
}

# Offline-Status Variablen
last_known_price = 0.0
is_online = True
connection_error_count = 0
last_historical_data = []

# IP-Info für Online-Indikator
public_ip = "Unknown"
ip_city = "Unknown"
ip_country = "Unknown"
ip_country_code = ""
ip_flag = ""

# Wallet Tracker Variablen
wallet_addresses = []
wallet_data = {}
wallet_transactions = {}
latest_block_height = 0

# Time ranges for historical data
TIME_RANGES = {
    '1h': {'interval': 1, 'hours': 1},
    '6h': {'interval': 1, 'hours': 6},
    '12h': {'interval': 1, 'hours': 12},
    '24h': {'interval': 1, 'hours': 24},
    '3d': {'interval': 5, 'days': 3},
    '7d': {'interval': 15, 'days': 7},
    '14d': {'interval': 30, 'days': 14},
    '1M': {'interval': 60, 'days': 31},
    '3M': {'interval': 240, 'days': 90},
    '1Y': {'interval': 1440, 'days': 365},
    'ALL': {'interval': 10080, 'all': True}
}

current_time_range = '12h'
last_price = 0.0
last_price_eur = 0.0
last_price_usd = 0.0
rsi_value = 0.0
stoch_rsi_value = 0.0
resistance_level = 0.0
support_level = 0.0
daily_prices_for_indicators = []

# Fees from mempool
fees_next_block = "Loading..."
fees_2_3_blocks = "Loading..."
fees_3_10_blocks = "Loading..."

# Queues für Thread-Kommunikation
price_queue = queue.Queue()
historical_queue = queue.Queue()
fear_greed_queue = queue.Queue()
fx_rate_queue = queue.Queue()
fees_queue = queue.Queue()
market_data_queue = queue.Queue()
wallet_queue = queue.Queue()
block_height_queue = queue.Queue()
ip_info_queue = queue.Queue()

# Thread Pool für API Calls
executor = ThreadPoolExecutor(max_workers=8)

# ====== HOVER FUNCTIONS ======
def on_enter_button(event, button):
    """Hover-Effekt - speichere originale Farbe"""
    if not hasattr(button, 'original_bg'):
        button.original_bg = button.cget('bg')
    button.config(bg=HOVER_COLOR)

def on_leave_button(event, button):
    """Hover-Effekt beenden - stelle originale Farbe wieder her"""
    if hasattr(button, 'original_bg'):
        button.config(bg=button.original_bg)
    else:
        button.config(bg=theme_color)

def on_enter_dark(event, button):
    """Hover-Effekt für dunkle Buttons"""
    if not hasattr(button, 'original_bg'):
        button.original_bg = button.cget('bg')
    button.config(bg=HOVER_DARK)

def on_leave_dark(event, button):
    """Hover-Effekt für dunkle Buttons beenden"""
    if hasattr(button, 'original_bg'):
        button.config(bg=button.original_bg)
    else:
        button.config(bg="#2A2A2A")

# ====== IP-INFO HOLEN ======
def fetch_ip_info_thread():
    """Holt öffentliche IP und Standortinformationen"""
    global public_ip, ip_city, ip_country, ip_country_code, ip_flag
    try:
        url = "https://ipapi.co/json/"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            public_ip = data.get('ip', 'Unknown')
            ip_city = data.get('city', 'Unknown')
            ip_country = data.get('country_name', 'Unknown')
            ip_country_code = data.get('country_code', '').upper()
            
            if ip_country_code and len(ip_country_code) == 2:
                flag = ''.join(chr(127397 + ord(c)) for c in ip_country_code)
                ip_flag = flag
            else:
                ip_flag = "🏳️"
            
            ip_info_queue.put(('ip_info', {
                'ip': public_ip,
                'city': ip_city,
                'country': ip_country,
                'country_code': ip_country_code,
                'flag': ip_flag
            }))
            return
        
        ip_response = requests.get("https://api.ipify.org?format=json", timeout=10)
        if ip_response.status_code == 200:
            public_ip = ip_response.json().get('ip', 'Unknown')
            
            geo_url = f"http://ip-api.com/json/{public_ip}?fields=status,message,city,country,countryCode"
            geo_response = requests.get(geo_url, timeout=10)
            if geo_response.status_code == 200:
                geo_data = geo_response.json()
                if geo_data.get('status') == 'success':
                    ip_city = geo_data.get('city', 'Unknown')
                    ip_country = geo_data.get('country', 'Unknown')
                    ip_country_code = geo_data.get('countryCode', '').upper()
                    
                    if ip_country_code and len(ip_country_code) == 2:
                        ip_flag = ''.join(chr(127397 + ord(c)) for c in ip_country_code)
                    else:
                        ip_flag = "🏳️"
                    
                    ip_info_queue.put(('ip_info', {
                        'ip': public_ip,
                        'city': ip_city,
                        'country': ip_country,
                        'country_code': ip_country_code,
                        'flag': ip_flag
                    }))
                    return
        
        ip_info_queue.put(('ip_info', {
            'ip': public_ip,
            'city': 'Unknown',
            'country': 'Unknown',
            'country_code': '',
            'flag': '🌐'
        }))
        
    except Exception as e:
        print(f"Error fetching IP info: {e}")
        ip_info_queue.put(('ip_info', {
            'ip': 'Error',
            'city': 'Error',
            'country': 'Error',
            'country_code': '',
            'flag': '❌'
        }))

# ====== ATTACHED WINDOW FUNCTIONS ======
def save_attached_window_pos(window_type, x, y):
    """Speichert Position von angehefteten Fenstern"""
    if window_type == 'indicators':
        filename = INDICATORS_WINDOW_POS_FILE
    elif window_type == 'wallet':
        filename = WALLET_WINDOW_POS_FILE
    elif window_type == 'avg':
        filename = AVG_WINDOW_POS_FILE
    else:
        filename = PORTFOLIO_WINDOW_POS_FILE
    try:
        with open(filename, "w") as f:
            f.write(f"{x},{y}")
    except:
        pass

def load_attached_window_pos(window_type):
    """Lädt Position von angehefteten Fenstern"""
    if window_type == 'indicators':
        filename = INDICATORS_WINDOW_POS_FILE
    elif window_type == 'wallet':
        filename = WALLET_WINDOW_POS_FILE
    elif window_type == 'avg':
        filename = AVG_WINDOW_POS_FILE
    else:
        filename = PORTFOLIO_WINDOW_POS_FILE
    
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                x, y = map(int, f.read().strip().split(','))
                return x, y
        except:
            return None, None
    return None, None

# ====== AKTUELLE BLOCKHÖHE HOLEN ======
def fetch_current_block_height_thread():
    """Holt die aktuelle Blockhöhe von Blockchain.com für Confirmations-Berechnung"""
    global latest_block_height
    try:
        url = "https://blockchain.info/q/getblockcount"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            latest_block_height = int(response.text.strip())
            block_height_queue.put(('block_height', latest_block_height))
            return
        
        url = "https://mempool.space/api/blocks/tip/height"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            latest_block_height = int(response.text.strip())
            block_height_queue.put(('block_height', latest_block_height))
            return
            
    except Exception as e:
        print(f"Error fetching block height: {e}")

# ====== WALLET FUNKTIONEN ======
def load_wallet_addresses():
    """Lädt gespeicherte Wallet-Adressen aus Datei"""
    global wallet_addresses
    if os.path.exists(WALLET_ADDRESSES_FILE):
        try:
            with open(WALLET_ADDRESSES_FILE, "r") as f:
                addresses = [line.strip() for line in f.readlines() if line.strip()]
                wallet_addresses = addresses
                return addresses
        except:
            return []
    return []

def save_wallet_addresses():
    """Speichert Wallet-Adressen in Datei"""
    try:
        with open(WALLET_ADDRESSES_FILE, "w") as f:
            for address in wallet_addresses:
                f.write(address + "\n")
    except:
        pass

def fetch_wallet_data_thread(address):
    """Holt Wallet-Daten von Blockchain.com und Mempool.space APIs"""
    global latest_block_height
    try:
        try:
            url = f"https://blockchain.info/rawaddr/{address}?limit=50"
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                tx_count = data.get('n_tx', 0)
                balance = data.get('final_balance', 0) / 100000000
                total_received = data.get('total_received', 0) / 100000000
                total_sent = data.get('total_sent', 0) / 100000000
                
                transactions = []
                for tx in data.get('txs', [])[:20]:
                    txid = tx.get('hash', 'N/A')
                    block_height = tx.get('block_height', 0)
                    
                    if block_height > 0 and latest_block_height > 0:
                        confirmations = latest_block_height - block_height + 1
                    else:
                        confirmations = 0
                    
                    value = 0
                    tx_type = "unknown"
                    
                    inputs_sum = 0
                    for inp in tx.get('inputs', []):
                        if inp.get('prev_out', {}).get('addr', '') == address:
                            inputs_sum += inp.get('prev_out', {}).get('value', 0)
                    
                    outputs_sum = 0
                    for out in tx.get('out', []):
                        if out.get('addr', '') == address:
                            outputs_sum += out.get('value', 0)
                    
                    if outputs_sum > 0 and inputs_sum > 0:
                        value = outputs_sum - inputs_sum
                        tx_type = "self" if abs(value) < 1000 else "mixed"
                    elif outputs_sum > 0:
                        value = outputs_sum
                        tx_type = "incoming"
                    elif inputs_sum > 0:
                        value = -inputs_sum
                        tx_type = "outgoing"
                    
                    value_btc = value / 100000000
                    timestamp = tx.get('time', 0)
                    tx_date = datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M") if timestamp else "N/A"
                    
                    transactions.append({
                        'txid': txid[:10] + "..." + txid[-8:] if len(txid) > 25 else txid,
                        'value': value_btc,
                        'value_sats': value,
                        'confirmations': max(0, confirmations),
                        'block_height': block_height,
                        'time': timestamp,
                        'date': tx_date,
                        'type': tx_type,
                        'is_confirmed': block_height > 0,
                        'inputs_sum': inputs_sum / 100000000,
                        'outputs_sum': outputs_sum / 100000000
                    })
                
                last_tx_date = transactions[0]['date'] if transactions else "N/A"
                
                wallet_queue.put(('wallet_data', {
                    'address': address,
                    'tx_count': tx_count,
                    'balance': balance,
                    'total_received': total_received,
                    'total_sent': total_sent,
                    'last_tx_date': last_tx_date,
                    'transactions': transactions,
                    'source': 'blockchain.com'
                }))
                return
        except Exception as e:
            print(f"Blockchain.com API error for {address}: {e}")
        
        try:
            mempool_url = f"https://mempool.space/api/address/{address}"
            response = requests.get(mempool_url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                chain_stats = data.get('chain_stats', {})
                mempool_stats = data.get('mempool_stats', {})
                
                tx_count = chain_stats.get('tx_count', 0) + mempool_stats.get('tx_count', 0)
                funded_sum = chain_stats.get('funded_txo_sum', 0) + mempool_stats.get('funded_txo_sum', 0)
                spent_sum = chain_stats.get('spent_txo_sum', 0) + mempool_stats.get('spent_txo_sum', 0)
                balance = (funded_sum - spent_sum) / 100000000
                
                txs_url = f"https://mempool.space/api/address/{address}/txs"
                txs_response = requests.get(txs_url, timeout=15)
                
                transactions = []
                if txs_response.status_code == 200:
                    txs_data = txs_response.json()
                    
                    for tx in txs_data[:20]:
                        txid = tx.get('txid', 'N/A')
                        
                        status = tx.get('status', {})
                        block_height = status.get('block_height', 0)
                        is_confirmed = status.get('confirmed', False)
                        
                        if is_confirmed and block_height > 0 and latest_block_height > 0:
                            confirmations = latest_block_height - block_height + 1
                        else:
                            confirmations = 0
                        
                        if is_confirmed and 'block_time' in status:
                            timestamp = status.get('block_time', 0)
                        else:
                            timestamp = time.time()
                        
                        tx_date = datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M")
                        
                        value = 0
                        tx_type = "unknown"
                        
                        inputs_sum = 0
                        for vin in tx.get('vin', []):
                            if vin.get('prevout', {}).get('scriptpubkey_address', '') == address:
                                inputs_sum += vin.get('prevout', {}).get('value', 0)
                        
                        outputs_sum = 0
                        for vout in tx.get('vout', []):
                            if vout.get('scriptpubkey_address', '') == address:
                                outputs_sum += vout.get('value', 0)
                        
                        if outputs_sum > 0 and inputs_sum > 0:
                            value = (outputs_sum - inputs_sum) / 100000000
                            tx_type = "self"
                        elif outputs_sum > 0:
                            value = outputs_sum / 100000000
                            tx_type = "incoming"
                        elif inputs_sum > 0:
                            value = -inputs_sum / 100000000
                            tx_type = "outgoing"
                        
                        transactions.append({
                            'txid': txid[:10] + "..." + txid[-8:] if len(txid) > 25 else txid,
                            'value': value,
                            'confirmations': confirmations,
                            'block_height': block_height,
                            'time': timestamp,
                            'date': tx_date,
                            'type': tx_type,
                            'is_confirmed': is_confirmed,
                            'inputs_sum': inputs_sum / 100000000,
                            'outputs_sum': outputs_sum / 100000000
                        })
                
                last_tx_date = transactions[0]['date'] if transactions else "N/A"
                
                wallet_queue.put(('wallet_data', {
                    'address': address,
                    'tx_count': tx_count,
                    'balance': balance,
                    'last_tx_date': last_tx_date,
                    'transactions': transactions,
                    'source': 'mempool.space'
                }))
                return
        except Exception as e:
            print(f"Mempool.space API error for {address}: {e}")
        
        wallet_queue.put(('wallet_error', address))
            
    except Exception as e:
        print(f"Error fetching wallet {address}: {e}")
        wallet_queue.put(('wallet_error', address))

def update_all_wallets():
    """Aktualisiert Daten für alle gespeicherten Wallets"""
    executor.submit(fetch_current_block_height_thread)
    time.sleep(0.5)
    
    for address in wallet_addresses:
        executor.submit(fetch_wallet_data_thread, address)

# ====== WALLET TRACKER WINDOW ======
class WalletTracker:
    def __init__(self, parent):
        self.parent = parent
        self.is_expanded = False
        self.expanded_window = None
        self.update_id = None
        self.current_selected_address = None
        
        self.wallet_button = tk.Button(parent, text="Wallets", command=self.toggle_expand,
                                      bg=theme_color, fg="black", font=("Arial", 10), width=6)
        self.wallet_button.place(x=10, y=415)
        
        self.wallet_button.bind("<Enter>", lambda e, b=self.wallet_button: on_enter_button(e, b))
        self.wallet_button.bind("<Leave>", lambda e, b=self.wallet_button: on_leave_button(e, b))
        
        load_wallet_addresses()
    
    def toggle_expand(self):
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()
    
    def expand(self):
        self.is_expanded = True
        
        self.expanded_window = tk.Toplevel(self.parent)
        self.expanded_window.overrideredirect(1)
        self.expanded_window.attributes('-topmost', True)
        self.expanded_window.config(bg="#212121")
        
        saved_x, saved_y = load_attached_window_pos('wallet')
        if saved_x is not None and saved_y is not None:
            self.expanded_window.geometry(f"700x650+{saved_x}+{saved_y}")
        else:
            main_x = self.parent.winfo_x()
            main_y = self.parent.winfo_y()
            self.expanded_window.geometry(f"700x650+{main_x-700}+{main_y}")
        
        movebar = tk.Frame(self.expanded_window, bg="#2A2A2A", height=30)
        movebar.pack(fill="x", side="top")
        movebar.pack_propagate(False)
        
        movebar_title = tk.Label(movebar, text="Wallet Tracker", 
                                bg="#2A2A2A", fg=theme_color, 
                                font=("Arial", 12, "bold"))
        movebar_title.pack(side="left", padx=10, pady=5)
        
        close_button = tk.Button(movebar, text="✕", command=self.collapse,
                                bg="#2A2A2A", fg="white", bd=0,
                                font=("Arial", 12, "bold"))
        close_button.pack(side="right", padx=10, pady=5)
        
        def on_drag_start(event):
            self.expanded_window.x = event.x
            self.expanded_window.y = event.y

        def on_drag_motion(event):
            deltax = event.x - self.expanded_window.x
            deltay = event.y - self.expanded_window.y
            x = self.expanded_window.winfo_x() + deltax
            y = self.expanded_window.winfo_y() + deltay
            self.expanded_window.geometry(f"+{x}+{y}")

        movebar.bind("<Button-1>", on_drag_start)
        movebar.bind("<B1-Motion>", on_drag_motion)
        movebar_title.bind("<Button-1>", on_drag_start)
        movebar_title.bind("<B1-Motion>", on_drag_motion)
        
        close_button.bind("<Enter>", lambda e: close_button.config(bg="#BD5959"))
        close_button.bind("<Leave>", lambda e: close_button.config(bg="#2A2A2A"))
        
        main_container = tk.Frame(self.expanded_window, bg="#212121")
        main_container.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        add_wallet_frame = tk.Frame(main_container, bg="#212121")
        add_wallet_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(add_wallet_frame, text="Add Bitcoin Address:", bg="#212121", 
                fg="white", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 5))
        
        entry_frame = tk.Frame(add_wallet_frame, bg="#212121")
        entry_frame.pack(fill="x")
        
        self.address_entry = tk.Entry(entry_frame, bg="#2A2A2A", fg="white", 
                                     insertbackground="white", font=("Arial", 10))
        self.address_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        add_button = tk.Button(entry_frame, text="Add Wallet", 
                              command=self.add_wallet_address,
                              bg=theme_color, fg="black", font=("Arial", 10), width=12)
        add_button.pack(side="right")
        
        columns_frame = tk.Frame(main_container, bg="#212121")
        columns_frame.pack(fill="both", expand=True)
        
        left_column = tk.Frame(columns_frame, bg="#212121", width=260)
        left_column.pack(side="left", fill="both", expand=False, padx=(0, 10))
        left_column.pack_propagate(False)
        
        tk.Label(left_column, text="Your Wallets", bg="#212121", 
                fg="white", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 8))
        
        wallet_list_container = tk.Frame(left_column, bg="#212121")
        wallet_list_container.pack(fill="both", expand=True)
        
        self.wallet_canvas = tk.Canvas(wallet_list_container, bg="#212121", 
                                      highlightthickness=0)
        wallet_scrollbar = tk.Scrollbar(wallet_list_container, orient="vertical", 
                                       command=self.wallet_canvas.yview)
        self.scrollable_frame = tk.Frame(self.wallet_canvas, bg="#212121")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.wallet_canvas.configure(scrollregion=self.wallet_canvas.bbox("all"))
        )
        
        self.wallet_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.wallet_canvas.configure(yscrollcommand=wallet_scrollbar.set)
        
        self.wallet_canvas.pack(side="left", fill="both", expand=True)
        wallet_scrollbar.pack(side="right", fill="y")
        
        right_column = tk.Frame(columns_frame, bg="#212121", width=380)
        right_column.pack(side="right", fill="both", expand=True)
        right_column.pack_propagate(False)
        
        tk.Label(right_column, text="Transaction History", bg="#212121", 
                fg="white", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 8))
        
        self.selected_wallet_frame = tk.Frame(right_column, bg="#2A2A2A", 
                                             highlightbackground="#444444", 
                                             highlightthickness=1, height=70)
        self.selected_wallet_frame.pack(fill="x", pady=(0, 10))
        self.selected_wallet_frame.pack_propagate(False)
        
        self.selected_wallet_label = tk.Label(self.selected_wallet_frame, 
                                             text="Select a wallet to view transactions", 
                                             bg="#2A2A2A", fg="grey", 
                                             font=("Arial", 10))
        self.selected_wallet_label.pack(expand=True)
        
        tx_list_container = tk.Frame(right_column, bg="#212121")
        tx_list_container.pack(fill="both", expand=True)
        
        self.tx_canvas = tk.Canvas(tx_list_container, bg="#212121", 
                                  highlightthickness=0)
        tx_scrollbar = tk.Scrollbar(tx_list_container, orient="vertical", 
                                   command=self.tx_canvas.yview)
        self.tx_scrollable_frame = tk.Frame(self.tx_canvas, bg="#212121")
        
        self.tx_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.tx_canvas.configure(scrollregion=self.tx_canvas.bbox("all"))
        )
        
        self.tx_canvas.create_window((0, 0), window=self.tx_scrollable_frame, anchor="nw")
        self.tx_canvas.configure(yscrollcommand=tx_scrollbar.set)
        
        self.tx_canvas.pack(side="left", fill="both", expand=True)
        tx_scrollbar.pack(side="right", fill="y")
        
        status_frame = tk.Frame(main_container, bg="#212121", height=40)
        status_frame.pack(fill="x", side="bottom", pady=(10, 0))
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(status_frame, text="● Ready", 
                                    bg="#212121", fg="#82ef82", font=("Arial", 10))
        self.status_label.pack(side="left")
        
        self.total_balance_label = tk.Label(status_frame, 
                                           text="Total Balance: 0.00000000 BTC", 
                                           bg="#212121", fg=theme_color, 
                                           font=("Arial", 11, "bold"))
        self.total_balance_label.pack(side="left", padx=(20, 0))
        
        self.block_height_label = tk.Label(status_frame, 
                                          text="Block: ---", 
                                          bg="#212121", fg="grey", 
                                          font=("Arial", 9))
        self.block_height_label.pack(side="left", padx=(20, 0))
        
        update_button = tk.Button(status_frame, text="Update", 
                                 command=self.update_all_wallets,
                                 bg=theme_color, fg="black", font=("Arial", 10), 
                                 width=10)
        update_button.pack(side="right")
        
        add_button.bind("<Enter>", lambda e, b=add_button: on_enter_button(e, b))
        add_button.bind("<Leave>", lambda e, b=add_button: on_leave_button(e, b))
        update_button.bind("<Enter>", lambda e, b=update_button: on_enter_button(e, b))
        update_button.bind("<Leave>", lambda e, b=update_button: on_leave_button(e, b))
        
        self.load_wallets_to_ui()
        self.schedule_updates()
    
    def add_wallet_address(self):
        address = self.address_entry.get().strip()
        
        if not address:
            return
        
        if not (address.startswith('1') or address.startswith('3') or 
                address.startswith('bc1') or address.startswith('bc1q')):
            self.status_label.config(text="● Invalid address format", fg="#ff4d4d")
            return
        
        if address not in wallet_addresses:
            wallet_addresses.append(address)
            save_wallet_addresses()
            
            self.address_entry.delete(0, tk.END)
            self.load_wallets_to_ui()
            executor.submit(fetch_wallet_data_thread, address)
            self.status_label.config(text="● Address added", fg="#82ef82")
        else:
            self.status_label.config(text="● Address already exists", fg="#ffb84d")
    
    def load_wallets_to_ui(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        if not wallet_addresses:
            empty_label = tk.Label(self.scrollable_frame, 
                                  text="No wallets added yet.\nAdd a Bitcoin address above.", 
                                  bg="#212121", fg="grey", font=("Arial", 11))
            empty_label.pack(pady=30)
            return
        
        for address in wallet_addresses:
            wallet_card = tk.Frame(self.scrollable_frame, bg="#2A2A2A", 
                                  highlightbackground="#444444", 
                                  highlightthickness=1)
            wallet_card.pack(fill="x", padx=5, pady=3)
            
            wallet_card.bind("<Button-1>", lambda e, addr=address: self.select_wallet(addr))
            
            header_frame = tk.Frame(wallet_card, bg="#2A2A2A")
            header_frame.pack(fill="x", padx=8, pady=(8, 2))
            header_frame.bind("<Button-1>", lambda e, addr=address: self.select_wallet(addr))
            
            short_address = address[:12] + "..." + address[-8:] if len(address) > 25 else address
            
            address_label = tk.Label(header_frame, text=short_address, 
                                    bg="#2A2A2A", fg="white", 
                                    font=("Arial", 10, "bold"))
            address_label.pack(side="left")
            address_label.bind("<Button-1>", lambda e, addr=address: self.select_wallet(addr))
            
            delete_button = tk.Button(header_frame, text="✕", 
                                     command=lambda addr=address: self.delete_wallet(addr),
                                     bg="#BD5959", fg="white", 
                                     font=("Arial", 8, "bold"), width=2, height=1,
                                     bd=0)
            delete_button.pack(side="right")
            
            delete_button.bind("<Enter>", lambda e, b=delete_button: on_enter_button(e, b))
            delete_button.bind("<Leave>", lambda e, b=delete_button: on_leave_button(e, b))
            
            content_frame = tk.Frame(wallet_card, bg="#2A2A2A")
            content_frame.pack(fill="x", padx=8, pady=(0, 8))
            content_frame.bind("<Button-1>", lambda e, addr=address: self.select_wallet(addr))
            
            if address in wallet_data:
                data = wallet_data[address]
                
                balance_text = f"Balance: {data['balance']:.8f} BTC"
                balance_label = tk.Label(content_frame, text=balance_text, 
                                        bg="#2A2A2A", fg="#F7931A", 
                                        font=("Arial", 10, "bold"))
                balance_label.pack(anchor="w", pady=(0, 2))
                balance_label.bind("<Button-1>", lambda e, addr=address: self.select_wallet(addr))
                
                pending_txs = sum(1 for tx in data.get('transactions', []) if tx.get('confirmations', 0) < 3)
                incoming_txs = sum(1 for tx in data.get('transactions', []) if tx.get('type') == 'incoming')
                outgoing_txs = sum(1 for tx in data.get('transactions', []) if tx.get('type') == 'outgoing')
                
                tx_text = f"TX: {data['tx_count']} total"
                if incoming_txs > 0 or outgoing_txs > 0:
                    tx_text += f"  |  ↓{incoming_txs}  ↑{outgoing_txs}"
                if pending_txs > 0:
                    tx_text += f"  •  {pending_txs} pending"
                    tx_color = "#ffb84d"
                else:
                    tx_color = "grey"
                
                tx_label = tk.Label(content_frame, text=tx_text, 
                                   bg="#2A2A2A", fg=tx_color, 
                                   font=("Arial", 9))
                tx_label.pack(anchor="w")
                tx_label.bind("<Button-1>", lambda e, addr=address: self.select_wallet(addr))
                
                last_tx_label = tk.Label(content_frame, text=f"Last: {data['last_tx_date']}", 
                                        bg="#2A2A2A", fg="grey", 
                                        font=("Arial", 8))
                last_tx_label.pack(anchor="w", pady=(2, 0))
                last_tx_label.bind("<Button-1>", lambda e, addr=address: self.select_wallet(addr))
                
                if 'source' in data:
                    source_label = tk.Label(content_frame, text=f"via {data['source']}", 
                                          bg="#2A2A2A", fg="#444444", 
                                          font=("Arial", 7))
                    source_label.pack(anchor="w")
            else:
                loading_label = tk.Label(content_frame, text="Loading wallet data...", 
                                        bg="#2A2A2A", fg="grey", 
                                        font=("Arial", 9))
                loading_label.pack(anchor="w", pady=5)
                loading_label.bind("<Button-1>", lambda e, addr=address: self.select_wallet(addr))
    
    def select_wallet(self, address):
        self.current_selected_address = address
        
        for widget in self.selected_wallet_frame.winfo_children():
            widget.destroy()
        
        if address in wallet_data:
            data = wallet_data[address]
            short_address = address[:16] + "..." + address[-10:] if len(address) > 30 else address
            
            addr_label = tk.Label(self.selected_wallet_frame, text=short_address, 
                                 bg="#2A2A2A", fg="white", 
                                 font=("Arial", 10, "bold"))
            addr_label.pack(anchor="w", padx=10, pady=(5, 2))
            
            stats_frame = tk.Frame(self.selected_wallet_frame, bg="#2A2A2A")
            stats_frame.pack(anchor="w", padx=10, fill="x")
            
            balance_label = tk.Label(stats_frame, 
                                    text=f"Balance: {data['balance']:.8f} BTC", 
                                    bg="#2A2A2A", fg="#F7931A", 
                                    font=("Arial", 10, "bold"))
            balance_label.pack(side="left")
            
            if 'transactions' in data:
                incoming = sum(1 for tx in data['transactions'] if tx.get('type') == 'incoming')
                outgoing = sum(1 for tx in data['transactions'] if tx.get('type') == 'outgoing')
                
                stats_text = f"  |  ↓{incoming}  ↑{outgoing}"
                stats_label = tk.Label(stats_frame, text=stats_text,
                                      bg="#2A2A2A", fg="grey",
                                      font=("Arial", 9))
                stats_label.pack(side="left", padx=(10, 0))
            
            if 'source' in data:
                source_label = tk.Label(self.selected_wallet_frame, 
                                       text=f"Data source: {data['source']}", 
                                       bg="#2A2A2A", fg="#444444", 
                                       font=("Arial", 7))
                source_label.pack(anchor="w", padx=10, pady=(0, 5))
        else:
            loading_label = tk.Label(self.selected_wallet_frame, 
                                    text="Loading wallet data...", 
                                    bg="#2A2A2A", fg="grey", 
                                    font=("Arial", 11))
            loading_label.pack(expand=True)
        
        self.load_transactions(address)
    
    def load_transactions(self, address):
        for widget in self.tx_scrollable_frame.winfo_children():
            widget.destroy()
        
        if address not in wallet_data or 'transactions' not in wallet_data[address]:
            no_tx_label = tk.Label(self.tx_scrollable_frame, 
                                  text="No transaction data available", 
                                  bg="#212121", fg="grey", 
                                  font=("Arial", 11))
            no_tx_label.pack(pady=30)
            return
        
        transactions = wallet_data[address].get('transactions', [])
        
        if not transactions:
            no_tx_label = tk.Label(self.tx_scrollable_frame, 
                                  text="No transactions found for this wallet", 
                                  bg="#212121", fg="grey", 
                                  font=("Arial", 11))
            no_tx_label.pack(pady=30)
            return
        
        transactions.sort(key=lambda x: x.get('time', 0), reverse=True)
        
        for tx in transactions[:20]:
            tx_card = tk.Frame(self.tx_scrollable_frame, bg="#2A2A2A", 
                              highlightbackground="#444444", highlightthickness=1)
            tx_card.pack(fill="x", padx=5, pady=3)
            
            header_frame = tk.Frame(tx_card, bg="#2A2A2A")
            header_frame.pack(fill="x", padx=8, pady=(8, 2))
            
            txid_label = tk.Label(header_frame, text=f"TX: {tx['txid']}", 
                                 bg="#2A2A2A", fg="#62edff", 
                                 font=("Arial", 8, "bold"))
            txid_label.pack(side="left")
            
            tx_type = tx.get('type', 'unknown')
            if tx_type == 'incoming':
                type_text = "↓ INCOMING"
                type_color = "#82ef82"
            elif tx_type == 'outgoing':
                type_text = "↑ OUTGOING"
                type_color = "#ff4d4d"
            elif tx_type == 'self':
                type_text = "↻ SELF"
                type_color = "#62edff"
            else:
                type_text = "• MIXED"
                type_color = "#ffb84d"
            
            type_label = tk.Label(header_frame, text=type_text, 
                                 bg="#2A2A2A", fg=type_color, 
                                 font=("Arial", 8, "bold"))
            type_label.pack(side="right")
            
            value_frame = tk.Frame(tx_card, bg="#2A2A2A")
            value_frame.pack(fill="x", padx=8, pady=2)
            
            value = tx.get('value', 0)
            value_color = "#82ef82" if value > 0 else "#ff4d4d"
            value_sign = "+" if value > 0 else ""
            value_text = f"{value_sign}{value:.8f} BTC"
            
            value_label = tk.Label(value_frame, text=value_text, 
                                  bg="#2A2A2A", fg=value_color, 
                                  font=("Arial", 10, "bold"))
            value_label.pack(anchor="w")
            
            conf_frame = tk.Frame(tx_card, bg="#2A2A2A")
            conf_frame.pack(fill="x", padx=8, pady=2)
            
            conf = tx.get('confirmations', 0)
            block_height = tx.get('block_height', 0)
            
            if conf >= 6:
                conf_color = "#82ef82"
                conf_text = f"✓ {conf} confirmations (fully confirmed)"
            elif conf >= 3:
                conf_color = "#62edff"
                conf_text = f"🔄 {conf} confirmations"
            elif conf >= 1:
                conf_color = "#ffb84d"
                conf_text = f"⏳ {conf} confirmation{'s' if conf > 1 else ''}"
            else:
                if block_height > 0:
                    conf_color = "#ffb84d"
                    conf_text = "⏳ In mempool (pending)"
                else:
                    conf_color = "#ff4d4d"
                    conf_text = "⚠️ Unconfirmed (in mempool)"
            
            conf_label = tk.Label(conf_frame, text=conf_text, 
                                 bg="#2A2A2A", fg=conf_color, 
                                 font=("Arial", 8))
            conf_label.pack(anchor="w")
            
            if block_height > 0:
                block_label = tk.Label(conf_frame, text=f"Block: {block_height}", 
                                      bg="#2A2A2A", fg="#444444", 
                                      font=("Arial", 7))
                block_label.pack(anchor="w")
            
            date_label = tk.Label(tx_card, text=tx['date'], 
                                 bg="#2A2A2A", fg="grey", 
                                 font=("Arial", 8))
            date_label.pack(anchor="w", padx=8, pady=(0, 8))
    
    def delete_wallet(self, address):
        if address in wallet_addresses:
            wallet_addresses.remove(address)
            save_wallet_addresses()
            
            if address in wallet_data:
                del wallet_data[address]
            if address in wallet_transactions:
                del wallet_transactions[address]
            
            if self.current_selected_address == address:
                self.current_selected_address = None
                for widget in self.selected_wallet_frame.winfo_children():
                    widget.destroy()
                empty_label = tk.Label(self.selected_wallet_frame, 
                                      text="Select a wallet to view transactions", 
                                      bg="#2A2A2A", fg="grey", 
                                      font=("Arial", 11))
                empty_label.pack(expand=True)
                
                for widget in self.tx_scrollable_frame.winfo_children():
                    widget.destroy()
            
            self.load_wallets_to_ui()
            self.update_total_balance()
            self.status_label.config(text=f"● Wallet deleted", fg="#ff4d4d")
    
    def update_all_wallets(self):
        self.status_label.config(text="● Updating wallets...", fg="#ffb84d")
        update_all_wallets()
    
    def update_block_height_display(self):
        if latest_block_height > 0:
            self.block_height_label.config(text=f"Block: {latest_block_height:,}")
    
    def schedule_updates(self):
        if self.is_expanded and self.expanded_window:
            self.update_id = self.expanded_window.after(300000, self.schedule_updates)
            self.update_all_wallets()
    
    def update_wallet_display(self):
        self.load_wallets_to_ui()
        self.update_total_balance()
        self.update_block_height_display()
        
        if self.current_selected_address and self.current_selected_address in wallet_data:
            self.select_wallet(self.current_selected_address)
        
        self.status_label.config(text="● Updated", fg="#82ef82")
    
    def update_total_balance(self):
        total_balance = 0.0
        for address in wallet_addresses:
            if address in wallet_data:
                total_balance += wallet_data[address]['balance']
        
        self.total_balance_label.config(text=f"Total Balance: {total_balance:.8f} BTC")
    
    def collapse(self):
        self.is_expanded = False
        self.wallet_button.config(text="Wallets")
        
        if self.expanded_window:
            try:
                x = self.expanded_window.winfo_x()
                y = self.expanded_window.winfo_y()
                save_attached_window_pos('wallet', x, y)
            except:
                pass
            
            if self.update_id:
                self.expanded_window.after_cancel(self.update_id)
            
            self.expanded_window.destroy()
            self.expanded_window = None

# ====== AVG CALCULATOR WINDOW ======
class AVGCalculator:
    def __init__(self, parent):
        self.parent = parent
        self.is_expanded = False
        self.expanded_window = None
        self.update_id = None
        
        # AVG Button - Position über dem P/L Button (y=385 statt 415)
        self.avg_button = tk.Button(parent, text="AVG", command=self.toggle_expand,
                                    bg=theme_color, fg="black", font=("Arial", 10), width=3)
        self.avg_button.place(x=75, y=380)
        
        self.avg_button.bind("<Enter>", lambda e, b=self.avg_button: on_enter_button(e, b))
        self.avg_button.bind("<Leave>", lambda e, b=self.avg_button: on_leave_button(e, b))
        
        # Daten für den Calculator
        self.data_file = "btc_transactions.txt"
        self.currencies = {
            'EUR': '€',
            'USD': '$',
            'CHF': 'Fr',
            'GBP': '£',
            'JPY': '¥',
            'CAD': 'C$',
            'AUD': 'A$'
        }
        self.current_currency = 'EUR'
        self.currency_symbol = '€'
        self.last_result = None
        self.current_market_price = last_known_price  # Aktueller Marktpreis
    
    def toggle_expand(self):
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()
    
    def expand(self):
        self.is_expanded = True
        self.avg_button.config(text="✕")
        
        self.expanded_window = tk.Toplevel(self.parent)
        self.expanded_window.overrideredirect(1)
        self.expanded_window.attributes('-topmost', True)
        self.expanded_window.config(bg="#212121")
        
        # Fenstergröße - ohne Scrollbar
        window_width = 550
        window_height = 700  # Etwas größer für die neuen Felder
        
        # Gespeicherte Position laden
        saved_x, saved_y = load_attached_window_pos('avg')
        if saved_x is not None and saved_y is not None:
            self.expanded_window.geometry(f"{window_width}x{window_height}+{saved_x}+{saved_y}")
        else:
            main_x = self.parent.winfo_x()
            main_y = self.parent.winfo_y()
            self.expanded_window.geometry(f"{window_width}x{window_height}+{main_x-window_width}+{main_y}")
        
        # Movebar
        movebar = tk.Frame(self.expanded_window, bg="#2A2A2A", height=35, cursor="fleur")
        movebar.pack(fill="x", side="top")
        movebar.pack_propagate(False)
        
        title_label = tk.Label(movebar, text="📊 BTC Average Price Calculator", 
                               bg="#2A2A2A", fg=theme_color, 
                               font=("Arial", 12, "bold"))
        title_label.pack(side="left", padx=15, pady=5)
        
        # Currency Toggle
        currency_frame = tk.Frame(movebar, bg="#2A2A2A")
        currency_frame.pack(side="left", padx=20)
        
        self.currency_var = tk.StringVar(value=self.current_currency)
        eur_radio = tk.Radiobutton(currency_frame, text="€ EUR", variable=self.currency_var, value="EUR",
                                  bg="#2A2A2A", fg="white", selectcolor=theme_color,
                                  command=self.change_currency)
        eur_radio.pack(side="left")
        
        usd_radio = tk.Radiobutton(currency_frame, text="$ USD", variable=self.currency_var, value="USD",
                                  bg="#2A2A2A", fg="white", selectcolor=theme_color,
                                  command=self.change_currency)
        usd_radio.pack(side="left", padx=(10,0))
        
        # Refresh Price Button
        refresh_price_btn = tk.Button(movebar, text="🔄", command=self.refresh_market_price,
                                      bg="#2A2A2A", fg=theme_color, bd=0,
                                      font=("Arial", 12), cursor="hand2")
        refresh_price_btn.pack(side="left", padx=5)
        refresh_price_btn.bind("<Enter>", lambda e: refresh_price_btn.config(bg=HOVER_DARK))
        refresh_price_btn.bind("<Leave>", lambda e: refresh_price_btn.config(bg="#2A2A2A"))
        
        close_button = tk.Button(movebar, text="✕", command=self.collapse,
                                bg="#2A2A2A", fg="white", bd=0,
                                font=("Arial", 14, "bold"))
        close_button.pack(side="right", padx=15, pady=5)
        
        # Drag-Funktionalität
        def on_drag_start(event):
            self.expanded_window.x = event.x
            self.expanded_window.y = event.y

        def on_drag_motion(event):
            deltax = event.x - self.expanded_window.x
            deltay = event.y - self.expanded_window.y
            x = self.expanded_window.winfo_x() + deltax
            y = self.expanded_window.winfo_y() + deltay
            self.expanded_window.geometry(f"+{x}+{y}")

        movebar.bind("<Button-1>", on_drag_start)
        movebar.bind("<B1-Motion>", on_drag_motion)
        title_label.bind("<Button-1>", on_drag_start)
        title_label.bind("<B1-Motion>", on_drag_motion)
        
        close_button.bind("<Enter>", lambda e: close_button.config(bg="#BD5959"))
        close_button.bind("<Leave>", lambda e: close_button.config(bg="#2A2A2A"))
        
        # Hauptcontainer - ohne Scrollbar
        main_frame = tk.Frame(self.expanded_window, bg="#212121")
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # UI erstellen
        self.create_ui(main_frame)
        
        # Marktpreis initial laden
        self.refresh_market_price()
    
    def refresh_market_price(self):
        """Aktualisiert den aktuellen Marktpreis"""
        global last_known_price
        self.current_market_price = last_known_price
        self.update_market_price_display()
    
    def update_market_price_display(self):
        """Aktualisiert die Anzeige des Marktpreises"""
        if hasattr(self, 'market_price_label'):
            symbol = self.currency_symbol
            if self.current_market_price > 0:
                self.market_price_label.config(
                    text=f"Current Market Price: {symbol}{self.current_market_price:.2f}",
                    fg=theme_color
                )
            else:
                self.market_price_label.config(text="Current Market Price: Loading...", fg="grey")
    
    def change_currency(self):
        """Ändert die Währung"""
        self.current_currency = self.currency_var.get()
        self.currency_symbol = self.currencies[self.current_currency]
        self.update_display()
        self.update_market_price_display()
        self.update_current_value()
    
    def create_ui(self, parent):
        """Erstellt die Benutzeroberfläche ohne Scrollbar"""
        # Market Price Display
        market_frame = tk.Frame(parent, bg="#212121")
        market_frame.pack(fill="x", pady=(0, 10))
        
        self.market_price_label = tk.Label(market_frame, text="Current Market Price: Loading...", 
                                           bg="#212121", fg="grey", 
                                           font=("Arial", 10, "bold"))
        self.market_price_label.pack()
        
        # Current Position Frame
        current_frame = tk.LabelFrame(parent, text="Current BTC Position", 
                                      bg="#212121", fg="white", 
                                      font=("Arial", 11, "bold"),
                                      padx=10, pady=10)
        current_frame.pack(fill="x", pady=(0, 15))
        
        # BTC Amount
        tk.Label(current_frame, text="BTC Amount:", bg="#212121", fg="grey",
                font=("Arial", 10)).grid(row=0, column=0, sticky="w", pady=5)
        self.btc_amount_entry = self.create_entry(current_frame)
        self.btc_amount_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # Average Purchase Price
        tk.Label(current_frame, text="Avg Price per BTC:", bg="#212121", fg="grey",
                font=("Arial", 10)).grid(row=1, column=0, sticky="w", pady=5)
        self.avg_price_entry = self.create_entry(current_frame)
        self.avg_price_entry.grid(row=1, column=1, padx=10, pady=5)
        
        # Investment Value (basierend auf Durchschnittspreis)
        tk.Label(current_frame, text="Investment Value:", bg="#212121", fg="grey",
                font=("Arial", 10)).grid(row=2, column=0, sticky="w", pady=5)
        self.investment_value_label = tk.Label(current_frame, text="0.00", 
                                               bg="#212121", fg="#888888",
                                               font=("Arial", 10, "bold"))
        self.investment_value_label.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        # Current Market Value (basierend auf aktuellem Marktpreis)
        tk.Label(current_frame, text="Current Market Value:", bg="#212121", fg="grey",
                font=("Arial", 10)).grid(row=3, column=0, sticky="w", pady=5)
        self.market_value_label = tk.Label(current_frame, text="0.00", 
                                           bg="#212121", fg=theme_color,
                                           font=("Arial", 10, "bold"))
        self.market_value_label.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        
        # Unrealized P/L
        tk.Label(current_frame, text="Unrealized P/L:", bg="#212121", fg="grey",
                font=("Arial", 10)).grid(row=4, column=0, sticky="w", pady=5)
        self.unrealized_pl_label = tk.Label(current_frame, text="0.00 (0.00%)", 
                                            bg="#212121", fg="white",
                                            font=("Arial", 10, "bold"))
        self.unrealized_pl_label.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        
        # New Purchase Frame
        buy_frame = tk.LabelFrame(parent, text="New BTC Purchase", 
                                  bg="#212121", fg="white", 
                                  font=("Arial", 11, "bold"),
                                  padx=10, pady=10)
        buy_frame.pack(fill="x", pady=(0, 15))
        
        # Additional BTC
        tk.Label(buy_frame, text="Additional BTC:", bg="#212121", fg="grey",
                font=("Arial", 10)).grid(row=0, column=0, sticky="w", pady=5)
        self.additional_btc_entry = self.create_entry(buy_frame)
        self.additional_btc_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # Purchase Price per BTC
        tk.Label(buy_frame, text="Purchase Price:", bg="#212121", fg="grey",
                font=("Arial", 10)).grid(row=1, column=0, sticky="w", pady=5)
        self.buy_price_entry = self.create_entry(buy_frame)
        self.buy_price_entry.grid(row=1, column=1, padx=10, pady=5)
        
        # Total Cost of Purchase
        tk.Label(buy_frame, text="Total Cost:", bg="#212121", fg="grey",
                font=("Arial", 10)).grid(row=2, column=0, sticky="w", pady=5)
        self.total_cost_label = tk.Label(buy_frame, text="0.00", 
                                        bg="#212121", fg=theme_color,
                                        font=("Arial", 11, "bold"))
        self.total_cost_label.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        # Button Frame
        button_frame = tk.Frame(buy_frame, bg="#212121")
        button_frame.grid(row=3, column=0, columnspan=2, pady=15)
        
        calculate_btn = tk.Button(button_frame, text="Calculate Average", 
                                 command=self.calculate_new_average,
                                 bg=theme_color, fg="black", font=("Arial", 10),
                                 padx=10, relief="flat", cursor="hand2")
        calculate_btn.pack(side="left", padx=5)
        
        save_btn = tk.Button(button_frame, text="Save Transaction", 
                            command=self.save_transaction,
                            bg="#2A2A2A", fg="white", font=("Arial", 10),
                            padx=10, relief="flat", cursor="hand2")
        save_btn.pack(side="left", padx=5)
        
        # Hover-Effekte
        calculate_btn.bind("<Enter>", lambda e, b=calculate_btn: on_enter_button(e, b))
        calculate_btn.bind("<Leave>", lambda e, b=calculate_btn: on_leave_button(e, b))
        save_btn.bind("<Enter>", lambda e, b=save_btn: on_enter_dark(e, b))
        save_btn.bind("<Leave>", lambda e, b=save_btn: on_leave_dark(e, b))
        
        # Live updates
        self.additional_btc_entry.bind('<KeyRelease>', self.update_total_cost)
        self.buy_price_entry.bind('<KeyRelease>', self.update_total_cost)
        
        # Result Frame
        result_frame = tk.LabelFrame(parent, text="Result", 
                                     bg="#212121", fg="white", 
                                     font=("Arial", 11, "bold"),
                                     padx=10, pady=10)
        result_frame.pack(fill="x", pady=(0, 15))
        
        # Total BTC Amount
        tk.Label(result_frame, text="Total BTC Amount:", bg="#212121", fg="grey",
                font=("Arial", 10)).grid(row=0, column=0, sticky="w", pady=5)
        self.total_btc_label = tk.Label(result_frame, text="0.00000000 BTC", 
                                       bg="#212121", fg=theme_color,
                                       font=("Arial", 11, "bold"))
        self.total_btc_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        # New Average Price
        tk.Label(result_frame, text="New Avg Price:", bg="#212121", fg="grey",
                font=("Arial", 10)).grid(row=1, column=0, sticky="w", pady=5)
        self.new_avg_label = tk.Label(result_frame, text="0.00", 
                                     bg="#212121", fg=theme_color,
                                     font=("Arial", 11, "bold"))
        self.new_avg_label.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        
        # Total Investment Value (nach Kauf)
        tk.Label(result_frame, text="Total Investment Value:", bg="#212121", fg="grey",
                font=("Arial", 10)).grid(row=2, column=0, sticky="w", pady=5)
        self.total_investment_label = tk.Label(result_frame, text="0.00", 
                                               bg="#212121", fg="#888888",
                                               font=("Arial", 11, "bold"))
        self.total_investment_label.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        # Total Market Value (nach Kauf, basierend auf aktuellem Preis)
        tk.Label(result_frame, text="Total Market Value:", bg="#212121", fg="grey",
                font=("Arial", 10)).grid(row=3, column=0, sticky="w", pady=5)
        self.total_market_value_label = tk.Label(result_frame, text="0.00", 
                                                 bg="#212121", fg=theme_color,
                                                 font=("Arial", 11, "bold"))
        self.total_market_value_label.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        
        # Future Unrealized P/L
        tk.Label(result_frame, text="Future Unrealized P/L:", bg="#212121", fg="grey",
                font=("Arial", 10)).grid(row=4, column=0, sticky="w", pady=5)
        self.future_pl_label = tk.Label(result_frame, text="0.00 (0.00%)", 
                                        bg="#212121", fg="white",
                                        font=("Arial", 11, "bold"))
        self.future_pl_label.grid(row=4, column=1, padx=10, pady=5, sticky="w")
        
        # Status Label
        self.status_label = tk.Label(parent, text="", 
                                    bg="#212121", fg="#82ef82",
                                    font=("Arial", 9))
        self.status_label.pack(pady=5)
        
        # Reset Button
        reset_btn = tk.Button(parent, text="Reset All Fields", 
                             command=self.reset_fields,
                             bg="#2A2A2A", fg="white", font=("Arial", 10),
                             padx=10, relief="flat", cursor="hand2")
        reset_btn.pack(pady=10)
        
        reset_btn.bind("<Enter>", lambda e, b=reset_btn: on_enter_dark(e, b))
        reset_btn.bind("<Leave>", lambda e, b=reset_btn: on_leave_dark(e, b))
        
        # Update events
        self.btc_amount_entry.bind('<KeyRelease>', self.update_current_value)
        self.avg_price_entry.bind('<KeyRelease>', self.update_current_value)
        
        # Werte aus globalen Einstellungen laden
        self.load_values_from_settings()
    
    def create_entry(self, parent):
        """Erstellt ein Entry-Widget mit Dark Mode Styling"""
        entry = tk.Entry(parent, bg="#2A2A2A", fg="white",
                        insertbackground="white", font=("Arial", 10),
                        relief="flat", bd=2, width=15)
        return entry
    
    def load_values_from_settings(self):
        """Lädt BTC Amount und Avg Price aus den globalen Einstellungen"""
        try:
            # BTC Amount aus gespeichertem Wert laden
            btc_amount = load_btc_value()
            if btc_amount > 0:
                self.btc_amount_entry.delete(0, tk.END)
                self.btc_amount_entry.insert(0, f"{btc_amount:.8f}")
            else:
                self.btc_amount_entry.delete(0, tk.END)
                self.btc_amount_entry.insert(0, "0.00000000")
            
            # Avg Price aus gespeichertem Wert laden
            avg_price = load_avg_price()
            if avg_price > 0:
                self.avg_price_entry.delete(0, tk.END)
                self.avg_price_entry.insert(0, f"{avg_price:.2f}")
            else:
                self.avg_price_entry.delete(0, tk.END)
                self.avg_price_entry.insert(0, "0.00")
            
            # Aktuelle Werte berechnen und anzeigen
            self.update_current_value()
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def update_current_value(self, event=None):
        """Berechnet und zeigt die aktuellen Werte an"""
        try:
            btc_amount = float(self.btc_amount_entry.get() or 0)
            avg_price = float(self.avg_price_entry.get() or 0)
            market_price = self.current_market_price if self.current_market_price > 0 else 0
            
            symbol = self.currency_symbol
            
            # Investment Value (basierend auf Durchschnittspreis)
            investment_value = btc_amount * avg_price
            self.investment_value_label.config(text=f"{symbol}{investment_value:.2f}")
            
            # Current Market Value (basierend auf aktuellem Marktpreis)
            market_value = btc_amount * market_price
            self.market_value_label.config(text=f"{symbol}{market_value:.2f}")
            
            # Unrealized P/L
            if investment_value > 0:
                unrealized_pl = market_value - investment_value
                unrealized_pl_pct = (unrealized_pl / investment_value) * 100
                pl_color = "#82ef82" if unrealized_pl >= 0 else "#ff4d4d"
                self.unrealized_pl_label.config(
                    text=f"{symbol}{unrealized_pl:+.2f} ({unrealized_pl_pct:+.1f}%)",
                    fg=pl_color
                )
            else:
                self.unrealized_pl_label.config(text=f"{symbol}0.00 (0.00%)", fg="grey")
            
        except:
            pass
    
    def update_total_cost(self, event=None):
        """Berechnet und zeigt die Gesamtkosten des neuen Kaufs"""
        try:
            additional_btc = float(self.additional_btc_entry.get() or 0)
            buy_price = float(self.buy_price_entry.get() or 0)
            total_cost = additional_btc * buy_price
            
            symbol = self.currency_symbol
            self.total_cost_label.config(text=f"{total_cost:.2f} {symbol}")
        except:
            self.total_cost_label.config(text="0.00")
    
    def calculate_new_average(self):
        """Berechnet den neuen durchschnittlichen Kaufpreis"""
        try:
            current_btc = float(self.btc_amount_entry.get() or 0)
            avg_price = float(self.avg_price_entry.get() or 0)
            additional_btc = float(self.additional_btc_entry.get() or 0)
            buy_price = float(self.buy_price_entry.get() or 0)
            market_price = self.current_market_price if self.current_market_price > 0 else 0
            
            symbol = self.currency_symbol
            
            # Validierung
            if additional_btc > 0 and buy_price <= 0:
                self.status_label.config(text="✗ Please enter a purchase price!", fg="#ff4d4d")
                return
            
            if buy_price > 0 and additional_btc <= 0:
                self.status_label.config(text="✗ Please enter the BTC amount!", fg="#ff4d4d")
                return
            
            # Berechnung
            if additional_btc == 0:
                new_avg_price = avg_price
                total_btc = current_btc
                total_investment = current_btc * avg_price
                total_cost = total_investment
            else:
                current_investment = current_btc * avg_price
                new_purchase_cost = additional_btc * buy_price
                total_btc = current_btc + additional_btc
                total_investment = current_investment + new_purchase_cost
                total_cost = total_investment
                
                if total_btc > 0:
                    new_avg_price = total_investment / total_btc
                else:
                    new_avg_price = 0
            
            # Total Market Value (basierend auf aktuellem Marktpreis)
            total_market_value = total_btc * market_price
            
            # Future Unrealized P/L
            if total_investment > 0:
                future_pl = total_market_value - total_investment
                future_pl_pct = (future_pl / total_investment) * 100
                pl_color = "#82ef82" if future_pl >= 0 else "#ff4d4d"
                self.future_pl_label.config(
                    text=f"{symbol}{future_pl:+.2f} ({future_pl_pct:+.1f}%)",
                    fg=pl_color
                )
            else:
                self.future_pl_label.config(text=f"{symbol}0.00 (0.00%)", fg="grey")
            
            # Ergebnisse speichern
            self.last_result = {
                'total_btc': total_btc,
                'new_avg_price': new_avg_price,
                'total_investment': total_investment,
                'total_market_value': total_market_value,
                'future_pl': future_pl if total_investment > 0 else 0,
                'future_pl_pct': future_pl_pct if total_investment > 0 else 0,
                'additional_btc': additional_btc,
                'buy_price': buy_price,
                'current_btc': current_btc,
                'avg_price': avg_price
            }
            
            # Anzeigen
            self.display_results(total_btc, new_avg_price, total_investment, total_market_value)
            self.status_label.config(text="✓ Calculation completed", fg="#82ef82")
            
            # Globale Einstellungen aktualisieren
            self.update_global_settings()
            
        except Exception as e:
            self.status_label.config(text=f"✗ Error: {str(e)}", fg="#ff4d4d")
    
    def update_global_settings(self):
        """Aktualisiert die globalen Einstellungen mit den aktuellen Werten"""
        try:
            btc_amount = float(self.btc_amount_entry.get() or 0)
            avg_price = float(self.avg_price_entry.get() or 0)
            
            if btc_amount > 0:
                save_btc_value(btc_amount)
            if avg_price > 0:
                save_avg_price(avg_price)
        except:
            pass
    
    def display_results(self, total_btc, new_avg_price, total_investment, total_market_value):
        """Zeigt die berechneten Ergebnisse an"""
        symbol = self.currency_symbol
        
        self.total_btc_label.config(text=f"{total_btc:.8f} BTC")
        self.new_avg_label.config(text=f"{new_avg_price:.2f} {symbol}")
        self.total_investment_label.config(text=f"{symbol}{total_investment:.2f}")
        self.total_market_value_label.config(text=f"{symbol}{total_market_value:.2f}")
    
    def save_transaction(self):
        """Speichert die Transaktion in einer Datei"""
        try:
            if not self.last_result:
                self.status_label.config(text="✗ Please calculate an average first!", fg="#ff4d4d")
                return
            
            # Timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            symbol = self.currency_symbol
            currency = self.current_currency
            market_price = self.current_market_price if self.current_market_price > 0 else 0
            
            # Datei öffnen
            with open(self.data_file, 'a', encoding='utf-8') as file:
                if os.path.getsize(self.data_file) == 0:
                    file.write("=" * 80 + "\n")
                    file.write("BTC TRANSACTION HISTORY\n")
                    file.write("=" * 80 + "\n\n")
                
                file.write(f"Date/Time: {timestamp}\n")
                file.write(f"Currency: {currency} ({symbol})\n")
                file.write(f"Current Market Price: {symbol}{market_price:.2f}\n")
                file.write("-" * 40 + "\n")
                file.write("BEFORE TRANSACTION:\n")
                file.write(f"  BTC Amount: {self.last_result['current_btc']:.8f} BTC\n")
                file.write(f"  Average Price: {self.last_result['avg_price']:.2f} {symbol}\n")
                file.write(f"  Investment Value: {self.last_result['current_btc'] * self.last_result['avg_price']:.2f} {symbol}\n")
                file.write(f"  Market Value: {self.last_result['current_btc'] * market_price:.2f} {symbol}\n")
                file.write("\n")
                file.write("NEW PURCHASE:\n")
                file.write(f"  Additional BTC: {self.last_result['additional_btc']:.8f} BTC\n")
                file.write(f"  Purchase Price: {self.last_result['buy_price']:.2f} {symbol}\n")
                file.write(f"  Total Cost: {self.last_result['additional_btc'] * self.last_result['buy_price']:.2f} {symbol}\n")
                file.write("\n")
                file.write("AFTER TRANSACTION:\n")
                file.write(f"  Total BTC: {self.last_result['total_btc']:.8f} BTC\n")
                file.write(f"  New Average Price: {self.last_result['new_avg_price']:.2f} {symbol}\n")
                file.write(f"  Total Investment: {self.last_result['total_investment']:.2f} {symbol}\n")
                file.write(f"  Total Market Value: {self.last_result['total_market_value']:.2f} {symbol}\n")
                file.write(f"  Future Unrealized P/L: {self.last_result['future_pl']:+.2f} ({self.last_result['future_pl_pct']:+.1f}%)\n")
                file.write("=" * 80 + "\n\n")
            
            self.status_label.config(text=f"✓ Transaction saved to {self.data_file}", fg="#82ef82")
            self.expanded_window.after(3000, lambda: self.status_label.config(text=""))
            
        except Exception as e:
            self.status_label.config(text=f"✗ Error saving: {str(e)}", fg="#ff4d4d")
    
    def reset_fields(self):
        """Setzt alle Felder zurück"""
        self.btc_amount_entry.delete(0, tk.END)
        self.btc_amount_entry.insert(0, "0.00000000")
        
        self.avg_price_entry.delete(0, tk.END)
        self.avg_price_entry.insert(0, "0.00")
        
        self.additional_btc_entry.delete(0, tk.END)
        self.buy_price_entry.delete(0, tk.END)
        
        symbol = self.currency_symbol
        self.total_btc_label.config(text="0.00000000 BTC")
        self.new_avg_label.config(text=f"0.00 {symbol}")
        self.total_investment_label.config(text=f"0.00 {symbol}")
        self.total_market_value_label.config(text=f"0.00 {symbol}")
        self.total_cost_label.config(text="0.00")
        self.future_pl_label.config(text=f"0.00 (0.00%)", fg="grey")
        self.status_label.config(text="")
        self.update_current_value()
        self.last_result = None
    
    def update_display(self):
        """Aktualisiert die Anzeige bei Währungswechsel"""
        symbol = self.currency_symbol
        try:
            self.update_current_value()
            self.update_total_cost()
            
            # Update result labels
            avg_text = self.new_avg_label.cget('text')
            if avg_text and ' ' in avg_text:
                value = avg_text.split()[0]
                self.new_avg_label.config(text=f"{value} {symbol}")
            
            inv_text = self.total_investment_label.cget('text')
            if inv_text and ' ' in inv_text:
                value = inv_text.split()[0]
                self.total_investment_label.config(text=f"{value} {symbol}")
            
            mv_text = self.total_market_value_label.cget('text')
            if mv_text and ' ' in mv_text:
                value = mv_text.split()[0]
                self.total_market_value_label.config(text=f"{value} {symbol}")
        except:
            pass
    
    def collapse(self):
        """Schließt das erweiterte Fenster"""
        self.is_expanded = False
        self.avg_button.config(text="AVG")
        
        if self.expanded_window:
            try:
                x = self.expanded_window.winfo_x()
                y = self.expanded_window.winfo_y()
                save_attached_window_pos('avg', x, y)
            except:
                pass
            
            self.expanded_window.destroy()
            self.expanded_window = None
						
# ====== ENHANCED PORTFOLIO TRACKER WINDOW ======
class PortfolioTracker:
    def __init__(self, parent):
        self.parent = parent
        self.is_expanded = False
        self.expanded_window = None
        self.update_id = None
        self.sort_column = 'time'
        self.sort_reverse = True
        self.hover_annotation = None
        self.hover_line = None
        self.hover_timer = None

        self.portfolio_button = tk.Button(parent, text="P/L", command=self.toggle_expand,
                                          bg=theme_color, fg="black", font=("Arial", 10), width=3)
        self.portfolio_button.place(x=75, y=415)

        self.portfolio_button.bind("<Enter>", lambda e, b=self.portfolio_button: on_enter_button(e, b))
        self.portfolio_button.bind("<Leave>", lambda e, b=self.portfolio_button: on_leave_button(e, b))

        # Labels initialisieren
        self.total_invested_label = None
        self.total_invested_excl_fees_label = None
        self.total_fees_label = None
        self.total_cost_label = None
        self.total_value_label = None
        self.realized_pnl_label = None
        self.unrealized_pnl_label = None
        self.total_pnl_label = None
        self.total_btc_label = None
        self.win_loss_label = None
        self.avg_price_excl_fees_label = None
        self.avg_price_incl_fees_label = None
        self.largest_win_label = None
        self.largest_loss_label = None
        self.portfolio_status_label = None
        self.trade_count_label = None
        self.total_btc_label_status = None
        self.trade_tree = None
        self.entry_widgets = {}

        # Chart Axes
        self.stash_ax = None
        self.realized_ax = None
        self.unrealized_ax = None
        self.portfolio_value_ax = None
        self.stash_canvas = None
        self.realized_canvas = None
        self.unrealized_canvas = None
        self.portfolio_value_canvas = None
        self.notebook = None
        self.main_container = None
        self.canvas = None
        self.scrollable_frame = None

        # Hover Variablen
        self.stash_fig = None
        self.realized_fig = None
        self.unrealized_fig = None
        self.portfolio_value_fig = None

        # Trades laden
        self.load_trades_from_file()

    def get_historical_price_at_time(self, target_time):
        """Holt den historischen Preis zu einem bestimmten Zeitpunkt aus den OHLC-Daten"""
        global last_historical_data

        if not last_historical_data:
            return None

        closest_price = None
        min_diff = timedelta(days=365)

        for data in last_historical_data:
            timestamp = data[0]
            close_price = data[4]
            diff = abs(timestamp - target_time)
            if diff < min_diff:
                min_diff = diff
                closest_price = close_price

        if min_diff < timedelta(days=7):
            return closest_price
        return None

    def load_trades_from_file(self):
        """Laedt Trades aus Datei"""
        global trades
        trades = []

        if os.path.exists(TRADES_FILE):
            try:
                with open(TRADES_FILE, "r") as f:
                    for line in f:
                        parts = line.strip().split('|')
                        if len(parts) >= 10:
                            trade = {
                                'time':      parts[0],
                                'type':      parts[1],
                                'vol':       float(parts[2]),
                                'price':     float(parts[3]),
                                'cost':      float(parts[4]),
                                'fee':       float(parts[5]),
                                'pair':      parts[6],
                                'ordertype': parts[7],
                                'txid':      parts[8],
                                'ordertxid': parts[9]
                            }
                            if trade['type'] == 'buy':
                                trade['total'] = trade['cost'] + trade['fee']
                            else:
                                trade['total'] = trade['cost'] - trade['fee']
                            try:
                                trade['datetime'] = datetime.strptime(trade['time'], "%Y-%m-%d %H:%M:%S")
                            except:
                                try:
                                    trade['datetime'] = datetime.strptime(trade['time'], "%Y-%m-%d %H:%M:%S.%f")
                                except:
                                    trade['datetime'] = datetime.now()
                            trade['id'] = len(trades)
                            trades.append(trade)
                print(f"Loaded {len(trades)} trades from file")
            except Exception as e:
                print(f"Error loading trades: {e}")

    def toggle_expand(self):
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        self.is_expanded = True
        self.portfolio_button.config(text="X")

        self.expanded_window = tk.Toplevel(self.parent)
        self.expanded_window.overrideredirect(1)
        self.expanded_window.attributes('-topmost', True)
        self.expanded_window.config(bg="#212121")

        window_width  = 1200
        window_height = 1000

        saved_x, saved_y = load_attached_window_pos('portfolio')
        if saved_x is not None and saved_y is not None:
            self.expanded_window.geometry(f"{window_width}x{window_height}+{saved_x}+{saved_y}")
        else:
            main_x = self.parent.winfo_x()
            main_y = self.parent.winfo_y()
            self.expanded_window.geometry(f"{window_width}x{window_height}+{main_x - window_width}+{main_y}")

        # ── Movebar ──────────────────────────────────────────────────────────
        movebar = tk.Frame(self.expanded_window, bg="#2A2A2A", height=35, cursor="fleur")
        movebar.pack(fill="x", side="top")
        movebar.pack_propagate(False)

        title_label = tk.Label(movebar, text="P/L Portfolio Tracker",
                               bg="#2A2A2A", fg=theme_color,
                               font=("Arial", 14, "bold"))
        title_label.pack(side="left", padx=15, pady=5)

        currency_frame = tk.Frame(movebar, bg="#2A2A2A")
        currency_frame.pack(side="left", padx=20)

        self.currency_var = tk.StringVar(value=CURRENCY)
        eur_radio = tk.Radiobutton(currency_frame, text="EUR", variable=self.currency_var, value="EUR",
                                   bg="#2A2A2A", fg="white", selectcolor=theme_color,
                                   command=self.change_currency)
        eur_radio.pack(side="left")
        usd_radio = tk.Radiobutton(currency_frame, text="USD", variable=self.currency_var, value="USD",
                                   bg="#2A2A2A", fg="white", selectcolor=theme_color,
                                   command=self.change_currency)
        usd_radio.pack(side="left", padx=(10, 0))

        import_button = tk.Button(movebar, text="Import CSV", command=self.import_csv,
                                  bg="#2A2A2A", fg=theme_color, bd=1, font=("Arial", 10))
        import_button.pack(side="left", padx=5)

        export_button = tk.Button(movebar, text="Export CSV", command=self.export_csv,
                                  bg="#2A2A2A", fg=theme_color, bd=1, font=("Arial", 10))
        export_button.pack(side="left", padx=5)

        clear_button = tk.Button(movebar, text="Clear All", command=self.clear_all_trades,
                                 bg="#BD5959", fg="white", bd=1, font=("Arial", 10))
        clear_button.pack(side="left", padx=5)

        close_button = tk.Button(movebar, text="X", command=self.collapse,
                                 bg="#2A2A2A", fg="white", bd=0, font=("Arial", 14, "bold"))
        close_button.pack(side="right", padx=15, pady=5)

        def on_drag_start(event):
            self.expanded_window.x = event.x
            self.expanded_window.y = event.y

        def on_drag_motion(event):
            deltax = event.x - self.expanded_window.x
            deltay = event.y - self.expanded_window.y
            x = self.expanded_window.winfo_x() + deltax
            y = self.expanded_window.winfo_y() + deltay
            self.expanded_window.geometry(f"+{x}+{y}")

        movebar.bind("<Button-1>", on_drag_start)
        movebar.bind("<B1-Motion>", on_drag_motion)
        title_label.bind("<Button-1>", on_drag_start)
        title_label.bind("<B1-Motion>", on_drag_motion)

        import_button.bind("<Enter>", lambda e, b=import_button: on_enter_button(e, b))
        import_button.bind("<Leave>", lambda e, b=import_button: on_leave_button(e, b))
        export_button.bind("<Enter>", lambda e, b=export_button: on_enter_button(e, b))
        export_button.bind("<Leave>", lambda e, b=export_button: on_leave_button(e, b))
        clear_button.bind("<Enter>", lambda e: clear_button.config(bg="#ff4d4d"))
        clear_button.bind("<Leave>", lambda e: clear_button.config(bg="#BD5959"))
        close_button.bind("<Enter>", lambda e: close_button.config(bg="#BD5959"))
        close_button.bind("<Leave>", lambda e: close_button.config(bg="#2A2A2A"))

        # ── Scrollable content area ───────────────────────────────────────────
        main_container = tk.Frame(self.expanded_window, bg="#212121")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        canvas_frame = tk.Frame(main_container, bg="#212121")
        canvas_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg="#212121", highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview,
                                 bg="#333333", troughcolor="#212121", width=14)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#212121")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        def configure_canvas_width(event):
            self.canvas.itemconfig(1, width=event.width)

        self.canvas.bind('<Configure>', configure_canvas_width)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ── Build UI ──────────────────────────────────────────────────────────
        self.create_content()
        self.create_notebook()

        # ── Status bar ────────────────────────────────────────────────────────
        status_frame = tk.Frame(main_container, bg="#212121", height=30)
        status_frame.pack(fill="x", side="bottom", pady=5)

        self.portfolio_status_label = tk.Label(status_frame, text="Ready",
                                               bg="#212121", fg="#82ef82", font=("Arial", 10))
        self.portfolio_status_label.pack(side="left")

        self.trade_count_label = tk.Label(status_frame, text="Trades: 0",
                                          bg="#212121", fg="grey", font=("Arial", 10))
        self.trade_count_label.pack(side="left", padx=20)

        self.total_btc_label_status = tk.Label(status_frame, text="BTC: 0.00000000",
                                               bg="#212121", fg="#F7931A", font=("Arial", 10, "bold"))
        self.total_btc_label_status.pack(side="left", padx=20)

        self.update_charts()
        self.load_trades_to_ui()
        self.update_portfolio_stats()

    def change_currency(self):
        """Aendert die Waehrung fuer das Portfolio-Fenster"""
        global CURRENCY
        new_currency = self.currency_var.get()
        if new_currency != CURRENCY:
            CURRENCY = new_currency
            self.update_portfolio_stats()
            self.update_charts()
            self.load_trades_to_ui()

    def create_content(self):
        """Erstellt den Inhalt im scrollbaren Frame"""
        stats_grid = tk.Frame(self.scrollable_frame, bg="#212121")
        stats_grid.pack(fill="x", pady=10, padx=10)

        # Row 1: Invested / Fees
        row1_frame = tk.Frame(stats_grid, bg="#212121")
        row1_frame.pack(fill="x", pady=2)

        invested_frame = self.create_stat_frame(row1_frame, "Invested (excl. Fees)")
        invested_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.total_invested_excl_fees_label = tk.Label(invested_frame, text="0.00",
                                                        bg="#2A2A2A", fg="white", font=("Arial", 14, "bold"))
        self.total_invested_excl_fees_label.pack(pady=(0, 5))

        fees_frame = self.create_stat_frame(row1_frame, "Total Fees Paid")
        fees_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.total_fees_label = tk.Label(fees_frame, text="0.00",
                                         bg="#2A2A2A", fg="#ffb84d", font=("Arial", 14, "bold"))
        self.total_fees_label.pack(pady=(0, 5))

        # Row 2: Total Cost / Current Value
        row2_frame = tk.Frame(stats_grid, bg="#212121")
        row2_frame.pack(fill="x", pady=2)

        cost_frame = self.create_stat_frame(row2_frame, "Total Cost (incl. Fees)")
        cost_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.total_cost_label = tk.Label(cost_frame, text="0.00",
                                         bg="#2A2A2A", fg="white", font=("Arial", 14, "bold"))
        self.total_cost_label.pack(pady=(0, 5))

        value_frame = self.create_stat_frame(row2_frame, "Current Value")
        value_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.total_value_label = tk.Label(value_frame, text="0.00",
                                          bg="#2A2A2A", fg="white", font=("Arial", 14, "bold"))
        self.total_value_label.pack(pady=(0, 5))

        # Row 3: Realized / Unrealized P/L
        row3_frame = tk.Frame(stats_grid, bg="#212121")
        row3_frame.pack(fill="x", pady=2)

        realized_frame = self.create_stat_frame(row3_frame, "Realized P/L")
        realized_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.realized_pnl_label = tk.Label(realized_frame, text="0.00 (0.00%)",
                                           bg="#2A2A2A", fg="white", font=("Arial", 14, "bold"))
        self.realized_pnl_label.pack(pady=(0, 5))

        unrealized_frame = self.create_stat_frame(row3_frame, "Unrealized P/L")
        unrealized_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.unrealized_pnl_label = tk.Label(unrealized_frame, text="0.00 (0.00%)",
                                              bg="#2A2A2A", fg="white", font=("Arial", 14, "bold"))
        self.unrealized_pnl_label.pack(pady=(0, 5))

        # Row 4: Total P/L / Total BTC
        row4_frame = tk.Frame(stats_grid, bg="#212121")
        row4_frame.pack(fill="x", pady=2)

        total_pnl_frame = self.create_stat_frame(row4_frame, "Total P/L")
        total_pnl_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.total_pnl_label = tk.Label(total_pnl_frame, text="0.00 (0.00%)",
                                        bg="#2A2A2A", fg="white", font=("Arial", 14, "bold"))
        self.total_pnl_label.pack(pady=(0, 5))

        btc_frame = self.create_stat_frame(row4_frame, "Total BTC")
        btc_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.total_btc_label = tk.Label(btc_frame, text="0.00000000 BTC",
                                        bg="#2A2A2A", fg="#F7931A", font=("Arial", 14, "bold"))
        self.total_btc_label.pack(pady=(0, 5))

        # Row 5: Avg Prices
        row5_frame = tk.Frame(stats_grid, bg="#212121")
        row5_frame.pack(fill="x", pady=2)

        avg_excl_frame = self.create_stat_frame(row5_frame, "Avg Buy Price (excl. Fees)")
        avg_excl_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.avg_price_excl_fees_label = tk.Label(avg_excl_frame, text="0.00",
                                                   bg="#2A2A2A", fg="white", font=("Arial", 12))
        self.avg_price_excl_fees_label.pack(pady=(0, 5))

        avg_incl_frame = self.create_stat_frame(row5_frame, "Avg Buy Price (incl. Fees)")
        avg_incl_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.avg_price_incl_fees_label = tk.Label(avg_incl_frame, text="0.00",
                                                   bg="#2A2A2A", fg="white", font=("Arial", 12))
        self.avg_price_incl_fees_label.pack(pady=(0, 5))

        # Row 6: Win/Loss / Largest Win
        row6_frame = tk.Frame(stats_grid, bg="#212121")
        row6_frame.pack(fill="x", pady=2)

        win_frame = self.create_stat_frame(row6_frame, "Win / Loss")
        win_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.win_loss_label = tk.Label(win_frame, text="0 / 0",
                                       bg="#2A2A2A", fg="white", font=("Arial", 12, "bold"))
        self.win_loss_label.pack(pady=(0, 5))

        lwin_frame = self.create_stat_frame(row6_frame, "Largest Win")
        lwin_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.largest_win_label = tk.Label(lwin_frame, text="0.00",
                                          bg="#2A2A2A", fg="#82ef82", font=("Arial", 12, "bold"))
        self.largest_win_label.pack(pady=(0, 5))

        # Row 7: Largest Loss / empty
        row7_frame = tk.Frame(stats_grid, bg="#212121")
        row7_frame.pack(fill="x", pady=2)

        lloss_frame = self.create_stat_frame(row7_frame, "Largest Loss")
        lloss_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.largest_loss_label = tk.Label(lloss_frame, text="0.00",
                                           bg="#2A2A2A", fg="#ff4d4d", font=("Arial", 12, "bold"))
        self.largest_loss_label.pack(pady=(0, 5))

        empty_frame = self.create_stat_frame(row7_frame, "")
        empty_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

        # ── Chart Container ───────────────────────────────────────────────────
        charts_container = tk.Frame(self.scrollable_frame, bg="#212121")
        charts_container.pack(fill="x", padx=10, pady=10)

        # ── Chart 1: BTC HODL'd ───────────────────────────────────────────────
        tk.Label(charts_container, text="Bitcoin HODL'd",
                 bg="#212121", fg="white", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 5))

        stash_frame = tk.Frame(charts_container, bg="#212121", height=200)
        stash_frame.pack(fill="x", pady=(0, 15))
        stash_frame.pack_propagate(False)

        self.stash_fig, self.stash_ax = plt.subplots(figsize=(11, 2.5), dpi=100)
        self.stash_fig.patch.set_facecolor('#212121')
        self.stash_ax.set_facecolor('#212121')
        self.stash_ax.tick_params(colors='grey')
        self.stash_ax.xaxis.label.set_color('grey')
        self.stash_ax.yaxis.label.set_color('grey')
        self.stash_fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.22)

        self.stash_canvas = FigureCanvasTkAgg(self.stash_fig, master=stash_frame)
        self.stash_canvas.get_tk_widget().pack(fill="both", expand=True)
        self.stash_canvas.mpl_connect('motion_notify_event', self.on_stash_hover)

        # ── Chart 2: Unrealized P/L ───────────────────────────────────────────
        tk.Label(charts_container, text="Unrealized P/L Over Time",
                 bg="#212121", fg="white", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10, 5))

        unrealized_frame = tk.Frame(charts_container, bg="#212121", height=200)
        unrealized_frame.pack(fill="x", pady=(0, 15))
        unrealized_frame.pack_propagate(False)

        self.unrealized_fig, self.unrealized_ax = plt.subplots(figsize=(11, 2.5), dpi=100)
        self.unrealized_fig.patch.set_facecolor('#212121')
        self.unrealized_ax.set_facecolor('#212121')
        self.unrealized_ax.tick_params(colors='grey')
        self.unrealized_ax.xaxis.label.set_color('grey')
        self.unrealized_ax.yaxis.label.set_color('grey')
        self.unrealized_fig.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.22)

        self.unrealized_canvas = FigureCanvasTkAgg(self.unrealized_fig, master=unrealized_frame)
        self.unrealized_canvas.get_tk_widget().pack(fill="both", expand=True)
        self.unrealized_canvas.mpl_connect('motion_notify_event', self.on_unrealized_hover)

        # ── Chart 3: Portfolio Value in Fiat ─────────────────────────────────
        tk.Label(charts_container, text="Portfolio Value in Fiat (at Trade Price)",
                 bg="#212121", fg="white", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10, 5))

        portfolio_value_frame = tk.Frame(charts_container, bg="#212121", height=200)
        portfolio_value_frame.pack(fill="x", pady=(0, 15))
        portfolio_value_frame.pack_propagate(False)

        self.portfolio_value_fig, self.portfolio_value_ax = plt.subplots(figsize=(11, 2.5), dpi=100)
        self.portfolio_value_fig.patch.set_facecolor('#212121')
        self.portfolio_value_ax.set_facecolor('#212121')
        self.portfolio_value_ax.tick_params(colors='grey')
        self.portfolio_value_ax.xaxis.label.set_color('grey')
        self.portfolio_value_ax.yaxis.label.set_color('grey')
        self.portfolio_value_fig.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.22)

        self.portfolio_value_canvas = FigureCanvasTkAgg(self.portfolio_value_fig, master=portfolio_value_frame)
        self.portfolio_value_canvas.get_tk_widget().pack(fill="both", expand=True)
        self.portfolio_value_canvas.mpl_connect('motion_notify_event', self.on_portfolio_value_hover)

        # ── Chart 4: Realized P/L ─────────────────────────────────────────────
        tk.Label(charts_container, text="Realized P/L from Sales",
                 bg="#212121", fg="white", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10, 5))

        realized_chart_frame = tk.Frame(charts_container, bg="#212121", height=200)
        realized_chart_frame.pack(fill="x", pady=(0, 15))
        realized_chart_frame.pack_propagate(False)

        self.realized_fig, self.realized_ax = plt.subplots(figsize=(11, 2.5), dpi=100)
        self.realized_fig.patch.set_facecolor('#212121')
        self.realized_ax.set_facecolor('#212121')
        self.realized_ax.tick_params(colors='grey')
        self.realized_ax.xaxis.label.set_color('grey')
        self.realized_ax.yaxis.label.set_color('grey')
        self.realized_fig.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.22)

        self.realized_canvas = FigureCanvasTkAgg(self.realized_fig, master=realized_chart_frame)
        self.realized_canvas.get_tk_widget().pack(fill="both", expand=True)
        self.realized_canvas.mpl_connect('motion_notify_event', self.on_realized_hover)

    def create_stat_frame(self, parent, title):
        """Erstellt einen Statistik-Frame mit Titel"""
        frame = tk.Frame(parent, bg="#2A2A2A", relief="solid", bd=1,
                         highlightbackground="#444444")
        tk.Label(frame, text=title, bg="#2A2A2A", fg="grey",
                 font=("Arial", 10)).pack(pady=(5, 0))
        return frame

    def create_notebook(self):
        """Erstellt Notebook mit Tabs"""
        notebook_frame = tk.Frame(self.scrollable_frame, bg="#212121")
        notebook_frame.pack(fill="both", expand=True, padx=10, pady=10)

        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background='#212121', borderwidth=0)
        style.configure('TNotebook.Tab', background='#2A2A2A', foreground='white',
                        padding=[15, 5], font=('Arial', 10))
        style.map('TNotebook.Tab', background=[('selected', theme_color)],
                  foreground=[('selected', 'black')])

        self.notebook = ttk.Notebook(notebook_frame)
        self.notebook.pack(fill="both", expand=True)

        history_tab = tk.Frame(self.notebook, bg="#212121")
        self.notebook.add(history_tab, text="Trade History")
        self.create_history_tab(history_tab)

        add_trade_tab = tk.Frame(self.notebook, bg="#212121")
        self.notebook.add(add_trade_tab, text="Add Trade")
        self.create_add_trade_tab(add_trade_tab)

    def create_history_tab(self, parent):
        """Erstellt den History Tab mit Trade-Tabelle"""
        tree_frame = tk.Frame(parent, bg="#212121")
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        columns = ('time', 'type', 'vol', 'price', 'cost', 'fee', 'total', 'pnl')
        self.trade_tree = ttk.Treeview(tree_frame, columns=columns, show='headings',
                                       height=12)

        style = ttk.Style()
        style.configure('Treeview', background='#2A2A2A', foreground='white',
                        fieldbackground='#2A2A2A', rowheight=25)
        style.configure('Treeview.Heading', background='#333333', foreground=theme_color,
                        font=('Arial', 10, 'bold'))
        style.map('Treeview', background=[('selected', '#444444')])

        col_headers = {
            'time':  ('Date / Time', 140),
            'type':  ('Type', 60),
            'vol':   ('Volume (BTC)', 110),
            'price': ('Price', 100),
            'cost':  ('Cost', 100),
            'fee':   ('Fee', 80),
            'total': ('Total', 100),
            'pnl':   ('P/L', 100),
        }
        for col, (heading, width) in col_headers.items():
            self.trade_tree.heading(col, text=heading,
                                    command=lambda c=col: self.sort_treeview(c))
            self.trade_tree.column(col, width=width, anchor='center')

        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical",
                                       command=self.trade_tree.yview)
        self.trade_tree.configure(yscrollcommand=tree_scrollbar.set)

        self.trade_tree.pack(side="left", fill="both", expand=True)
        tree_scrollbar.pack(side="right", fill="y")

        button_frame = tk.Frame(parent, bg="#212121")
        button_frame.pack(fill="x", pady=5, padx=5)

        delete_button = tk.Button(button_frame, text="Delete Selected",
                                  command=self.delete_selected_trade,
                                  bg="#BD5959", fg="white", font=("Arial", 10), padx=10, bd=0)
        delete_button.pack(side="left", padx=5)

        delete_button.bind("<Enter>", lambda e: delete_button.config(bg="#ff4d4d"))
        delete_button.bind("<Leave>", lambda e: delete_button.config(bg="#BD5959"))

        self.load_trades_to_ui()

    def create_add_trade_tab(self, parent):
        """Erstellt den Add Trade Tab"""
        form_frame = tk.Frame(parent, bg="#212121")
        form_frame.pack(fill="both", expand=True, padx=20, pady=20)

        tk.Label(form_frame, text="Add Trade Manually", bg="#212121", fg="white",
                 font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=4,
                                                   pady=(0, 15), sticky="w")

        fields = [
            ("Date / Time",    "time",  "YYYY-MM-DD HH:MM:SS"),
            ("Type",           "type",  "buy / sell"),
            ("Volume (BTC)",   "vol",   "0.00000000"),
            ("Price",          "price", "0.00"),
            ("Cost",           "cost",  "0.00"),
            ("Fee",            "fee",   "0.00"),
            ("Pair",           "pair",  "XBTEUR"),
            ("Order Type",     "ordertype", "market"),
            ("TXID",           "txid",  "optional"),
            ("Order TXID",     "ordertxid", "optional"),
        ]

        self.entry_widgets = {}
        for i, (label, key, placeholder) in enumerate(fields):
            row = i // 2
            col = (i % 2) * 2

            tk.Label(form_frame, text=label + ":", bg="#212121", fg="grey",
                     font=("Arial", 10)).grid(row=row + 1, column=col,
                                               sticky="e", padx=(10, 5), pady=5)

            entry = tk.Entry(form_frame, bg="#2A2A2A", fg="white",
                             insertbackground="white", width=20, font=("Arial", 10), bd=0)
            entry.insert(0, placeholder)
            entry.config(fg="grey")
            entry.bind("<FocusIn>",
                       lambda e, p=placeholder: e.widget.delete(0, tk.END)
                       if e.widget.get() == p else None)
            entry.bind("<FocusOut>",
                       lambda e, p=placeholder: (e.widget.insert(0, p),
                                                  e.widget.config(fg="grey"))
                       if not e.widget.get() else e.widget.config(fg="white"))
            entry.grid(row=row + 1, column=col + 1, sticky="w", padx=(0, 10), pady=5)
            self.entry_widgets[key] = entry

        submit_button = tk.Button(form_frame, text="Add Trade",
                                  command=self.add_trade_manual,
                                  bg=theme_color, fg="black",
                                  font=("Arial", 11, "bold"), padx=15, pady=8, bd=0)
        submit_button.grid(row=len(fields) // 2 + 2, column=0, columnspan=4, pady=15)
        submit_button.bind("<Enter>", lambda e, b=submit_button: on_enter_button(e, b))
        submit_button.bind("<Leave>", lambda e, b=submit_button: on_leave_button(e, b))

        self.add_trade_status = tk.Label(form_frame, text="", bg="#212121", fg="grey",
                                          font=("Arial", 9))
        self.add_trade_status.grid(row=len(fields) // 2 + 3, column=0, columnspan=4)

    def add_trade_manual(self):
        """Fuegt einen manuell eingegebenen Trade hinzu"""
        try:
            placeholders = {
                "time": "YYYY-MM-DD HH:MM:SS",
                "type": "buy / sell",
                "vol": "0.00000000",
                "price": "0.00",
                "cost": "0.00",
                "fee": "0.00",
                "pair": "XBTEUR",
                "ordertype": "market",
                "txid": "optional",
                "ordertxid": "optional",
            }

            def get_val(key):
                v = self.entry_widgets[key].get().strip()
                return "" if v == placeholders.get(key, "") else v

            trade_time = get_val("time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            trade_type = get_val("type").lower()
            if trade_type not in ("buy", "sell"):
                self.add_trade_status.config(text="Type must be 'buy' or 'sell'.", fg="#ff4d4d")
                return

            vol       = float(get_val("vol") or 0)
            price     = float(get_val("price") or 0)
            cost      = float(get_val("cost") or 0) or vol * price
            fee       = float(get_val("fee") or 0)
            pair      = get_val("pair") or "XBTEUR"
            ordertype = get_val("ordertype") or "market"
            txid      = get_val("txid") or f"manual_{len(trades)}"
            ordertxid = get_val("ordertxid") or txid

            trade = {
                'time':      trade_time,
                'type':      trade_type,
                'vol':       vol,
                'price':     price,
                'cost':      cost,
                'fee':       fee,
                'pair':      pair,
                'ordertype': ordertype,
                'txid':      txid,
                'ordertxid': ordertxid,
            }
            trade['total'] = cost + fee if trade_type == 'buy' else cost - fee
            try:
                trade['datetime'] = datetime.strptime(trade_time, "%Y-%m-%d %H:%M:%S")
            except:
                trade['datetime'] = datetime.now()
            trade['id'] = len(trades)
            trades.append(trade)
            self.save_trades()

            self.update_charts()
            self.load_trades_to_ui()
            self.update_portfolio_stats()
            self.add_trade_status.config(text="Trade added successfully.", fg="#82ef82")

        except ValueError as exc:
            self.add_trade_status.config(text=f"Invalid input: {exc}", fg="#ff4d4d")

    def import_csv(self):
        """Importiert Trades aus einer CSV-Datei"""
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(
            title="Select Kraken CSV Export",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not filepath:
            return
        try:
            imported = 0
            with open(filepath, "r", encoding="utf-8") as f:
                import csv
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        trade_type = row.get('type', '').lower()
                        if trade_type not in ('buy', 'sell'):
                            continue
                        vol   = float(row.get('vol', 0))
                        price = float(row.get('price', 0))
                        cost  = float(row.get('cost', 0))
                        fee   = float(row.get('fee', 0))
                        trade = {
                            'time':      row.get('time', ''),
                            'type':      trade_type,
                            'vol':       vol,
                            'price':     price,
                            'cost':      cost,
                            'fee':       fee,
                            'pair':      row.get('pair', 'XBTEUR'),
                            'ordertype': row.get('ordertype', 'market'),
                            'txid':      row.get('txid', f'csv_{len(trades)}'),
                            'ordertxid': row.get('ordertxid', ''),
                        }
                        trade['total'] = cost + fee if trade_type == 'buy' else cost - fee
                        try:
                            trade['datetime'] = datetime.strptime(trade['time'], "%Y-%m-%d %H:%M:%S")
                        except:
                            try:
                                trade['datetime'] = datetime.strptime(trade['time'], "%Y-%m-%d %H:%M:%S.%f")
                            except:
                                trade['datetime'] = datetime.now()
                        trade['id'] = len(trades)
                        trades.append(trade)
                        imported += 1
                    except Exception:
                        continue

            self.save_trades()
            self.update_charts()
            self.load_trades_to_ui()
            self.update_portfolio_stats()
            if self.portfolio_status_label:
                self.portfolio_status_label.config(text=f"Imported {imported} trades.", fg="#82ef82")
        except Exception as exc:
            if self.portfolio_status_label:
                self.portfolio_status_label.config(text=f"Import error: {exc}", fg="#ff4d4d")

    def export_csv(self):
        """Exportiert Trades als CSV-Datei"""
        from tkinter import filedialog
        import csv
        filepath = filedialog.asksaveasfilename(
            title="Export Trades",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")]
        )
        if not filepath:
            return
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["time", "type", "vol", "price", "cost", "fee",
                                 "pair", "ordertype", "txid", "ordertxid"])
                for t in trades:
                    writer.writerow([
                        t.get('time', ''), t.get('type', ''), t.get('vol', 0),
                        t.get('price', 0), t.get('cost', 0), t.get('fee', 0),
                        t.get('pair', ''), t.get('ordertype', ''),
                        t.get('txid', ''), t.get('ordertxid', '')
                    ])
            if self.portfolio_status_label:
                self.portfolio_status_label.config(text="Export successful.", fg="#82ef82")
        except Exception as exc:
            if self.portfolio_status_label:
                self.portfolio_status_label.config(text=f"Export error: {exc}", fg="#ff4d4d")

    def clear_all_trades(self):
        """Loescht alle Trades nach Bestaetigung"""
        if messagebox.askyesno("Clear Trades", "Delete all trades? This cannot be undone."):
            global trades
            trades = []
            self.save_trades()
            self.update_charts()
            self.load_trades_to_ui()
            self.update_portfolio_stats()

    def delete_selected_trade(self):
        """Loescht den ausgewaehlten Trade"""
        selected = self.trade_tree.selection()
        if not selected:
            return
        item = self.trade_tree.item(selected[0])
        values = item['values']
        if not values:
            return
        time_str = str(values[0])
        global trades
        trades = [t for t in trades if t.get('time', '') != time_str]
        self.save_trades()
        self.update_charts()
        self.load_trades_to_ui()
        self.update_portfolio_stats()

    def sort_treeview(self, col):
        """Sortiert die Treeview-Spalte"""
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = False
        self.load_trades_to_ui()

    def load_trades_to_ui(self):
        """Laedt Trades in die Treeview"""
        if not hasattr(self, 'trade_tree') or self.trade_tree is None:
            return

        for item in self.trade_tree.get_children():
            self.trade_tree.delete(item)

        symbol = get_currency_symbol()

        sorted_trades = sorted(trades,
                               key=lambda x: x.get(self.sort_column,
                                                    x.get('datetime', datetime.now())),
                               reverse=self.sort_reverse)

        for trade in sorted_trades:
            pnl, pnl_pct = self.calculate_trade_pnl(trade)
            pnl_str = f"{symbol}{pnl:+.2f} ({pnl_pct:+.1f}%)" if trade.get('type') == 'sell' else "-"
            values = (
                trade.get('time', ''),
                trade.get('type', '').upper(),
                f"{trade.get('vol', 0):.8f}",
                f"{symbol}{trade.get('price', 0):.2f}",
                f"{symbol}{trade.get('cost', 0):.2f}",
                f"{symbol}{trade.get('fee', 0):.4f}",
                f"{symbol}{trade.get('total', 0):.2f}",
                pnl_str,
            )
            tag = 'buy' if trade.get('type') == 'buy' else ('sell_win' if pnl >= 0 else 'sell_loss')
            self.trade_tree.insert('', 'end', values=values, tags=(tag,))

        self.trade_tree.tag_configure('buy',       foreground='#62ffc2')
        self.trade_tree.tag_configure('sell',      foreground='#ff4d4d')
        self.trade_tree.tag_configure('sell_win',  foreground='#82ef82')
        self.trade_tree.tag_configure('sell_loss', foreground='#ff4d4d')

        if hasattr(self, 'trade_count_label') and self.trade_count_label:
            self.trade_count_label.config(text=f"Trades: {len(trades)}")

        total_btc = (sum(t.get('vol', 0) for t in trades if t.get('type') == 'buy') -
                     sum(t.get('vol', 0) for t in trades if t.get('type') == 'sell'))
        if hasattr(self, 'total_btc_label_status') and self.total_btc_label_status:
            self.total_btc_label_status.config(text=f"BTC {total_btc:.8f}")

    # ── Chart update methods ───────────────────────────────────────────────────

    def update_charts(self):
        """Aktualisiert alle Charts"""
        self.update_stash_chart()
        self.update_unrealized_chart()
        self.update_portfolio_value_chart()
        self.update_realized_chart()

    def update_stash_chart(self):
        """Aktualisiert den BTC Stash Graph"""
        if not hasattr(self, 'stash_ax') or self.stash_ax is None:
            return

        self.stash_ax.clear()
        self.stash_ax.set_facecolor('#212121')

        if not trades:
            self.stash_ax.text(0.5, 0.5, "No trades to display",
                               color='grey', ha='center', va='center',
                               transform=self.stash_ax.transAxes, fontsize=11)
            if hasattr(self, 'stash_canvas'):
                self.stash_canvas.draw()
            return

        sorted_trades = sorted(trades, key=lambda x: x.get('datetime', datetime.now()))

        dates        = []
        stash_values = []
        buy_dates    = []
        buy_volumes  = []
        sell_dates   = []
        sell_volumes = []
        current_stash = 0.0

        for trade in sorted_trades:
            if 'datetime' not in trade:
                continue
            dates.append(trade['datetime'])
            if trade.get('type') == 'buy':
                current_stash += trade.get('vol', 0)
                buy_dates.append(trade['datetime'])
                buy_volumes.append(current_stash)
            elif trade.get('type') == 'sell':
                current_stash -= trade.get('vol', 0)
                sell_dates.append(trade['datetime'])
                sell_volumes.append(current_stash)
            stash_values.append(current_stash)

        if dates and stash_values:
            self.stash_ax.plot(dates, stash_values, color=theme_color,
                               linewidth=1.5, alpha=0.8)
            if buy_dates:
                self.stash_ax.scatter(buy_dates, buy_volumes, color='#82ef82',
                                      s=30, marker='^', zorder=5, label='Buy')
            if sell_dates:
                self.stash_ax.scatter(sell_dates, sell_volumes, color='#ff4d4d',
                                      s=30, marker='v', zorder=5, label='Sell')
            self.stash_ax.fill_between(dates, 0, stash_values,
                                       color=theme_color, alpha=0.15)
            self.stash_ax.set_ylabel('BTC', color='grey', fontsize=9)
            self.stash_ax.grid(color='#444444', linestyle=':', linewidth=0.5, alpha=0.5)
            legend = self.stash_ax.legend(loc='upper left', facecolor='#2A2A2A',
                                          edgecolor='#444444', labelcolor='white', fontsize=9)
            legend.get_frame().set_alpha(0.9)
            if len(dates) > 1:
                self.stash_ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%y'))
                self.stash_ax.tick_params(axis='x', colors='grey', labelsize=8)
                self.stash_ax.tick_params(axis='y', colors='grey', labelsize=8)

        self.stash_fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.22)
        if hasattr(self, 'stash_canvas'):
            self.stash_canvas.draw()

    def update_realized_chart(self):
        """Aktualisiert den Realized P/L Graph"""
        if not hasattr(self, 'realized_ax') or self.realized_ax is None:
            return

        self.realized_ax.clear()
        self.realized_ax.set_facecolor('#212121')

        if not trades:
            self.realized_ax.text(0.5, 0.5, "No realized P/L from sales",
                                  color='grey', ha='center', va='center',
                                  transform=self.realized_ax.transAxes, fontsize=11)
            if hasattr(self, 'realized_canvas'):
                self.realized_canvas.draw()
            return

        sorted_trades = sorted(trades, key=lambda x: x.get('datetime', datetime.now()))

        dates          = []
        cumulative_pnl = []
        running_pnl    = 0.0

        for trade in sorted_trades:
            if 'datetime' not in trade:
                continue
            dates.append(trade['datetime'])
            if trade.get('type') == 'sell':
                pnl, _ = self.calculate_trade_pnl(trade)
                running_pnl += pnl
            cumulative_pnl.append(running_pnl)

        if dates and cumulative_pnl:
            self.realized_ax.plot(dates, cumulative_pnl, color=theme_color,
                                  linewidth=2, marker='o', markersize=4)
            self.realized_ax.fill_between(dates, 0, cumulative_pnl,
                                          where=[x >= 0 for x in cumulative_pnl],
                                          color='#82ef82', alpha=0.2)
            self.realized_ax.fill_between(dates, 0, cumulative_pnl,
                                          where=[x < 0 for x in cumulative_pnl],
                                          color='#ff4d4d', alpha=0.2)
            self.realized_ax.axhline(y=0, color='white', linestyle='--',
                                     linewidth=0.5, alpha=0.5)
            symbol = get_currency_symbol()
            self.realized_ax.set_ylabel(f'P/L ({symbol})', color='grey', fontsize=9)
            self.realized_ax.grid(color='#444444', linestyle=':', linewidth=0.5, alpha=0.5)
            if len(dates) > 1:
                self.realized_ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%y'))
                self.realized_ax.tick_params(axis='x', colors='grey', labelsize=8)
                self.realized_ax.tick_params(axis='y', colors='grey', labelsize=8)

        self.realized_fig.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.22)
        if hasattr(self, 'realized_canvas'):
            self.realized_canvas.draw()

    def update_unrealized_chart(self):
        """Aktualisiert den Unrealized P/L Graph"""
        if not hasattr(self, 'unrealized_ax') or self.unrealized_ax is None:
            return

        self.unrealized_ax.clear()
        self.unrealized_ax.set_facecolor('#212121')

        if not trades:
            self.unrealized_ax.text(0.5, 0.5, "No unrealized P/L data",
                                    color='grey', ha='center', va='center',
                                    transform=self.unrealized_ax.transAxes, fontsize=11)
            if hasattr(self, 'unrealized_canvas'):
                self.unrealized_canvas.draw()
            return

        sorted_trades = sorted(trades, key=lambda x: x.get('datetime', datetime.now()))

        price_history = {}
        for trade in sorted_trades:
            if 'datetime' in trade:
                hist = self.get_historical_price_at_time(trade['datetime'])
                price_history[trade['datetime']] = hist if hist else trade.get('price', last_known_price)

        buy_queue            = []
        dates                = []
        unrealized_pnl_values = []

        for trade in sorted_trades:
            if 'datetime' not in trade:
                continue
            dates.append(trade['datetime'])
            current_price_at_time = price_history.get(trade['datetime'],
                                                       trade.get('price', last_known_price))
            if trade.get('type') == 'buy':
                buy_queue.append({
                    'btc':          trade.get('vol', 0),
                    'original_btc': trade.get('vol', 0),
                    'price':        trade.get('price', 0),
                    'fee':          trade.get('fee', 0),
                })
            elif trade.get('type') == 'sell':
                remaining = trade.get('vol', 0)
                while remaining > 0 and buy_queue:
                    buy = buy_queue[0]
                    sold = min(buy['btc'], remaining)
                    buy['btc'] -= sold
                    remaining  -= sold
                    if buy['btc'] <= 1e-8:
                        buy_queue.pop(0)

            total_btc_held  = sum(b['btc'] for b in buy_queue)
            total_invested  = sum(b['btc'] * b['price'] for b in buy_queue)
            current_value   = total_btc_held * current_price_at_time
            unrealized_pnl_values.append(current_value - total_invested)

        if dates and unrealized_pnl_values:
            self.unrealized_ax.plot(dates, unrealized_pnl_values, color='#62edff',
                                    linewidth=2, marker='s', markersize=4)
            self.unrealized_ax.fill_between(dates, 0, unrealized_pnl_values,
                                            where=[x >= 0 for x in unrealized_pnl_values],
                                            color='#82ef82', alpha=0.2)
            self.unrealized_ax.fill_between(dates, 0, unrealized_pnl_values,
                                            where=[x < 0 for x in unrealized_pnl_values],
                                            color='#ff4d4d', alpha=0.2)
            self.unrealized_ax.axhline(y=0, color='white', linestyle='--',
                                       linewidth=0.5, alpha=0.5)
            symbol = get_currency_symbol()
            self.unrealized_ax.set_ylabel(f'Unrealized ({symbol})', color='grey', fontsize=9)
            self.unrealized_ax.grid(color='#444444', linestyle=':', linewidth=0.5, alpha=0.5)
            if len(dates) > 1:
                self.unrealized_ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%y'))
                self.unrealized_ax.tick_params(axis='x', colors='grey', labelsize=8)
                self.unrealized_ax.tick_params(axis='y', colors='grey', labelsize=8)

        self.unrealized_fig.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.22)
        if hasattr(self, 'unrealized_canvas'):
            self.unrealized_canvas.draw()

    def update_portfolio_value_chart(self):
        """
        Aktualisiert den Portfolio Value in Fiat Chart.
        Jeder Trade ist ein Datenpunkt. Der Portfoliowert zum Zeitpunkt
        des Trades wird als: (kumuliertes BTC nach Trade) * (Tradingpreis) berechnet.
        """
        if not hasattr(self, 'portfolio_value_ax') or self.portfolio_value_ax is None:
            return

        self.portfolio_value_ax.clear()
        self.portfolio_value_ax.set_facecolor('#212121')

        if not trades:
            self.portfolio_value_ax.text(0.5, 0.5, "No trades to display",
                                         color='grey', ha='center', va='center',
                                         transform=self.portfolio_value_ax.transAxes, fontsize=11)
            if hasattr(self, 'portfolio_value_canvas'):
                self.portfolio_value_canvas.draw()
            return

        sorted_trades = sorted(trades, key=lambda x: x.get('datetime', datetime.now()))

        dates            = []
        portfolio_values = []
        buy_points       = []
        sell_points      = []
        current_btc      = 0.0

        for trade in sorted_trades:
            if 'datetime' not in trade:
                continue
            trade_price = trade.get('price', 0)
            if trade_price <= 0:
                continue

            if trade.get('type') == 'buy':
                current_btc += trade.get('vol', 0)
            elif trade.get('type') == 'sell':
                current_btc -= trade.get('vol', 0)

            value = current_btc * trade_price
            dates.append(trade['datetime'])
            portfolio_values.append(value)

            if trade.get('type') == 'buy':
                buy_points.append((trade['datetime'], value))
            else:
                sell_points.append((trade['datetime'], value))

        if not dates:
            self.portfolio_value_ax.text(0.5, 0.5, "No valid data points",
                                         color='grey', ha='center', va='center',
                                         transform=self.portfolio_value_ax.transAxes, fontsize=11)
            if hasattr(self, 'portfolio_value_canvas'):
                self.portfolio_value_canvas.draw()
            return

        self.portfolio_value_ax.plot(dates, portfolio_values,
                                     color='#DAA520', linewidth=1.5, alpha=0.9)
        self.portfolio_value_ax.fill_between(dates, 0, portfolio_values,
                                              color='#DAA520', alpha=0.12)

        if buy_points:
            bx, by = zip(*buy_points)
            self.portfolio_value_ax.scatter(bx, by, color='#82ef82',
                                            s=35, marker='^', zorder=5, label='Buy')
        if sell_points:
            sx, sy = zip(*sell_points)
            self.portfolio_value_ax.scatter(sx, sy, color='#ff4d4d',
                                            s=35, marker='v', zorder=5, label='Sell')

        symbol = get_currency_symbol()
        self.portfolio_value_ax.set_ylabel(f'Value ({symbol})', color='grey', fontsize=9)
        self.portfolio_value_ax.grid(color='#444444', linestyle=':', linewidth=0.5, alpha=0.5)

        legend = self.portfolio_value_ax.legend(
            loc='upper left', facecolor='#2A2A2A',
            edgecolor='#444444', labelcolor='white', fontsize=9)
        legend.get_frame().set_alpha(0.9)

        if len(dates) > 1:
            self.portfolio_value_ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%y'))
            self.portfolio_value_ax.tick_params(axis='x', colors='grey', labelsize=8)
            self.portfolio_value_ax.tick_params(axis='y', colors='grey', labelsize=8)

        self.portfolio_value_fig.subplots_adjust(left=0.10, right=0.97, top=0.88, bottom=0.22)
        if hasattr(self, 'portfolio_value_canvas'):
            self.portfolio_value_canvas.draw()

    # ── Safe tooltip placement ────────────────────────────────────────────────

    def _safe_tooltip_offset(self, ax, x_data, y_data):
        """
        Berechnet einen sicheren Offset fuer den Tooltip, damit dieser
        niemals ausserhalb der Axes-Grenzen abgeschnitten wird.
        Gibt (ha, va, xytext) zurueck.
        """
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()

        x_range = xlim[1] - xlim[0] if xlim[1] != xlim[0] else 1.0
        y_range = ylim[1] - ylim[0] if ylim[1] != ylim[0] else 1.0

        x_frac = (x_data - xlim[0]) / x_range
        y_frac = (y_data - ylim[0]) / y_range

        # Horizontal: rechts der Mitte -> links ausrichten, links -> rechts
        if x_frac > 0.6:
            ha    = 'right'
            x_off = -12
        else:
            ha    = 'left'
            x_off = 12

        # Vertikal: oben -> nach unten, unten -> nach oben
        if y_frac > 0.6:
            va    = 'top'
            y_off = -12
        else:
            va    = 'bottom'
            y_off = 12

        return ha, va, (x_off, y_off)

    # ── Hover: Stash chart ────────────────────────────────────────────────────

    def on_stash_hover(self, event):
        if event.inaxes != self.stash_ax:
            self._clear_chart_hover('stash')
            return
        if not hasattr(event, 'xdata') or event.xdata is None:
            return
        for trade in trades:
            if 'datetime' in trade:
                if abs(event.xdata - mdates.date2num(trade['datetime'])) < 0.3:
                    self._show_stash_tooltip(trade)
                    return

    def _show_stash_tooltip(self, trade):
        self._clear_chart_hover('stash')
        symbol = get_currency_symbol()
        date_str = trade['datetime'].strftime('%d.%m.%Y %H:%M')
        vol   = trade.get('vol', 0)
        price = trade.get('price', 0)
        total = vol * price

        current_stash = 0.0
        for t in sorted(trades, key=lambda x: x.get('datetime', datetime.now())):
            if t['datetime'] <= trade['datetime']:
                if t.get('type') == 'buy':
                    current_stash += t.get('vol', 0)
                else:
                    current_stash -= t.get('vol', 0)

        x = mdates.date2num(trade['datetime'])
        ha, va, xytext = self._safe_tooltip_offset(self.stash_ax, x, current_stash)

        self.stash_line = self.stash_ax.axvline(
            x=x, color='white', linestyle='--', linewidth=1, alpha=0.7, zorder=10)

        tooltip_text = (
            f"{date_str}\n"
            f"{trade.get('type', '').upper()}\n"
            f"{vol:.8f} BTC\n"
            f"{symbol}{price:.2f} / BTC\n"
            f"Total: {symbol}{total:.2f}\n"
            f"Held after: {current_stash:.8f} BTC"
        )
        self.stash_annotation = self.stash_ax.annotate(
            tooltip_text,
            xy=(x, current_stash),
            xytext=xytext,
            textcoords='offset points',
            annotation_clip=False,
            bbox=dict(boxstyle='round,pad=0.5', fc='#2A2A2A', ec=theme_color, alpha=0.97),
            color='white', fontsize=9,
            ha=ha, va=va,
            zorder=20,
        )
        self.stash_canvas.draw_idle()
        if hasattr(self, 'stash_hover_timer'):
            self.stash_canvas.get_tk_widget().after_cancel(self.stash_hover_timer)
        self.stash_hover_timer = self.stash_canvas.get_tk_widget().after(
            4000, lambda: self._clear_chart_hover('stash'))

    # ── Hover: Unrealized chart ───────────────────────────────────────────────

    def on_unrealized_hover(self, event):
        if event.inaxes != self.unrealized_ax:
            self._clear_chart_hover('unrealized')
            return
        if not hasattr(event, 'xdata') or event.xdata is None:
            return

        price_history = {}
        for trade in trades:
            if 'datetime' in trade:
                hist = self.get_historical_price_at_time(trade['datetime'])
                price_history[trade['datetime']] = hist if hist else trade.get('price', last_known_price)

        sorted_trades = sorted(trades, key=lambda x: x.get('datetime', datetime.now()))
        for i, trade in enumerate(sorted_trades):
            if 'datetime' in trade:
                if abs(event.xdata - mdates.date2num(trade['datetime'])) < 0.3:
                    self._show_unrealized_tooltip(trade, i, sorted_trades, price_history)
                    return

    def _show_unrealized_tooltip(self, trade, index, all_trades, price_history):
        self._clear_chart_hover('unrealized')

        buy_queue = []
        for t in all_trades[:index + 1]:
            if t.get('type') == 'buy':
                buy_queue.append({
                    'btc':          t.get('vol', 0),
                    'original_btc': t.get('vol', 0),
                    'price':        t.get('price', 0),
                    'fee':          t.get('fee', 0),
                })
            elif t.get('type') == 'sell':
                remaining = t.get('vol', 0)
                while remaining > 0 and buy_queue:
                    buy = buy_queue[0]
                    sold = min(buy['btc'], remaining)
                    buy['btc'] -= sold
                    remaining  -= sold
                    if buy['btc'] <= 1e-8:
                        buy_queue.pop(0)

        current_price_at_time = price_history.get(trade['datetime'],
                                                    trade.get('price', last_known_price))
        total_btc_held = sum(b['btc'] for b in buy_queue)
        total_invested = sum(b['btc'] * b['price'] for b in buy_queue)
        unrealized     = total_btc_held * current_price_at_time - total_invested

        symbol   = get_currency_symbol()
        date_str = trade['datetime'].strftime('%d.%m.%Y %H:%M')
        x        = mdates.date2num(trade['datetime'])
        ha, va, xytext = self._safe_tooltip_offset(self.unrealized_ax, x, unrealized)

        self.unrealized_line = self.unrealized_ax.axvline(
            x=x, color='white', linestyle='--', linewidth=1, alpha=0.7, zorder=10)

        tooltip_text = (
            f"{date_str}\n"
            f"{trade.get('type', '').upper()}\n"
            f"{trade.get('vol', 0):.8f} BTC @ {symbol}{trade.get('price', 0):.2f}\n"
            f"Unrealized: {symbol}{unrealized:+.2f}\n"
            f"BTC held: {total_btc_held:.8f}\n"
            f"Price at trade: {symbol}{current_price_at_time:.2f}"
        )
        self.unrealized_annotation = self.unrealized_ax.annotate(
            tooltip_text,
            xy=(x, unrealized),
            xytext=xytext,
            textcoords='offset points',
            annotation_clip=False,
            bbox=dict(boxstyle='round,pad=0.5', fc='#2A2A2A', ec='#62edff', alpha=0.97),
            color='white', fontsize=9,
            ha=ha, va=va,
            zorder=20,
        )
        self.unrealized_canvas.draw_idle()
        if hasattr(self, 'unrealized_hover_timer'):
            self.unrealized_canvas.get_tk_widget().after_cancel(self.unrealized_hover_timer)
        self.unrealized_hover_timer = self.unrealized_canvas.get_tk_widget().after(
            4000, lambda: self._clear_chart_hover('unrealized'))

    # ── Hover: Portfolio Value chart ──────────────────────────────────────────

    def on_portfolio_value_hover(self, event):
        if event.inaxes != self.portfolio_value_ax:
            self._clear_chart_hover('portfolio_value')
            return
        if not hasattr(event, 'xdata') or event.xdata is None:
            return

        sorted_trades = sorted(trades, key=lambda x: x.get('datetime', datetime.now()))
        current_btc   = 0.0

        for trade in sorted_trades:
            if 'datetime' not in trade:
                continue
            if trade.get('price', 0) <= 0:
                continue
            if trade.get('type') == 'buy':
                current_btc += trade.get('vol', 0)
            else:
                current_btc -= trade.get('vol', 0)
            value = current_btc * trade.get('price', 0)

            if abs(event.xdata - mdates.date2num(trade['datetime'])) < 0.3:
                self._show_portfolio_value_tooltip(trade, current_btc, value)
                return

    def _show_portfolio_value_tooltip(self, trade, btc_held, fiat_value):
        self._clear_chart_hover('portfolio_value')

        symbol   = get_currency_symbol()
        date_str = trade['datetime'].strftime('%d.%m.%Y %H:%M')
        x        = mdates.date2num(trade['datetime'])
        ha, va, xytext = self._safe_tooltip_offset(self.portfolio_value_ax, x, fiat_value)

        self.portfolio_value_line = self.portfolio_value_ax.axvline(
            x=x, color='white', linestyle='--', linewidth=1, alpha=0.7, zorder=10)

        tooltip_text = (
            f"{date_str}\n"
            f"{trade.get('type', '').upper()}\n"
            f"{trade.get('vol', 0):.8f} BTC\n"
            f"Trade price: {symbol}{trade.get('price', 0):.2f}\n"
            f"Portfolio value: {symbol}{fiat_value:.2f}\n"
            f"BTC held: {btc_held:.8f}"
        )
        self.portfolio_value_annotation = self.portfolio_value_ax.annotate(
            tooltip_text,
            xy=(x, fiat_value),
            xytext=xytext,
            textcoords='offset points',
            annotation_clip=False,
            bbox=dict(boxstyle='round,pad=0.5', fc='#2A2A2A', ec='#DAA520', alpha=0.97),
            color='white', fontsize=9,
            ha=ha, va=va,
            zorder=20,
        )
        self.portfolio_value_canvas.draw_idle()
        if hasattr(self, 'portfolio_value_hover_timer'):
            self.portfolio_value_canvas.get_tk_widget().after_cancel(self.portfolio_value_hover_timer)
        self.portfolio_value_hover_timer = self.portfolio_value_canvas.get_tk_widget().after(
            4000, lambda: self._clear_chart_hover('portfolio_value'))

    # ── Hover: Realized chart ─────────────────────────────────────────────────

    def on_realized_hover(self, event):
        if event.inaxes != self.realized_ax:
            self._clear_chart_hover('realized')
            return
        if not hasattr(event, 'xdata') or event.xdata is None:
            return

        sell_trades = sorted([t for t in trades if t.get('type') == 'sell'],
                             key=lambda x: x.get('datetime', datetime.now()))
        running_pnl = 0.0
        for trade in sell_trades:
            if 'datetime' not in trade:
                continue
            pnl, pnl_pct = self.calculate_trade_pnl(trade)
            running_pnl += pnl
            if abs(event.xdata - mdates.date2num(trade['datetime'])) < 0.3:
                self._show_realized_tooltip(trade, pnl, pnl_pct, running_pnl)
                return

    def _show_realized_tooltip(self, trade, pnl, pnl_pct, cumulative):
        self._clear_chart_hover('realized')

        symbol   = get_currency_symbol()
        date_str = trade['datetime'].strftime('%d.%m.%Y %H:%M')
        vol      = trade.get('vol', 0)
        price    = trade.get('price', 0)
        x        = mdates.date2num(trade['datetime'])
        ha, va, xytext = self._safe_tooltip_offset(self.realized_ax, x, cumulative)

        self.realized_line = self.realized_ax.axvline(
            x=x, color='white', linestyle='--', linewidth=1, alpha=0.7, zorder=10)

        tooltip_text = (
            f"{date_str}\n"
            f"SELL\n"
            f"{vol:.8f} BTC @ {symbol}{price:.2f}\n"
            f"P/L: {symbol}{pnl:+.2f} ({pnl_pct:+.1f}%)\n"
            f"Cumulative: {symbol}{cumulative:+.2f}"
        )
        self.realized_annotation = self.realized_ax.annotate(
            tooltip_text,
            xy=(x, cumulative),
            xytext=xytext,
            textcoords='offset points',
            annotation_clip=False,
            bbox=dict(boxstyle='round,pad=0.5', fc='#2A2A2A', ec=theme_color, alpha=0.97),
            color='white', fontsize=9,
            ha=ha, va=va,
            zorder=20,
        )
        self.realized_canvas.draw_idle()
        if hasattr(self, 'realized_hover_timer'):
            self.realized_canvas.get_tk_widget().after_cancel(self.realized_hover_timer)
        self.realized_hover_timer = self.realized_canvas.get_tk_widget().after(
            4000, lambda: self._clear_chart_hover('realized'))

    # ── Universal hover cleanup ───────────────────────────────────────────────

    def _clear_chart_hover(self, chart_name):
        """Entfernt Hover-Elemente eines bestimmten Charts"""
        annotation_attr = f'{chart_name}_annotation'
        line_attr       = f'{chart_name}_line'
        canvas_attr     = f'{chart_name}_canvas'

        for attr in (annotation_attr, line_attr):
            if hasattr(self, attr):
                try:
                    getattr(self, attr).remove()
                except Exception:
                    pass
                try:
                    delattr(self, attr)
                except Exception:
                    pass

        if hasattr(self, canvas_attr):
            try:
                getattr(self, canvas_attr).draw_idle()
            except Exception:
                pass

    # ── Portfolio statistics ──────────────────────────────────────────────────

    def update_portfolio_stats(self):
        """Aktualisiert die Portfolio-Statistiken"""
        global portfolio_data

        if not hasattr(self, 'total_invested_excl_fees_label') or \
                self.total_invested_excl_fees_label is None:
            return

        buy_queue         = []
        total_btc_bought  = 0.0
        total_btc_sold    = 0.0
        total_fees_paid   = 0.0
        total_pnl_realized = 0.0
        winning_trades    = 0
        losing_trades     = 0
        largest_win       = 0.0
        largest_loss      = 0.0

        sorted_trades = sorted(trades, key=lambda x: x.get('datetime', datetime.now()))

        for trade in sorted_trades:
            trade_type = trade.get('type', '').lower()
            vol   = float(trade.get('vol', 0))
            price = float(trade.get('price', 0))
            fee   = float(trade.get('fee', 0))

            total_fees_paid += fee

            if trade_type == 'buy':
                buy_queue.append({
                    'btc':          vol,
                    'original_btc': vol,
                    'price':        price,
                    'fee':          fee,
                })
                total_btc_bought += vol

            elif trade_type == 'sell':
                remaining      = vol
                total_btc_sold += vol

                while remaining > 0 and buy_queue:
                    buy         = buy_queue[0]
                    sell_amount = min(buy['btc'], remaining)
                    cost_basis  = sell_amount * buy['price']
                    fee_prop    = ((sell_amount / buy['original_btc']) * buy['fee']
                                   if buy['original_btc'] > 0 else 0)
                    pnl = (sell_amount * price) - cost_basis - fee_prop
                    total_pnl_realized += pnl

                    if pnl > 0:
                        winning_trades += 1
                        largest_win     = max(largest_win, pnl)
                    elif pnl < 0:
                        losing_trades += 1
                        largest_loss   = min(largest_loss, pnl)

                    buy['btc'] -= sell_amount
                    remaining  -= sell_amount
                    if buy['btc'] <= 1e-8:
                        buy_queue.pop(0)

        total_btc_current = total_btc_bought - total_btc_sold
        current_price     = last_known_price if last_known_price > 0 else 0
        current_value     = total_btc_current * current_price

        total_invested_excl_fees = 0.0
        total_invested_incl_fees = 0.0
        for buy in buy_queue:
            if buy['btc'] > 0:
                total_invested_excl_fees += buy['btc'] * buy['price']
                fee_prop = (buy['fee'] * (buy['btc'] / buy['original_btc'])
                            if buy['original_btc'] > 0 else 0)
                total_invested_incl_fees += buy['btc'] * buy['price'] + fee_prop

        avg_price_excl_fees = (total_invested_excl_fees / total_btc_current
                               if total_btc_current > 0 and buy_queue else 0)
        avg_price_incl_fees = (total_invested_incl_fees / total_btc_current
                               if total_btc_current > 0 and buy_queue else 0)

        unrealized_pnl = current_value - total_invested_incl_fees
        unrealized_pnl_pct = ((unrealized_pnl / total_invested_incl_fees) * 100
                               if total_invested_incl_fees > 0 else 0)

        total_cost_sold = sum(t.get('cost', 0) for t in sorted_trades
                              if t.get('type') == 'sell'
                              and self.calculate_trade_pnl(t)[0] != 0)
        realized_pnl_pct = ((total_pnl_realized / total_cost_sold) * 100
                             if total_cost_sold > 0 else 0)

        total_pnl     = total_pnl_realized + unrealized_pnl
        total_cost_all = total_invested_incl_fees + total_cost_sold
        total_pnl_pct  = ((total_pnl / total_cost_all) * 100
                           if total_cost_all > 0 else 0)

        symbol = get_currency_symbol()

        self.total_invested_excl_fees_label.config(text=f"{symbol}{total_invested_excl_fees:.2f}")
        self.total_fees_label.config(text=f"{symbol}{total_fees_paid:.2f}")
        self.total_cost_label.config(text=f"{symbol}{total_invested_incl_fees:.2f}")
        self.total_value_label.config(text=f"{symbol}{current_value:.2f}")

        realized_color = "#82ef82" if total_pnl_realized >= 0 else "#ff4d4d"
        self.realized_pnl_label.config(
            text=f"{symbol}{total_pnl_realized:+.2f} ({realized_pnl_pct:+.1f}%)",
            fg=realized_color)

        unrealized_color = "#82ef82" if unrealized_pnl >= 0 else "#ff4d4d"
        self.unrealized_pnl_label.config(
            text=f"{symbol}{unrealized_pnl:+.2f} ({unrealized_pnl_pct:+.1f}%)",
            fg=unrealized_color)

        total_pnl_color = "#82ef82" if total_pnl >= 0 else "#ff4d4d"
        self.total_pnl_label.config(
            text=f"{symbol}{total_pnl:+.2f} ({total_pnl_pct:+.1f}%)",
            fg=total_pnl_color)

        self.total_btc_label.config(text=f"{total_btc_current:.8f} BTC")
        self.win_loss_label.config(text=f"{winning_trades} / {losing_trades}")
        self.avg_price_excl_fees_label.config(text=f"{symbol}{avg_price_excl_fees:.2f}")
        self.avg_price_incl_fees_label.config(text=f"{symbol}{avg_price_incl_fees:.2f}")
        self.largest_win_label.config(text=f"{symbol}{largest_win:.2f}")
        self.largest_loss_label.config(text=f"{symbol}{abs(largest_loss):.2f}")

        if hasattr(self, 'trade_count_label') and self.trade_count_label:
            self.trade_count_label.config(text=f"Trades: {len(trades)}")
        if hasattr(self, 'total_btc_label_status') and self.total_btc_label_status:
            self.total_btc_label_status.config(text=f"BTC {total_btc_current:.8f}")

    def calculate_trade_pnl(self, trade):
        """Berechnet P/L fuer einen einzelnen Trade (FIFO)"""
        if trade.get('type') != 'sell':
            return 0.0, 0.0

        buy_trades = sorted(
            [t for t in trades
             if t.get('type') == 'buy'
             and t.get('datetime', datetime.now()) < trade.get('datetime', datetime.now())],
            key=lambda x: x.get('datetime', datetime.now())
        )

        remaining  = trade.get('vol', 0)
        total_cost = 0.0
        total_btc  = 0.0
        total_fees = 0.0

        temp_queue = [{'btc': b.get('vol', 0), 'original_btc': b.get('vol', 0),
                       'price': b.get('price', 0), 'fee': b.get('fee', 0)}
                      for b in buy_trades]

        while remaining > 0 and temp_queue:
            buy         = temp_queue[0]
            sell_amount = min(buy['btc'], remaining)
            fee_prop    = ((sell_amount / buy['original_btc']) * buy['fee']
                           if buy['original_btc'] > 0 else 0)
            total_cost += sell_amount * buy['price']
            total_btc  += sell_amount
            total_fees += fee_prop
            buy['btc'] -= sell_amount
            remaining  -= sell_amount
            if buy['btc'] <= 1e-8:
                temp_queue.pop(0)

        if total_btc > 0:
            avg_cost = total_cost / total_btc
            pnl      = trade.get('vol', 0) * trade.get('price', 0) - total_cost - total_fees
            pnl_pct  = ((trade.get('price', 0) - avg_cost) / avg_cost) * 100
            return pnl, pnl_pct

        return 0.0, 0.0

    def save_trades(self):
        """Speichert Trades in Datei"""
        try:
            with open(TRADES_FILE, "w") as f:
                for trade in trades:
                    line = (f"{trade.get('time', '')}|{trade.get('type', '')}|"
                            f"{trade.get('vol', 0)}|{trade.get('price', 0)}|"
                            f"{trade.get('cost', 0)}|{trade.get('fee', 0)}|"
                            f"{trade.get('pair', '')}|{trade.get('ordertype', '')}|"
                            f"{trade.get('txid', '')}|{trade.get('ordertxid', '')}\n")
                    f.write(line)
            print(f"Saved {len(trades)} trades to file")
        except Exception as e:
            print(f"Error saving trades: {e}")

    def collapse(self):
        """Schliesst das erweiterte Fenster"""
        self.is_expanded = False
        self.portfolio_button.config(text="P/L")

        if self.expanded_window:
            try:
                x = self.expanded_window.winfo_x()
                y = self.expanded_window.winfo_y()
                save_attached_window_pos('portfolio', x, y)
            except Exception:
                pass
            if hasattr(self, 'canvas'):
                self.canvas.unbind_all("<MouseWheel>")
            self.expanded_window.destroy()
            self.expanded_window = None

# ====== ENHANCED OPTIONS WINDOW ======
def open_options():
    """Verbesserte Options-Fenster mit mehr Einstellungen"""
    global theme_color, current_time_range, CURRENCY
    
    options_window = tk.Toplevel(root)
    options_window.overrideredirect(1)
    options_window.geometry("500x700")
    options_window.config(bg="#212121")

    def on_drag_start(event):
        options_window.x = event.x
        options_window.y = event.y

    def on_drag_motion(event):
        deltax = event.x - options_window.x
        deltay = event.y - options_window.y
        x = options_window.winfo_x() + deltax
        y = options_window.winfo_y() + deltay
        options_window.geometry(f"+{x}+{y}")

    options_window.bind('<Button-1>', on_drag_start)
    options_window.bind('<B1-Motion>', on_drag_motion)

    # Movebar
    movebar = tk.Frame(options_window, bg="#2A2A2A", height=30, cursor="fleur")
    movebar.pack(fill="x", side="top")
    movebar.pack_propagate(False)
    
    tk.Label(movebar, text="⚙️ Settings", bg="#2A2A2A", fg=theme_color, 
            font=("Arial", 12, "bold")).pack(side="left", padx=10, pady=5)
    
    close_btn = tk.Button(movebar, text="✕", command=options_window.destroy, 
                         bg="#2A2A2A", fg="white", bd=0, font=('Arial', 12, 'bold'))
    close_btn.pack(side="right", padx=10, pady=5)
    
    close_btn.bind("<Enter>", lambda e: close_btn.config(bg="#BD5959"))
    close_btn.bind("<Leave>", lambda e: close_btn.config(bg="#2A2A2A"))

    # Hauptcontainer mit Scrollbar
    main_frame = tk.Frame(options_window, bg="#212121")
    main_frame.pack(fill="both", expand=True, padx=20, pady=10)

    # Canvas für Scrolling
    canvas = tk.Canvas(main_frame, bg="#212121", highlightthickness=0)
    scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview,
                            bg="#333333", troughcolor="#212121")
    scrollable_frame = tk.Frame(canvas, bg="#212121")

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Mousewheel Scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # Currency Section
    currency_frame = tk.LabelFrame(scrollable_frame, text="💱 Currency Settings", 
                                  bg="#212121", fg="white", font=("Arial", 11, "bold"),
                                  padx=10, pady=10)
    currency_frame.pack(fill="x", pady=5)

    currency_var = tk.StringVar(value=CURRENCY)

    radio_frame = tk.Frame(currency_frame, bg="#212121")
    radio_frame.pack(pady=5)

    eur_radio = tk.Radiobutton(radio_frame, text="€ EUR (Euro)", variable=currency_var, value="EUR",
                              bg="#212121", fg="white", selectcolor=theme_color,
                              font=("Arial", 10))
    eur_radio.pack(side="left", padx=20)

    usd_radio = tk.Radiobutton(radio_frame, text="$ USD (US Dollar)", variable=currency_var, value="USD",
                              bg="#212121", fg="white", selectcolor=theme_color,
                              font=("Arial", 10))
    usd_radio.pack(side="left", padx=20)

    # Theme Section
    theme_frame = tk.LabelFrame(scrollable_frame, text="🎨 Theme Settings", 
                               bg="#212121", fg="white", font=("Arial", 11, "bold"),
                               padx=10, pady=10)
    theme_frame.pack(fill="x", pady=5)

    tk.Label(theme_frame, text="Select Theme Color:", bg="#212121", fg="grey",
            font=("Arial", 10)).pack(pady=5)

    # Color Picker Grid
    color_grid = tk.Frame(theme_frame, bg="#212121")
    color_grid.pack(pady=5)

    all_colors = preset_colors + custom_colors[:10]
    for i, color in enumerate(all_colors):
        row = i // 5
        col = i % 5
        btn = tk.Button(color_grid, bg=color, width=3, height=1,
                       command=lambda c=color: [set_theme_color(c), options_window.destroy()])
        btn.grid(row=row, column=col, padx=2, pady=2)
        
        # Hover-Effekt
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg=HOVER_COLOR))
        btn.bind("<Leave>", lambda e, b=btn, c=color: b.config(bg=c))

    # Time Range Section
    time_frame = tk.LabelFrame(scrollable_frame, text="⏰ Default Time Range", 
                              bg="#212121", fg="white", font=("Arial", 11, "bold"),
                              padx=10, pady=10)
    time_frame.pack(fill="x", pady=5)

    time_range_options_var = tk.StringVar(value=current_time_range)

    # Grid für Time Ranges
    time_grid = tk.Frame(time_frame, bg="#212121")
    time_grid.pack(pady=5)

    ranges = list(TIME_RANGES.keys())
    for i, range_name in enumerate(ranges):
        row = i // 4
        col = i % 4
        rb = tk.Radiobutton(time_grid, text=range_name, variable=time_range_options_var, 
                           value=range_name, bg="#212121", fg="white", 
                           selectcolor=theme_color, font=("Arial", 9))
        rb.grid(row=row, column=col, sticky="w", padx=10, pady=2)

    # Average Price Section
    avg_price_frame = tk.LabelFrame(scrollable_frame, text="📊 Average Buy Price", 
                                   bg="#212121", fg="white", font=("Arial", 11, "bold"),
                                   padx=10, pady=10)
    avg_price_frame.pack(fill="x", pady=5)

    price_frame = tk.Frame(avg_price_frame, bg="#212121")
    price_frame.pack(pady=5)

    tk.Label(price_frame, text="Your avg. buy price:", bg="#212121", fg="grey",
            font=("Arial", 10)).pack(side="left", padx=5)

    avg_price_var = tk.StringVar(value=str(load_avg_price()))
    avg_entry = tk.Entry(price_frame, textvariable=avg_price_var, width=15,
                        bg="#2A2A2A", fg="white", insertbackground="white",
                        font=("Arial", 10), bd=0)
    avg_entry.pack(side="left", padx=5)

    symbol_label = tk.Label(price_frame, text=get_currency_symbol(), 
                           bg="#212121", fg="white", font=("Arial", 10))
    symbol_label.pack(side="left")

    # BTC Amount Section
    btc_amount_frame = tk.LabelFrame(scrollable_frame, text="₿ Default BTC Amount", 
                                    bg="#212121", fg="white", font=("Arial", 11, "bold"),
                                    padx=10, pady=10)
    btc_amount_frame.pack(fill="x", pady=5)

    btc_frame = tk.Frame(btc_amount_frame, bg="#212121")
    btc_frame.pack(pady=5)

    tk.Label(btc_frame, text="Default BTC amount:", bg="#212121", fg="grey",
            font=("Arial", 10)).pack(side="left", padx=5)

    btc_amount_var = tk.StringVar(value=str(load_btc_value()))
    btc_entry_opt = tk.Entry(btc_frame, textvariable=btc_amount_var, width=15,
                            bg="#2A2A2A", fg="white", insertbackground="white",
                            font=("Arial", 10), bd=0)
    btc_entry_opt.pack(side="left", padx=5)

    tk.Label(btc_frame, text="BTC", bg="#212121", fg="white",
            font=("Arial", 10)).pack(side="left")

    # Startup Section
    startup_frame = tk.LabelFrame(scrollable_frame, text="🚀 Startup Settings", 
                                 bg="#212121", fg="white", font=("Arial", 11, "bold"),
                                 padx=10, pady=10)
    startup_frame.pack(fill="x", pady=5)

    start_with_windows_var = tk.IntVar(value=1 if is_startup_enabled() else 0)
    startup_check = tk.Checkbutton(startup_frame, text="Start with Windows", 
                                   variable=start_with_windows_var,
                                   bg="#212121", fg="white", selectcolor=theme_color,
                                   font=("Arial", 10))
    startup_check.pack(pady=5)

    # Data Management Section
    data_frame = tk.LabelFrame(scrollable_frame, text="💾 Data Management", 
                              bg="#212121", fg="white", font=("Arial", 11, "bold"),
                              padx=10, pady=10)
    data_frame.pack(fill="x", pady=5)

    def clear_all_data():
        if messagebox.askyesno("Clear Data", "Delete all trades and wallet data?"):
            global trades, wallet_addresses, wallet_data
            trades = []
            wallet_addresses = []
            wallet_data = {}
            save_trades()
            save_wallet_addresses()
            status_label.config(text="● All data cleared", fg="#ffb84d")

    clear_btn = tk.Button(data_frame, text="🗑️ Clear All Data", 
                         command=clear_all_data,
                         bg="#BD5959", fg="white", font=("Arial", 10),
                         padx=10, pady=5, bd=0, cursor="hand2")
    clear_btn.pack(pady=5)

    clear_btn.bind("<Enter>", lambda e: clear_btn.config(bg="#ff4d4d"))
    clear_btn.bind("<Leave>", lambda e: clear_btn.config(bg="#BD5959"))

    # Donation Section
    donation_frame = tk.LabelFrame(scrollable_frame, text="❤️ Support Development", 
                                  bg="#212121", fg="white", font=("Arial", 11, "bold"),
                                  padx=10, pady=10)
    donation_frame.pack(fill="x", pady=5)

    tk.Label(donation_frame, text="BTC Donations:", bg="#212121", fg="grey",
            font=("Arial", 10)).pack(pady=2)

    btc_address = "bc1q4df4r739n0rrqdrcdx0dlj7ukklpykgxe7ekm2"
    address_frame = tk.Frame(donation_frame, bg="#2A2A2A", 
                            highlightbackground="#444444", highlightthickness=1)
    address_frame.pack(pady=5, padx=10, fill="x")

    btc_address_entry = tk.Entry(address_frame, width=45, font=("Arial", 9),
                                bg="#2A2A2A", fg=theme_color, bd=0,
                                readonlybackground="#2A2A2A")
    btc_address_entry.insert(0, btc_address)
    btc_address_entry.config(state="readonly")
    btc_address_entry.pack(padx=5, pady=5)

    tk.Label(donation_frame, text="a program by F.S (2024)", bg="#212121", fg="grey",
            font=("Arial", 9, "bold")).pack(pady=5)

    # Status Label
    status_label = tk.Label(scrollable_frame, text="", bg="#212121", fg="grey",
                           font=("Arial", 9))
    status_label.pack(pady=5)

    # Save Button Frame
    button_frame = tk.Frame(scrollable_frame, bg="#212121")
    button_frame.pack(fill="x", pady=15)

    def save_all_settings():
        global CURRENCY, current_time_range
        
        CURRENCY = currency_var.get()
        current_time_range = time_range_options_var.get()
        set_startup(start_with_windows_var.get())
        
        # AVG Price speichern
        try:
            avg_price = float(avg_price_var.get())
            save_avg_price(avg_price)
        except ValueError:
            pass
        
        # BTC Amount speichern
        try:
            btc_amount = float(btc_amount_var.get())
            save_btc_value(btc_amount)
            btc_entry.delete(0, tk.END)
            btc_entry.insert(0, str(btc_amount))
            update_conversion()
        except ValueError:
            pass
        
        save_options_to_file()
        refresh_ui_for_currency()
        
        status_label.config(text="✓ Settings saved successfully!", fg="#82ef82")
        options_window.after(1500, options_window.destroy)

    save_btn = tk.Button(button_frame, text="💾 Save All Settings", 
                        command=save_all_settings,
                        bg=theme_color, fg="black", font=("Arial", 11, "bold"),
                        padx=20, pady=8, bd=0, cursor="hand2")
    save_btn.pack()

    cancel_btn = tk.Button(button_frame, text="✕ Cancel", 
                          command=options_window.destroy,
                          bg="#2A2A2A", fg="white", font=("Arial", 11),
                          padx=20, pady=5, bd=0, cursor="hand2")
    cancel_btn.pack(pady=5)

    # Hover-Effekte
    save_btn.bind("<Enter>", lambda e, b=save_btn: on_enter_button(e, b))
    save_btn.bind("<Leave>", lambda e, b=save_btn: on_leave_button(e, b))
    cancel_btn.bind("<Enter>", lambda e, b=cancel_btn: on_enter_dark(e, b))
    cancel_btn.bind("<Leave>", lambda e, b=cancel_btn: on_leave_dark(e, b))

def set_theme_color(color):
    """Setzt die Theme-Farbe"""
    global theme_color
    theme_color = color
    save_theme_color(color)
    update_theme()

def save_theme_color(color):
    """Speichert Theme-Farbe in Datei"""
    with open(THEME_COLOR_FILE, "w") as f:
        f.write(color)

# ====== EXPANDABLE INDICATORS WINDOW ======
class ExpandableWindow:
    def __init__(self, parent):
        self.parent = parent
        self.is_expanded = False
        self.expanded_window = None
        self.update_id = None
        
        self.expand_button = tk.Button(parent, text="<", command=self.toggle_expand,
                                      bg=theme_color, fg="black", font=("Arial", 10), width=1)
        self.expand_button.place(x=10, y=380)
        
        self.expand_button.bind("<Enter>", lambda e, b=self.expand_button: on_enter_button(e, b))
        self.expand_button.bind("<Leave>", lambda e, b=self.expand_button: on_leave_button(e, b))
    
    def toggle_expand(self):
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()
    
    def expand(self):
        self.is_expanded = True
        self.expand_button.config(text=">")
        
        self.expanded_window = tk.Toplevel(self.parent)
        self.expanded_window.overrideredirect(1)
        self.expanded_window.attributes('-topmost', True)
        self.expanded_window.config(bg="#212121")
        
        saved_x, saved_y = load_attached_window_pos('indicators')
        if saved_x is not None and saved_y is not None:
            self.expanded_window.geometry(f"400x500+{saved_x}+{saved_y}")
        else:
            main_x = self.parent.winfo_x()
            main_y = self.parent.winfo_y()
            self.expanded_window.geometry(f"400x500+{main_x-400}+{main_y}")
        
        movebar = tk.Frame(self.expanded_window, bg="#2A2A2A", height=30)
        movebar.pack(fill="x", side="top")
        movebar.pack_propagate(False)
        
        movebar_title = tk.Label(movebar, text="Indicators & Market Data", 
                                bg="#2A2A2A", fg=theme_color, 
                                font=("Arial", 12, "bold"))
        movebar_title.pack(side="left", padx=10, pady=5)
        
        close_button = tk.Button(movebar, text="✕", command=self.collapse,
                                bg="#2A2A2A", fg="white", bd=0,
                                font=("Arial", 12, "bold"))
        close_button.pack(side="right", padx=10, pady=5)
        
        def on_drag_start(event):
            self.expanded_window.x = event.x
            self.expanded_window.y = event.y

        def on_drag_motion(event):
            deltax = event.x - self.expanded_window.x
            deltay = event.y - self.expanded_window.y
            x = self.expanded_window.winfo_x() + deltax
            y = self.expanded_window.winfo_y() + deltay
            self.expanded_window.geometry(f"+{x}+{y}")

        movebar.bind("<Button-1>", on_drag_start)
        movebar.bind("<B1-Motion>", on_drag_motion)
        movebar_title.bind("<Button-1>", on_drag_start)
        movebar_title.bind("<B1-Motion>", on_drag_motion)
        
        close_button.bind("<Enter>", lambda e: close_button.config(bg="#BD5959"))
        close_button.bind("<Leave>", lambda e: close_button.config(bg="#2A2A2A"))
        
        main_container = tk.Frame(self.expanded_window, bg="#212121")
        main_container.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        indicators_frame = tk.Frame(main_container, bg="#212121")
        indicators_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(indicators_frame, text="Technical Indicators", bg="#212121", 
                fg="white", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 8))
        
        rsi_frame = tk.Frame(indicators_frame, bg="#212121")
        rsi_frame.pack(fill="x", pady=3)
        
        tk.Label(rsi_frame, text="RSI (14):", bg="#212121", fg="grey", 
                font=("Arial", 10)).pack(side="left")
        
        self.rsi_label = tk.Label(rsi_frame, text="50.0", bg="#212121", 
                                 fg="white", font=("Arial", 10, "bold"))
        self.rsi_label.pack(side="left", padx=(5, 10))
        
        self.rsi_bar_bg = tk.Frame(rsi_frame, bg="#333333", height=12, width=200)
        self.rsi_bar_bg.pack(side="left", padx=(0, 5))
        self.rsi_bar = tk.Frame(self.rsi_bar_bg, bg="#82ef82", height=12, width=100)
        self.rsi_bar.place(x=0, y=0)
        
        stoch_frame = tk.Frame(indicators_frame, bg="#212121")
        stoch_frame.pack(fill="x", pady=3)
        
        tk.Label(stoch_frame, text="Stoch RSI:", bg="#212121", fg="grey", 
                font=("Arial", 10)).pack(side="left")
        
        self.stoch_rsi_label = tk.Label(stoch_frame, text="50.0", bg="#212121", 
                                       fg="white", font=("Arial", 10, "bold"))
        self.stoch_rsi_label.pack(side="left", padx=(5, 10))
        
        self.stoch_bar_bg = tk.Frame(stoch_frame, bg="#333333", height=12, width=200)
        self.stoch_bar_bg.pack(side="left", padx=(0, 5))
        self.stoch_bar = tk.Frame(self.stoch_bar_bg, bg="#62edff", height=12, width=100)
        self.stoch_bar.place(x=0, y=0)
        
        sr_frame = tk.Frame(indicators_frame, bg="#212121")
        sr_frame.pack(fill="x", pady=5)
        
        support_frame = tk.Frame(sr_frame, bg="#212121")
        support_frame.pack(side="left", fill="x", expand=True)
        
        tk.Label(support_frame, text="Support:", bg="#212121", fg="#82ef82", 
                font=("Arial", 10, "bold")).pack(side="left")
        
        self.support_label = tk.Label(support_frame, text="Loading...", 
                                     bg="#212121", fg="#82ef82", font=("Arial", 10, "bold"))
        self.support_label.pack(side="left", padx=(5, 0))
        
        resistance_frame = tk.Frame(sr_frame, bg="#212121")
        resistance_frame.pack(side="right", fill="x", expand=True)
        
        tk.Label(resistance_frame, text="Resistance:", bg="#212121", fg="#ff4d4d", 
                font=("Arial", 10, "bold")).pack(side="left")
        
        self.resistance_label = tk.Label(resistance_frame, text="Loading...", 
                                        bg="#212121", fg="#ff4d4d", font=("Arial", 10, "bold"))
        self.resistance_label.pack(side="left", padx=(5, 0))
        
        psych_frame = tk.Frame(indicators_frame, bg="#212121")
        psych_frame.pack(fill="x", pady=3)
        
        tk.Label(psych_frame, text="Psychological:", bg="#212121", fg="grey", 
                font=("Arial", 9)).pack(side="left")
        
        self.psych_levels_label = tk.Label(psych_frame, text="...", bg="#212121", 
                                          fg="white", font=("Arial", 9))
        self.psych_levels_label.pack(side="left", padx=(5, 0))
        
        separator = tk.Frame(main_container, height=2, bg=theme_color)
        separator.pack(fill="x", pady=10)
        
        fees_frame = tk.Frame(main_container, bg="#212121")
        fees_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(fees_frame, text="Mempool Fees (sats/vB)", bg="#212121", 
                fg="white", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 8))
        
        next_block_frame = tk.Frame(fees_frame, bg="#212121")
        next_block_frame.pack(fill="x", pady=2)
        
        tk.Label(next_block_frame, text="▪ Next Block:", bg="#212121", fg="#5AA36F", 
                font=("Arial", 10)).pack(side="left")
        
        self.fees_next_block_label = tk.Label(next_block_frame, text="x s/vB", 
                                             bg="#212121", fg="white", 
                                             font=("Arial", 10, "bold"))
        self.fees_next_block_label.pack(side="left", padx=(5, 0))
        
        blocks_2_3_frame = tk.Frame(fees_frame, bg="#212121")
        blocks_2_3_frame.pack(fill="x", pady=2)
        
        tk.Label(blocks_2_3_frame, text="▪ 2-3 Blocks (30min):", bg="#212121", fg="#ffb84d", 
                font=("Arial", 10)).pack(side="left")
        
        self.fees_2_3_blocks_label = tk.Label(blocks_2_3_frame, text="x s/vB", 
                                             bg="#212121", fg="white", 
                                             font=("Arial", 10, "bold"))
        self.fees_2_3_blocks_label.pack(side="left", padx=(5, 0))
        
        blocks_3_10_frame = tk.Frame(fees_frame, bg="#212121")
        blocks_3_10_frame.pack(fill="x", pady=2)
        
        tk.Label(blocks_3_10_frame, text="▪ 3-6 Blocks (60min):", bg="#212121", fg="#BA3D3D", 
                font=("Arial", 10)).pack(side="left")
        
        self.fees_3_10_blocks_label = tk.Label(blocks_3_10_frame, text="x s/vB", 
                                              bg="#212121", fg="white", 
                                              font=("Arial", 10, "bold"))
        self.fees_3_10_blocks_label.pack(side="left", padx=(5, 0))
        
        separator2 = tk.Frame(main_container, height=2, bg=theme_color)
        separator2.pack(fill="x", pady=10)
        
        status_frame = tk.Frame(main_container, bg="#212121")
        status_frame.pack(fill="x", side="bottom")
        
        self.status_label = tk.Label(status_frame, text="● Updating", 
                                    bg="#212121", fg="#82ef82", font=("Arial", 9))
        self.status_label.pack(side="left")
        
        self.data_source_label = tk.Label(status_frame, text="Based on daily prices", 
                                         bg="#212121", fg="grey", font=("Arial", 8))
        self.data_source_label.pack(side="left", padx=(10, 0))
        
        update_button = tk.Button(status_frame, text="Update", 
                                 command=self.update_all_data,
                                 bg=theme_color, fg="black", font=("Arial", 10))
        update_button.pack(side="right")
        
        update_button.bind("<Enter>", lambda e, b=update_button: on_enter_button(e, b))
        update_button.bind("<Leave>", lambda e, b=update_button: on_leave_button(e, b))
        
        self.update_all_data()
        self.schedule_updates()
    
    def collapse(self):
        self.is_expanded = False
        self.expand_button.config(text="<")
        
        if self.expanded_window:
            try:
                x = self.expanded_window.winfo_x()
                y = self.expanded_window.winfo_y()
                save_attached_window_pos('indicators', x, y)
            except:
                pass
            
            if self.update_id:
                self.expanded_window.after_cancel(self.update_id)
            
            self.expanded_window.destroy()
            self.expanded_window = None
    
    def update_all_data(self):
        self.status_label.config(text="● Updating...", fg="#ffb84d")
        executor.submit(fetch_mempool_fees_thread)
        executor.submit(fetch_daily_prices_for_indicators_thread)
        executor.submit(fetch_market_indicators_thread)
    
    def schedule_updates(self):
        if self.is_expanded and self.expanded_window:
            self.update_id = self.expanded_window.after(30000, self.schedule_updates)
            self.update_all_data()
    
    def update_fees_display(self):
        self.fees_next_block_label.config(text=fees_next_block + " s/vB")
        self.fees_2_3_blocks_label.config(text=fees_2_3_blocks + " s/vB")
        self.fees_3_10_blocks_label.config(text=fees_3_10_blocks + " s/vB")
    
    def update_indicators_display(self):
        rsi_text = f"{rsi_value:.1f}"
        self.rsi_label.config(text=rsi_text)
        
        if rsi_value >= 70:
            rsi_color = "#ff4d4d"
        elif rsi_value >= 60:
            rsi_color = "#ffb84d"
        elif rsi_value <= 30:
            rsi_color = "#82ef82"
        elif rsi_value <= 40:
            rsi_color = "#62edff"
        else:
            rsi_color = "#ffffff"
        
        self.rsi_label.config(fg=rsi_color)
        
        rsi_bar_width = min(200, max(0, int(rsi_value * 2)))
        self.rsi_bar.config(width=rsi_bar_width, bg=rsi_color)
        
        stoch_text = f"{stoch_rsi_value:.1f}"
        self.stoch_rsi_label.config(text=stoch_text)
        
        if stoch_rsi_value >= 80:
            stoch_color = "#ff4d4d"
        elif stoch_rsi_value >= 70:
            stoch_color = "#ffb84d"
        elif stoch_rsi_value <= 20:
            stoch_color = "#82ef82"
        elif stoch_rsi_value <= 30:
            stoch_color = "#62edff"
        else:
            stoch_color = "#ffffff"
        
        self.stoch_rsi_label.config(fg=stoch_color)
        
        stoch_bar_width = min(200, max(0, int(stoch_rsi_value * 2)))
        self.stoch_bar.config(width=stoch_bar_width, bg=stoch_color)
        
        symbol = get_currency_symbol()
        if support_level > 0:
            self.support_label.config(text=f"{symbol}{support_level:.0f}" if support_level > 1000 else f"{symbol}{support_level:.2f}")
        if resistance_level > 0:
            self.resistance_label.config(text=f"{symbol}{resistance_level:.0f}" if resistance_level > 1000 else f"{symbol}{resistance_level:.2f}")
        
        if last_known_price > 0:
            psych_levels, increment = find_psychological_levels(last_known_price)
            next_support = max([l for l in psych_levels if l < last_known_price], default=last_known_price * 0.97)
            next_resistance = min([l for l in psych_levels if l > last_known_price], default=last_known_price * 1.03)
            
            support_text = f"{symbol}{next_support:.0f}" if next_support > 1000 else f"{symbol}{next_support:.2f}"
            resistance_text = f"{symbol}{next_resistance:.0f}" if next_resistance > 1000 else f"{symbol}{next_resistance:.2f}"
            
            self.psych_levels_label.config(text=f"{support_text} / {resistance_text}")
        
        if daily_prices_for_indicators:
            days = len(daily_prices_for_indicators)
            self.data_source_label.config(text=f"Based on {days} daily closes")
        
        self.status_label.config(text="● Updated", fg="#82ef82")

# ====== QUEUE PROCESSING ======
def process_queues():
    """Verarbeitet alle verfügbaren Queue-Nachrichten"""
    try:
        while True:
            msg_type, data = price_queue.get_nowait()
            
            if msg_type == 'bitcoin_price' and data is not None:
                global last_price, last_known_price
                
                if last_price == 0:
                    last_price = data
                    last_known_price = data
                    symbol = get_currency_symbol()
                    price_label.config(text=f"₿itcoin: {symbol}{data:.2f}")
                elif data != last_price:
                    animate_price_change(price_label, last_price, data)
                    last_price = data
                    last_known_price = data
                
                try:
                    btc_amount = float(btc_entry.get())
                    currency_value = btc_amount * data
                    symbol = get_currency_symbol()
                    eur_value_label.config(text=f"{currency_value:.2f} {symbol}")
                    
                    avg_price = load_avg_price()
                    if avg_price > 0:
                        profit_percentage = calculate_profit_percentage(avg_price, data)
                        if profit_percentage is not None:
                            profit_color = "#6FAB65" if profit_percentage >= 0 else "#BD5959"
                            percent_label_conversion.config(text=f"{profit_percentage:+.2f}%", fg=profit_color)
                except:
                    pass
                
                if hasattr(root, 'portfolio_tracker') and root.portfolio_tracker.is_expanded:
                    root.portfolio_tracker.update_portfolio_stats()
                    root.portfolio_tracker.update_charts()
            
            elif msg_type == 'connection_status':
                update_offline_indicator(data)
                if not data:
                    show_last_known_data()
                    
    except queue.Empty:
        pass
    
    try:
        while True:
            msg_type, data = historical_queue.get_nowait()
            if msg_type == 'historical_data':
                if data:
                    plot_historical_prices_data(ax, data)
                    
                    if data:
                        prices = [price[1] for price in data]
                        highest_price = max(prices)
                        symbol = get_currency_symbol()
                        high_label.config(text=f"Top: {symbol}{highest_price:.2f}")
                    
                    if data and len(data) > 0:
                        start_price = data[0][1]
                        if last_known_price > 0:
                            percentage_change = calculate_percentage_change(start_price, last_known_price)
                            color = "#82ef82" if percentage_change >= 0 else "#ff4d4d"
                            percent_label.config(text=f"{percentage_change:.2f}%", fg=color)
                else:
                    plot_no_data_with_message(ax, "No historical data available")
    except queue.Empty:
        pass
    
    try:
        while True:
            msg_type, data = fear_greed_queue.get_nowait()
            if msg_type == 'fear_greed':
                index, classification = data
                if index is not None:
                    fg_color = "#ff4d4d" if index < 45 else "#ffb84d" if index < 60 else "#82ef82"
                    fear_greed_label.config(text=f"{index} {classification}", fg=fg_color)
                else:
                    fear_greed_label.config(text="N/A", fg="grey")
    except queue.Empty:
        pass
    
    try:
        while True:
            msg_type, data = fx_rate_queue.get_nowait()
            if msg_type == 'fx_rate':
                usd_eur_rate = data
                if usd_eur_rate:
                    current_rate_label.config(text=f"1 USD = {usd_eur_rate:.4f} €")
    except queue.Empty:
        pass
    
    try:
        while True:
            msg_type, data = fees_queue.get_nowait()
            if msg_type == 'mempool_fees':
                if hasattr(root, 'expandable_window') and root.expandable_window.is_expanded:
                    root.expandable_window.update_fees_display()
    except queue.Empty:
        pass
    
    try:
        while True:
            msg_type, data = market_data_queue.get_nowait()
            if msg_type == 'market_indicators':
                if hasattr(root, 'expandable_window') and root.expandable_window.is_expanded:
                    root.expandable_window.update_indicators_display()
    except queue.Empty:
        pass
    
    try:
        while True:
            msg_type, data = block_height_queue.get_nowait()
            if msg_type == 'block_height':
                global latest_block_height
                latest_block_height = data
                if hasattr(root, 'wallet_tracker') and root.wallet_tracker.is_expanded:
                    root.wallet_tracker.update_block_height_display()
    except queue.Empty:
        pass
    
    try:
        while True:
            msg_type, data = wallet_queue.get_nowait()
            if msg_type == 'wallet_data':
                address = data['address']
                
                wallet_data[address] = {
                    'tx_count': data['tx_count'],
                    'balance': data['balance'],
                    'last_tx_date': data['last_tx_date'],
                    'transactions': data.get('transactions', [])
                }
                
                wallet_transactions[address] = data.get('transactions', [])
                
                if hasattr(root, 'wallet_tracker') and root.wallet_tracker.is_expanded:
                    root.wallet_tracker.update_wallet_display()
                    
            elif msg_type == 'wallet_error':
                address = data
                print(f"Error fetching data for wallet: {address}")
                
    except queue.Empty:
        pass
    
    try:
        while True:
            msg_type, data = ip_info_queue.get_nowait()
            if msg_type == 'ip_info':
                global public_ip, ip_city, ip_country, ip_flag
                public_ip = data.get('ip', 'Unknown')
                ip_city = data.get('city', 'Unknown')
                ip_country = data.get('country', 'Unknown')
                ip_flag = data.get('flag', '🌐')
                
                if hasattr(root, 'offline_canvas'):
                    if is_online:
                        tooltip_text = f"Online\nIP: {public_ip}\n📍 {ip_city}, {ip_country} {ip_flag}"
                    else:
                        tooltip_text = f"Offline - showing last known data\nIP: {public_ip}\n📍 {ip_city}, {ip_country} {ip_flag}"
                    root.offline_tooltip_text = tooltip_text
    except queue.Empty:
        pass
    
    root.after(100, process_queues)

# ====== OFFLINE FUNKTIONEN ======
def update_offline_indicator(is_connected):
    """Aktualisiert den Online/Offline-Status"""
    global is_online
    is_online = is_connected
    
    if hasattr(root, 'offline_canvas'):
        if is_connected:
            root.offline_canvas.itemconfig(root.offline_dot, fill="#4dffa6")
            tooltip_text = f"Online\nIP: {public_ip}\n📍 {ip_city}, {ip_country} {ip_flag}"
        else:
            root.offline_canvas.itemconfig(root.offline_dot, fill="#ff4d4d")
            tooltip_text = f"Offline - showing last known data\nIP: {public_ip}\n📍 {ip_city}, {ip_country} {ip_flag}"
        root.offline_tooltip_text = tooltip_text

def create_offline_indicator():
    """Erstellt einen perfekt runden Offline-Indikator"""
    if not hasattr(root, 'offline_canvas'):
        root.offline_canvas = tk.Canvas(root, width=16, height=16, 
                                       bg="#212121", highlightthickness=0, bd=0)
        root.offline_canvas.place(x=615, y=425)
        
        root.offline_dot = root.offline_canvas.create_oval(
            2, 2, 10, 10,
            fill="#4dffa6",
            outline="",
            width=0
        )
        tooltip_text = f"Online\nIP: {public_ip}\n📍 {ip_city}, {ip_country} {ip_flag}"
        root.offline_tooltip_text = tooltip_text
        
        def show_tooltip(event):
            tooltip = tk.Toplevel(root)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            tooltip_frame = tk.Frame(tooltip, bg="#333333", bd=1, relief="solid")
            tooltip_frame.pack()
            
            lines = root.offline_tooltip_text.split('\n')
            for line in lines:
                label = tk.Label(tooltip_frame, text=line, 
                               bg="#333333", fg="white", font=("Arial", 9))
                label.pack(padx=5, pady=2)
            
            tooltip.after(3000, tooltip.destroy)
        
        root.offline_canvas.bind("<Enter>", show_tooltip)

def show_last_known_data():
    """Zeigt die letzten bekannten Daten an"""
    global last_known_price
    
    if last_known_price > 0:
        symbol = get_currency_symbol()
        price_label.config(text=f"₿itcoin: {symbol}{last_known_price:.2f}")
        
        try:
            btc_amount = float(btc_entry.get())
            currency_value = btc_amount * last_known_price
            eur_value_label.config(text=f"{currency_value:.2f} {symbol}")
        except:
            pass

def plot_no_data_with_message(ax, message="No data available"):
    """Zeigt Nachricht wenn keine neuen Daten"""
    ax.clear()
    ax.set_facecolor('#212121')
    ax.text(0.5, 0.5, message, color='white', 
            ha='center', va='center', transform=ax.transAxes, fontsize=10)
    canvas.draw()

# ====== TECHNICAL ANALYSIS FUNCTIONS ======
def calculate_rsi(prices, period=14):
    """Calculate RSI (Relative Strength Index)"""
    if len(prices) < period:
        return 50.0
    
    try:
        series = pd.Series(prices)
        rsi_indicator = RSIIndicator(close=series, window=period)
        rsi_values = rsi_indicator.rsi()
        
        if not rsi_values.isna().iloc[-1]:
            return float(rsi_values.iloc[-1])
        return 50.0
    except:
        return 50.0

def calculate_stoch_rsi(prices, period=14, smooth_k=3, smooth_d=3):
    """Calculate Stochastic RSI"""
    if len(prices) < period:
        return 50.0
    
    try:
        series = pd.Series(prices)
        rsi_indicator = RSIIndicator(close=series, window=period)
        rsi_values = rsi_indicator.rsi()
        
        stoch_rsi_indicator = StochasticOscillator(
            high=rsi_values,
            low=rsi_values,
            close=rsi_values,
            window=period,
            smooth_window=smooth_k
        )
        
        stoch_rsi_k = stoch_rsi_indicator.stoch()
        
        if not stoch_rsi_k.isna().iloc[-1]:
            return float(stoch_rsi_k.iloc[-1])
        return 50.0
    except:
        return 50.0

def find_swing_points(prices, lookback=5):
    """Findet Swing Highs und Lows"""
    swing_highs = []
    swing_lows = []
    
    for i in range(lookback, len(prices) - lookback):
        if prices[i] == max(prices[i-lookback:i+lookback+1]):
            swing_highs.append(prices[i])
        
        if prices[i] == min(prices[i-lookback:i+lookback+1]):
            swing_lows.append(prices[i])
    
    return swing_highs, swing_lows

def find_psychological_levels(price, increment=None):
    """Findet psychologische Support/Resistance Levels"""
    if increment is None:
        if price > 100000:
            increment = 1000
        elif price > 50000:
            increment = 1000
        elif price > 20000:
            increment = 500
        elif price > 10000:
            increment = 500
        elif price > 1000:
            increment = 100
        elif price > 100:
            increment = 10
        else:
            increment = 1
    
    base = (price // increment) * increment
    levels = []
    
    for i in range(1, 4):
        levels.append(base - (i * increment))
    
    for i in range(1, 4):
        levels.append(base + (i * increment))
    
    return levels, increment

def calculate_pivot_points(high, low, close):
    """Berechnet Pivot Points"""
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    return pivot, r1, r2, s1, s2

def calculate_professional_support_resistance(prices):
    """Berechnet professionelle Support/Resistance Levels"""
    if len(prices) < 20:
        return 0.0, 0.0
    
    try:
        current_price = prices[-1] if prices else 0
        
        recent_high = max(prices[-20:]) if len(prices) >= 20 else max(prices)
        recent_low = min(prices[-20:]) if len(prices) >= 20 else min(prices)
        
        swing_highs, swing_lows = find_swing_points(prices, lookback=3)
        
        major_swing_high = max(swing_highs[-3:]) if swing_highs else recent_high
        major_swing_low = min(swing_lows[-3:]) if swing_lows else recent_low
        
        series = pd.Series(prices)
        sma_20 = series.rolling(window=20).mean().iloc[-1]
        sma_50 = series.rolling(window=50).mean().iloc[-1] if len(prices) >= 50 else sma_20
        
        psych_levels, increment = find_psychological_levels(current_price)
        
        psych_resistance = min([l for l in psych_levels if l > current_price], 
                              default=current_price * 1.05)
        psych_support = max([l for l in psych_levels if l < current_price], 
                           default=current_price * 0.95)
        
        if len(prices) >= 2:
            pivot, r1, r2, s1, s2 = calculate_pivot_points(
                max(prices[-2:]),
                min(prices[-2:]),
                prices[-1]
            )
        else:
            r1, s1 = current_price * 1.02, current_price * 0.98
        
        if len(prices) >= 20:
            bb = BollingerBands(close=series, window=20, window_dev=2)
            bb_upper = bb.bollinger_hband().iloc[-1]
            bb_lower = bb.bollinger_lband().iloc[-1]
        else:
            bb_upper = current_price * 1.03
            bb_lower = current_price * 0.97
        
        resistance_candidates = [
            recent_high,
            major_swing_high,
            psych_resistance,
            r1,
            bb_upper,
            sma_20
        ]
        
        support_candidates = [
            recent_low,
            major_swing_low,
            psych_support,
            s1,
            bb_lower,
            sma_50
        ]
        
        resistance_weights = [0.25, 0.20, 0.20, 0.15, 0.10, 0.10]
        support_weights = [0.25, 0.20, 0.20, 0.15, 0.10, 0.10]
        
        resistance = sum(r * w for r, w in zip(resistance_candidates, resistance_weights))
        support = sum(s * w for s, w in zip(support_candidates, support_weights))
        
        if resistance <= support:
            resistance = current_price * 1.03
            support = current_price * 0.97
        
        if current_price > 1000:
            resistance = round(resistance, 0)
            support = round(support, 0)
        elif current_price > 100:
            resistance = round(resistance, 1)
            support = round(support, 1)
        else:
            resistance = round(resistance, 2)
            support = round(support, 2)
        
        return support, resistance, increment
        
    except Exception as e:
        if current_price > 0:
            return current_price * 0.97, current_price * 1.03, 100
        return 0.0, 0.0, 100

# ====== LOADING STATUS SYSTEM ======
class LoadingStatus:
    def __init__(self):
        self.status = {
            'bitcoin_price': False,
            'historical_data': False,
            'fear_greed': False,
            'fx_rate': False,
            'mempool_fees': False,
            'market_indicators': False,
            'daily_prices': False,
            'wallet_data': False,
            'ip_info': False
        }
        self.callbacks = []
        self.all_loaded = False
    
    def set_loaded(self, key):
        self.status[key] = True
        
        if all(self.status.values()) and not self.all_loaded:
            self.all_loaded = True
            for callback in self.callbacks:
                callback()
    
    def get_progress(self):
        loaded = sum(1 for v in self.status.values() if v)
        total = len(self.status)
        return (loaded / total) * 100 if total > 0 else 0
    
    def register_callback(self, callback):
        self.callbacks.append(callback)

loading_status = LoadingStatus()

# ====== WELCOME SCREEN ======
class WelcomeScreen:
    def __init__(self, parent, x=None, y=None):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        
        self.MIN_DISPLAY_TIME = 2.0
        self.MAX_DISPLAY_TIME = 5.5
        self.FADE_OUT_TIME = 0.2
        
        self.start_time = time.time()
        self.all_data_loaded = False
        self.fade_out_started = False
        
        window_width = 640
        window_height = 450
        
        if x is not None and y is not None:
            loading_x = x + (640 - window_width) // 2
            loading_y = y + (450 - window_height) // 2
            window_geometry = f"{window_width}x{window_height}+{loading_x}+{loading_y}"
        else:
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            x = (screen_width // 2) - (window_width // 2)
            y = (screen_height // 2) - (window_height // 2)
            window_geometry = f"{window_width}x{window_height}+{x}+{y}"
        
        self.window.geometry(window_geometry)
        
        self.canvas = tk.Canvas(self.window, width=window_width, height=window_height, 
                               highlightthickness=0, bg="#0a0a0a")
        self.canvas.pack(fill="both", expand=True)
        
        self.animation_running = True
        
        self.create_background()
        self.create_title()
        self.create_loading_indicator()
        self.create_btc_logo_animation()
        
        self.animate()
        
        loading_status.register_callback(self.on_all_data_loaded)
        
        self.max_time_timer = self.window.after(
            int(self.MAX_DISPLAY_TIME * 1000), 
            self.start_fade_out
        )
    
    def create_background(self):
        """Erstellt einen minimalistischen, dunklen Hintergrund"""
        self.background_chars = []
        btc_symbols = ["₿"]
        
        for i in range(20):
            x = random.randint(0, 640)
            y = random.randint(0, 450)
            font_size = random.randint(8, 14)
            base_opacity = random.uniform(0.02, 0.06)
            shimmer_speed = random.uniform(0.5, 2.0)
            shimmer_phase = random.uniform(0, 2 * math.pi)
            shimmer_intensity = random.uniform(0.03, 0.08)
            
            char_id = self.canvas.create_text(
                x, y,
                text=random.choice(btc_symbols),
                font=("Arial", font_size),
                fill=self.rgba_to_hex(247, 147, 26, base_opacity),
                anchor="center"
            )
            
            self.background_chars.append({
                'id': char_id,
                'x': x,
                'y': y,
                'original_x': x,
                'original_y': y,
                'size': font_size,
                'base_opacity': base_opacity,
                'current_opacity': base_opacity,
                'shimmer_speed': shimmer_speed,
                'shimmer_phase': shimmer_phase,
                'shimmer_intensity': shimmer_intensity,
                'drift_speed_x': random.uniform(-0.05, 0.05),
                'drift_speed_y': random.uniform(-0.05, 0.05),
                'drift_radius_x': random.uniform(5, 15),
                'drift_radius_y': random.uniform(5, 15),
                'time_offset': random.uniform(0, 10),
                'color_variant': random.choice([
                    (247, 147, 26),
                    (255, 165, 0),
                    (218, 165, 32),
                    (255, 200, 0),
                ])
            })
    
    def rgba_to_hex(self, r, g, b, a=1.0):
        """Konvertiert RGBA zu Hex mit Alpha"""
        if a < 0.5:
            brightness_factor = a * 2
            r = int(r * brightness_factor)
            g = int(g * brightness_factor)
            b = int(b * brightness_factor)
        
        return f'#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}'
    
    def create_title(self):
        """Erstellt den minimalistischen Schriftzug"""
        self.btc_symbol = self.canvas.create_text(
            300, 100,
            text="₿",
            font=("Arial", 72, "bold"),
            fill="#F7931A"
        )
        
        self.title_text = self.canvas.create_text(
            300, 170,
            text="BTC PRACKER",
            font=("Arial", 28, "bold"),
            fill="#FFFFFF"
        )
        
        self.subtitle = self.canvas.create_text(
            300, 200,
            text="Bitcoin Price Tracker",
            font=("Arial", 12),
            fill="#a3a3a3"
        )
    
    def create_btc_logo_animation(self):
        """Erstellt ein zentrales, pulsierendes BTC Logo"""
        self.logo_center_x = 300
        self.logo_center_y = 240
        self.logo_size = 40
        self.logo_pulse = 0
        
        self.main_logo = self.canvas.create_oval(
            self.logo_center_x - self.logo_size//2,
            self.logo_center_y - self.logo_size//2,
            self.logo_center_x + self.logo_size//2,
            self.logo_center_y + self.logo_size//2,
            fill="#F7931A",
            outline="#FF9900",
            width=2
        )
        
        self.logo_text = self.canvas.create_text(
            self.logo_center_x,
            self.logo_center_y,
            text="₿",
            font=("Arial", 24, "bold"),
            fill="black"
        )
        
        self.rings = []
        for i in range(3):
            ring = self.canvas.create_oval(
                self.logo_center_x - self.logo_size//2 - 10,
                self.logo_center_y - self.logo_size//2 - 10,
                self.logo_center_x + self.logo_size//2 + 10,
                self.logo_center_y + self.logo_size//2 + 10,
                outline="",
                width=0
            )
            self.rings.append({
                'id': ring,
                'size': self.logo_size + 20,
                'opacity': 0.0,
                'growing': True,
                'delay': i * 0.5
            })
    
    def create_loading_indicator(self):
        """Erstellt einen minimalistischen Lade-Indikator"""
        self.progress_bg = self.canvas.create_rectangle(
            150, 300, 450, 304,
            fill="#333333",
            outline="",
            width=0
        )
        
        self.progress_fg = self.canvas.create_rectangle(
            150, 300, 150, 304,
            fill="#F7931A",
            outline="",
            width=0
        )
        
        self.loading_text = self.canvas.create_text(
            300, 280,
            text="Loading Kraken API Calls...",
            font=("Arial", 11),
            fill="#888888"
        )
        
        self.status_text = self.canvas.create_text(
            300, 320,
            text="• • • •",
            font=("Arial", 10),
            fill="#555555"
        )
        
        self.version_text = self.canvas.create_text(
            300, 380,
            text="Version 0.21 (13.02.2026)",
            font=("Arial", 9),
            fill="#a3a3a3"
        )
    
    def update_progress(self):
        """Aktualisiert den Fortschrittsbalken und Status"""
        progress = loading_status.get_progress()
        
        progress_width = 150 + (progress / 100) * 300
        current_coords = self.canvas.coords(self.progress_fg)
        if len(current_coords) >= 4:
            target_width = progress_width
            current_width = current_coords[2]
            new_width = current_width + (target_width - current_width) * 0.3
            
            self.canvas.coords(self.progress_fg, 150, 300, new_width, 304)
        
        status_symbols = []
        if progress >= 25:
            status_symbols.append("●")
        else:
            status_symbols.append("○")
            
        if progress >= 50:
            status_symbols.append("●")
        else:
            status_symbols.append("○")
            
        if progress >= 75:
            status_symbols.append("●")
        else:
            status_symbols.append("○")
            
        if progress >= 100:
            status_symbols.append("●")
        else:
            status_symbols.append("○")
        
        self.canvas.itemconfig(self.status_text, text=" ".join(status_symbols))
        
        if progress < 25:
            status_msg = "Connecting to markets..."
        elif progress < 50:
            status_msg = "Fetching price data..."
        elif progress < 75:
            status_msg = "Loading charts..."
        elif progress < 100:
            status_msg = "Finalizing..."
        else:
            status_msg = "Ready!"
        
        self.canvas.itemconfig(self.loading_text, text=status_msg)
    
    def on_all_data_loaded(self):
        """Wird aufgerufen wenn alle Daten geladen sind"""
        self.all_data_loaded = True
        
        elapsed = time.time() - self.start_time
        remaining_min_time = max(0, self.MIN_DISPLAY_TIME - elapsed)
        
        self.window.after(int(remaining_min_time * 1000), self.start_fade_out)
    
    def start_fade_out(self):
        """Startet das Ausblenden des Welcome Screens"""
        if self.fade_out_started:
            return
        
        self.fade_out_started = True
        
        self.canvas.itemconfig(self.loading_text, text="Ready!", fill="#82ef82")
        self.canvas.itemconfig(self.status_text, text="● ● ● ●", fill="#82ef82")
        
        self.canvas.coords(self.progress_fg, 150, 300, 450, 304)
        
        self.window.after(200, self.perform_final_animation)
    
    def perform_final_animation(self):
        """Führt eine finale Animation durch bevor Fade-Out"""
        self.animation_running = False
        
        for i in range(3):
            self.window.after(i * 100, lambda flash=i: 
                self.canvas.itemconfig(self.main_logo, 
                    fill="#FFD700" if flash % 2 == 0 else "#F7931A"))
        
        self.window.after(300, self.fade_out)
    
    def fade_out(self):
        """Führt das Ausblenden durch"""
        fade_steps = 20
        for i in range(fade_steps + 1):
            if not self.window.winfo_exists():
                break
            alpha = 1.0 - (i / fade_steps)
            self.window.attributes('-alpha', alpha)
            self.window.update()
            time.sleep(self.FADE_OUT_TIME / fade_steps)
        
        self.close()
    
    def animate(self):
        """Hauptanimation-Loop"""
        if not self.animation_running:
            return
        
        current_time = time.time()
        
        self.update_progress()
        
        self.logo_pulse = (self.logo_pulse + 0.05) % (2 * math.pi)
        pulse_scale = 1.0 + math.sin(self.logo_pulse) * 0.1
        
        new_size = int(self.logo_size * pulse_scale)
        self.canvas.coords(self.main_logo,
                          self.logo_center_x - new_size//2,
                          self.logo_center_y - new_size//2,
                          self.logo_center_x + new_size//2,
                          self.logo_center_y + new_size//2)
        
        for char in self.background_chars:
            time_factor = current_time * 0.3 + char['time_offset']
            drift_x = math.sin(time_factor * char['drift_speed_x']) * char['drift_radius_x']
            drift_y = math.cos(time_factor * char['drift_speed_y']) * char['drift_radius_y']
            
            char['x'] = char['original_x'] + drift_x
            char['y'] = char['original_y'] + drift_y
            
            shimmer_value = math.sin(current_time * char['shimmer_speed'] + char['shimmer_phase'])
            
            if random.random() > 0.7:
                char['current_opacity'] = char['base_opacity'] + (
                    (shimmer_value * 0.5 + 0.5) * char['shimmer_intensity']
                )
            else:
                char['current_opacity'] = char['base_opacity'] + (
                    math.sin(shimmer_value) * char['shimmer_intensity']
                )
            
            char['current_opacity'] = max(0.01, min(0.1, char['current_opacity']))
            
            r, g, b = char['color_variant']
            brightness_factor = 1.0 + char['current_opacity'] * 2
            adjusted_r = min(255, int(r * brightness_factor))
            adjusted_g = min(255, int(g * brightness_factor))
            adjusted_b = min(255, int(b * brightness_factor))
            
            new_color = self.rgba_to_hex(adjusted_r, adjusted_g, adjusted_b, char['current_opacity'])
            
            self.canvas.coords(char['id'], char['x'], char['y'])
            self.canvas.itemconfig(char['id'], fill=new_color)
            
            if random.random() > 0.95:
                size_variation = math.sin(current_time * 2) * 0.5 + 1.0
                new_font_size = max(6, min(16, int(char['size'] * size_variation)))
                self.canvas.itemconfig(char['id'], font=("Arial", new_font_size))
        
        for ring in self.rings:
            ring['delay'] -= 0.1
            if ring['delay'] <= 0:
                if ring['growing']:
                    ring['size'] += 2
                    ring['opacity'] += 0.05
                    if ring['opacity'] >= 0.3:
                        ring['growing'] = False
                else:
                    ring['size'] += 1
                    ring['opacity'] -= 0.03
                    if ring['opacity'] <= 0:
                        ring['size'] = self.logo_size + 20
                        ring['opacity'] = 0.0
                        ring['growing'] = True
                        ring['delay'] = random.uniform(0, 1.0)
                
                color = self.rgba_to_hex(247, 147, 26, ring['opacity'])
                self.canvas.coords(ring['id'],
                                  self.logo_center_x - ring['size']//2,
                                  self.logo_center_y - ring['size']//2,
                                  self.logo_center_x + ring['size']//2,
                                  self.logo_center_y + ring['size']//2)
                self.canvas.itemconfig(ring['id'], outline=color)
        
        title_pulse = math.sin(current_time * 1.5) * 0.02 + 0.98
        title_shimmer = math.sin(current_time * 0.7) * 0.1 + 0.9
        combined_pulse = title_pulse * title_shimmer
        
        title_color = self.rgba_to_hex(255, 255, 255, combined_pulse)
        self.canvas.itemconfig(self.title_text, fill=title_color)
        
        subtitle_shimmer = math.sin(current_time * 0.9 + 0.5) * 0.05 + 0.95
        subtitle_color = self.rgba_to_hex(136, 136, 136, subtitle_shimmer)
        self.canvas.itemconfig(self.subtitle, fill=subtitle_color)
        
        self.window.after(40, self.animate)
    
    def rgba_to_hex(self, r, g, b, a=1.0):
        """Konvertiert RGBA zu Hex"""
        return f'#{int(r):02x}{int(g):02x}{int(b):02x}'
    
    def close(self):
        """Schließt den Welcome Screen und zeigt Hauptfenster"""
        if hasattr(self, 'max_time_timer'):
            self.window.after_cancel(self.max_time_timer)
        
        self.window.destroy()
        if hasattr(self.parent, 'show_main_window'):
            self.parent.show_main_window()
            
# ====== THREADED API FUNCTIONS ======
def fetch_bitcoin_price_thread():
    """Holt Bitcoin-Preis in der gewählten Währung"""
    global last_known_price, connection_error_count
    
    try:
        if CURRENCY == "USD":
            url = 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD'
            pair_key = 'XXBTZUSD'
        else:
            url = 'https://api.kraken.com/0/public/Ticker?pair=XBTEUR'
            pair_key = 'XXBTZEUR'
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if 'result' in data and pair_key in data['result']:
            price = float(data['result'][pair_key]['c'][0])
            price_queue.put(('bitcoin_price', price))
            last_known_price = price
            connection_error_count = 0
            
            if not is_online:
                price_queue.put(('connection_status', True))
        else:
            price_queue.put(('bitcoin_price', None))
            connection_error_count += 1
            
    except Exception as e:
        connection_error_count += 1
        price_queue.put(('bitcoin_price', None))
        
        if connection_error_count >= 3 and is_online:
            price_queue.put(('connection_status', False))
    
    finally:
        loading_status.set_loaded('bitcoin_price')

def fetch_historical_prices_thread():
    """Holt historische Preise in einem separaten Thread"""
    global last_historical_data
    
    try:
        time_range = TIME_RANGES[current_time_range]
        interval = time_range['interval']
        
        if CURRENCY == "USD":
            pair = 'XBTUSD'
            pair_key = 'XXBTZUSD'
        else:
            pair = 'XBTEUR'
            pair_key = 'XXBTZEUR'
        
        url = f'https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}'
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'result' in data and pair_key in data['result']:
            prices = data['result'][pair_key]
            historical_data = []
            
            for price in prices:
                try:
                    timestamp = datetime.fromtimestamp(int(price[0]))
                    open_price = float(price[1])
                    high = float(price[2])
                    low = float(price[3])
                    close = float(price[4])
                    
                    historical_data.append((timestamp, open_price, high, low, close))
                except (ValueError, IndexError):
                    continue
            
            last_historical_data = historical_data
            historical_queue.put(('historical_data', historical_data))
        else:
            historical_queue.put(('historical_data', []))
            
    except Exception as e:
        if last_historical_data:
            historical_queue.put(('historical_data', last_historical_data))
        else:
            historical_queue.put(('historical_data', []))
    finally:
        loading_status.set_loaded('historical_data')

def fetch_daily_prices_for_indicators_thread():
    """Holt tägliche Preise speziell für technische Indikatoren"""
    global daily_prices_for_indicators
    try:
        if CURRENCY == "USD":
            pair = 'XBTUSD'
            pair_key = 'XXBTZUSD'
        else:
            pair = 'XBTEUR'
            pair_key = 'XXBTZEUR'
        
        url = f'https://api.kraken.com/0/public/OHLC?pair={pair}&interval=1440&limit=100'
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'result' in data and pair_key in data['result']:
            prices = data['result'][pair_key]
            daily_prices_for_indicators = []
            
            for price in prices:
                try:
                    close_price = float(price[4])
                    daily_prices_for_indicators.append(close_price)
                except (ValueError, IndexError):
                    continue
            
            print(f"Daily prices loaded: {len(daily_prices_for_indicators)} days")
        else:
            daily_prices_for_indicators = []
            
    except Exception as e:
        daily_prices_for_indicators = []
        print(f"Error loading daily prices: {e}")
    finally:
        loading_status.set_loaded('daily_prices')

def fetch_fear_greed_thread():
    """Holt Fear & Greed Index in einem separaten Thread"""
    try:
        url = 'https://api.alternative.me/fng/?limit=1'
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if 'data' in data and len(data['data']) > 0:
            index_value = int(data['data'][0]['value'])
            classification = data['data'][0]['value_classification']
            fear_greed_queue.put(('fear_greed', (index_value, classification)))
        else:
            fear_greed_queue.put(('fear_greed', (None, "Error")))
    except Exception as e:
        fear_greed_queue.put(('fear_greed', (None, "Error")))
    finally:
        loading_status.set_loaded('fear_greed')

def fetch_fx_rate_thread():
    """Holt Wechselkurs in einem separaten Thread"""
    try:
        url = 'https://api.kraken.com/0/public/Ticker?pair=USDTEUR'
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if 'result' in data and 'USDTEUR' in data['result']:
            rate = float(data['result']['USDTEUR']['c'][0])
            fx_rate_queue.put(('fx_rate', rate))
        else:
            fx_rate_queue.put(('fx_rate', 0.92))
    except Exception as e:
        fx_rate_queue.put(('fx_rate', 0.92))
    finally:
        loading_status.set_loaded('fx_rate')

def fetch_mempool_fees_thread():
    """Holt Mempool Fees von mempool.space"""
    try:
        url = 'https://mempool.space/api/v1/fees/precise'
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        global fees_next_block, fees_2_3_blocks, fees_3_10_blocks
        
        fees_next_block = f"{data.get('fastestFee', 'N/A')}"
        fees_2_3_blocks = f"{data.get('halfHourFee', 'N/A')}"
        fees_3_10_blocks = f"{data.get('hourFee', 'N/A')}"
        
        fees_queue.put(('mempool_fees', data))
        
    except Exception as e:
        fees_next_block = "Error"
        fees_2_3_blocks = "Error"
        fees_3_10_blocks = "Error"
        fees_queue.put(('mempool_fees', None))
    finally:
        loading_status.set_loaded('mempool_fees')

def fetch_market_indicators_thread():
    """Holt Marktindikatoren"""
    global rsi_value, stoch_rsi_value, resistance_level, support_level
    
    try:
        if daily_prices_for_indicators and len(daily_prices_for_indicators) >= 20:
            prices = daily_prices_for_indicators
            
            rsi_value = calculate_rsi(prices)
            stoch_rsi_value = calculate_stoch_rsi(prices)
            support_level, resistance_level, increment = calculate_professional_support_resistance(prices)
            
            market_data_queue.put(('market_indicators', {
                'rsi': rsi_value,
                'stoch_rsi': stoch_rsi_value,
                'support': support_level,
                'resistance': resistance_level,
                'increment': increment,
                'based_on': f"{len(prices)} daily closes"
            }))
        else:
            if last_historical_data:
                prices = [x[4] for x in last_historical_data]
                if len(prices) >= 20:
                    rsi_value = calculate_rsi(prices)
                    stoch_rsi_value = calculate_stoch_rsi(prices)
                    support_level, resistance_level, increment = calculate_professional_support_resistance(prices)
                else:
                    set_default_indicators()
            else:
                set_default_indicators()
            
            market_data_queue.put(('market_indicators', {
                'rsi': rsi_value,
                'stoch_rsi': stoch_rsi_value,
                'support': support_level,
                'resistance': resistance_level,
                'increment': 100,
                'based_on': 'fallback data'
            }))
        
    except Exception as e:
        print(f"Error calculating indicators: {e}")
        set_default_indicators()
        market_data_queue.put(('market_indicators', None))
    finally:
        loading_status.set_loaded('market_indicators')

def set_default_indicators():
    """Setzt Standardwerte für Indikatoren"""
    global rsi_value, stoch_rsi_value, resistance_level, support_level
    
    rsi_value = 50.0
    stoch_rsi_value = 50.0
    
    if last_known_price > 0:
        support_level = last_known_price * 0.97
        resistance_level = last_known_price * 1.03
    else:
        support_level = 0.0
        resistance_level = 0.0

def fetch_opposite_currency_price():
    """Holt den Preis in der gegenteiligen Währung direkt von der API"""
    try:
        if CURRENCY == "USD":
            url = 'https://api.kraken.com/0/public/Ticker?pair=XBTEUR'
            pair_key = 'XXBTZEUR'
        else:
            url = 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD'
            pair_key = 'XXBTZUSD'
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if 'result' in data and pair_key in data['result']:
            opposite_price = float(data['result'][pair_key]['c'][0])
            
            if CURRENCY == "USD":
                btc_rate_label.config(text=f"1 BTC = {opposite_price:.2f} €")
            else:
                btc_rate_label.config(text=f"1 BTC = {opposite_price:.2f} $")
        else:
            update_btc_rate_with_fx()
    except Exception as e:
        update_btc_rate_with_fx()

def update_btc_rate_with_fx():
    """Fallback: Berechnet gegenteiligen Preis mit Wechselkurs"""
    try:
        url = 'https://api.kraken.com/0/public/Ticker?pair=USDTEUR'
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if 'result' in data and 'USDTEUR' in data['result']:
            usd_eur_rate = float(data['result']['USDTEUR']['c'][0])
            
            if CURRENCY == "USD" and last_known_price > 0:
                btc_in_eur = last_known_price * usd_eur_rate
                btc_rate_label.config(text=f"1 BTC = {btc_in_eur:.2f} €")
            elif CURRENCY == "EUR" and last_known_price > 0:
                btc_in_usd = last_known_price / usd_eur_rate
                btc_rate_label.config(text=f"1 BTC = {btc_in_usd:.2f} $")
    except:
        pass

# ====== OPTIONS FILE HANDLING ======
def save_options_to_file():
    """Speichert alle Einstellungen in einer Datei"""
    options = {
        'currency': CURRENCY,
        'theme_color': theme_color,
        'time_range': current_time_range,
        'startup': 1 if is_startup_enabled() else 0,
        'avg_price': load_avg_price(),
        'btc_amount': load_btc_value()
    }
    
    with open(OPTIONS_FILE, "w") as f:
        for key, value in options.items():
            f.write(f"{key}={value}\n")

def load_options_from_file():
    """Lädt alle Einstellungen aus einer Datei"""
    global CURRENCY, theme_color, current_time_range
    
    if os.path.exists(OPTIONS_FILE):
        options = {}
        with open(OPTIONS_FILE, "r") as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    options[key] = value
        
        if 'currency' in options:
            CURRENCY = options['currency']
        
        if 'theme_color' in options:
            theme_color = options['theme_color']
        
        if 'time_range' in options:
            current_time_range = options['time_range']
        
        if 'startup' in options:
            set_startup(int(options['startup']) == 1)
        
        if 'avg_price' in options:
            try:
                save_avg_price(float(options['avg_price']))
            except ValueError:
                pass
        
        if 'btc_amount' in options:
            try:
                save_btc_value(float(options['btc_amount']))
            except ValueError:
                pass
        
        return True
    return False

# ====== WÄHRUNGSKONVERTIERUNG ======
def get_currency_symbol():
    """Gibt das Währungssymbol zurück"""
    return "$" if CURRENCY == "USD" else "€"

def get_currency_code():
    """Gibt den Währungscode zurück"""
    return "USD" if CURRENCY == "USD" else "EUR"

# ====== STARTUP FUNCTIONS ======
def set_startup(enable):
    """Set or remove this script from Windows startup."""
    try:
        key = winreg.HKEY_CURRENT_USER
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(key, reg_path, 0, winreg.KEY_ALL_ACCESS) as registry_key:
            if enable:
                winreg.SetValueEx(registry_key, APP_NAME, 0, winreg.REG_SZ, APP_PATH)
            else:
                try:
                    winreg.DeleteValue(registry_key, APP_NAME)
                except:
                    pass
    except:
        pass

def is_startup_enabled():
    """Check if the app is set to start with Windows."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            return APP_PATH == winreg.QueryValueEx(key, APP_NAME)[0]
    except:
        return False

# ====== WINDOW POSITION ======
def load_window_position():
    if os.path.exists(WINDOW_POSITION_FILE):
        with open(WINDOW_POSITION_FILE, "r") as f:
            try:
                x, y = map(int, f.read().strip().split(','))
                return x, y
            except:
                return None, None
    return None, None

def save_window_position(x, y):
    with open(WINDOW_POSITION_FILE, "w") as f:
        f.write(f"{x},{y}")

# ====== AVG PRICE FUNCTIONS ======
def save_avg_price(price):
    with open(AVG_PRICE_FILE, "w") as f:
        f.write(str(price))

def load_avg_price():
    if os.path.exists(AVG_PRICE_FILE):
        with open(AVG_PRICE_FILE, "r") as f:
            try:
                return float(f.read().strip())
            except:
                return 0.0
    return 0.0

def calculate_profit_percentage(avg_price, current_price):
    if avg_price == 0:
        return None
    return ((current_price - avg_price) / avg_price) * 100

# ====== PERCENTAGE CHANGE ======
def calculate_percentage_change(start_price, current_price):
    if start_price == 0:
        return 0
    return ((current_price - start_price) / start_price) * 100

# ====== NOTEBOOK ======
def open_notebook():
    notebook_window = Toplevel(root)
    notebook_window.title("Notebook")
    notebook_window.geometry("400x380")
    notebook_window.config(bg="#212121")

    text_area = Text(notebook_window, wrap="word", font=("Arial", 10), 
                    bg="#212121", fg="white", insertbackground="white")
    text_area.pack(expand=True, fill="both")

    if os.path.exists(NOTEBOOK_FILE):
        with open(NOTEBOOK_FILE, "r") as f:
            notes = f.read()
            text_area.insert("1.0", notes)

    def save_notes():
        with open(NOTEBOOK_FILE, "w") as f:
            f.write(text_area.get("1.0", "end-1c"))
        notebook_window.destroy()

    notebook_window.protocol("WM_DELETE_WINDOW", save_notes)

# ====== BTC VALUE FUNCTIONS ======
def save_btc_value(value):
    with open(BTC_VALUE_FILE, "w") as f:
        f.write(str(value))

def load_btc_value():
    if os.path.exists(BTC_VALUE_FILE):
        with open(BTC_VALUE_FILE, "r") as f:
            try:
                return float(f.read().strip())
            except:
                return 0.0
    return 0.0

# ====== PRICE ANIMATION ======
def animate_price_change(label, start_price, end_price, duration=150, steps=50):
    """Animate the price label."""
    symbol = get_currency_symbol()
    if start_price == 0:
        start_price = end_price * 0.99
    
    price_difference = end_price - start_price
    step_value = price_difference / steps
    delay = duration // steps

    def update_price(step=0):
        if step <= steps:
            current_price = start_price + step_value * step
            label.config(text=f"₿itcoin: {symbol}{current_price:.2f}")
            label.after(delay, update_price, step + 1)
        else:
            label.config(text=f"₿itcoin: {symbol}{end_price:.2f}")

    update_price()

# ====== GRAPH FUNCTIONS ======
def plot_historical_prices_data(ax, historical_data):
    """Plottet historische Daten"""
    if not historical_data:
        if last_historical_data:
            historical_data = last_historical_data
            plot_historical_prices_data_internal(ax, historical_data, is_offline=True)
        else:
            plot_no_data_with_message(ax, "No data available - offline")
        return
    
    plot_historical_prices_data_internal(ax, historical_data, is_offline=False)

def plot_historical_prices_data_internal(ax, historical_data, is_offline=False):
    """Interne Funktion zum Plotten historischer Daten"""
    if not historical_data:
        return
    
    dates = [x[0] for x in historical_data]
    opens = [x[1] for x in historical_data]
    highs = [x[2] for x in historical_data]
    lows = [x[3] for x in historical_data]
    closes = [x[4] for x in historical_data]
    
    ax.clear()
    ax.set_facecolor('#212121')
    
    if is_offline:
        ax.text(0.02, 0.98, "Showing last known data", 
                transform=ax.transAxes, color='#ff4d4d', fontsize=8,
                verticalalignment='top', bbox=dict(facecolor='#212121', alpha=0.7))
    
    for i in range(len(dates)):
        color = bullish_color if closes[i] >= opens[i] else bearish_color
        
        ax.plot([dates[i], dates[i]], 
                [opens[i], closes[i]], 
                color=color, 
                linewidth=1.0,
                solid_capstyle='round')
        
        ax.plot([dates[i], dates[i]], 
                [highs[i], max(opens[i], closes[i])], 
                color=color, 
                linewidth=0.6)
        ax.plot([dates[i], dates[i]], 
                [min(opens[i], closes[i]), lows[i]], 
                color=color, 
                linewidth=0.6)
    
    ha_closes = []
    ha_opens = []
    for i in range(len(historical_data)):
        if i == 0:
            ha_close = (opens[i] + highs[i] + lows[i] + closes[i]) / 4
            ha_open = opens[i]
        else:
            ha_close = (opens[i] + highs[i] + lows[i] + closes[i]) / 4
            ha_open = (ha_opens[i-1] + ha_closes[i-1]) / 2
        ha_closes.append(ha_close)
        ha_opens.append(ha_open)
    
    ax.plot(dates, ha_closes, 
           color=theme_color, 
           linewidth=1.0, 
           alpha=0.5,
           linestyle='-')
    
    symbol = get_currency_symbol()
    time_delta = timedelta(hours=12)
    
    if current_time_range in ['1h', '6h', '12h', '24h']:
        hours = int(current_time_range.replace('h', ''))
        label_text = f'  {current_time_range} Mid'
        time_delta = timedelta(hours=hours)
    elif current_time_range in ['3d', '7d', '14d']:
        days = int(current_time_range.replace('d', ''))
        label_text = f'  {current_time_range} Mid'
        time_delta = timedelta(days=days)
    elif current_time_range == '1M':
        label_text = '  1 Month Mid'
        time_delta = timedelta(days=31)
    elif current_time_range == '3M':
        label_text = '  3 Month Mid'
        time_delta = timedelta(days=90)
    elif current_time_range == '6M':
        label_text = '  6 Month Mid'
        time_delta = timedelta(days=182)
    elif current_time_range in ['1Y', '2Y', '3Y', '4Y', '5Y']:
        years = int(current_time_range.replace('Y', ''))
        label_text = f'  {years} Year Mid'
        time_delta = timedelta(days=years * 365)
    elif current_time_range == 'YTD':
        start_of_year = datetime(datetime.now().year, 1, 1)
        time_delta = datetime.now() - start_of_year
        label_text = '  YTD Mid'
    elif current_time_range == 'ALL':
        time_delta = dates[-1] - dates[0] if dates else timedelta(days=365)
        label_text = '  All Mid'
    else:
        if current_time_range == '31d':
            label_text = '  31d Mid'
            time_delta = timedelta(days=31)
        elif current_time_range == '90d':
            label_text = '  90d Mid'
            time_delta = timedelta(days=90)
        elif current_time_range == '365d':
            label_text = '  1y Mid'
            time_delta = timedelta(days=365)
        else:
            label_text = '  Mid'
            time_delta = timedelta(hours=12)
    
    cutoff_time = datetime.now() - time_delta
    mid_prices = []
    
    for data in historical_data:
        timestamp, open_price, high, low, close = data
        if timestamp >= cutoff_time:
            mid_prices.append((high + low) / 2)
    
    if mid_prices:
        avg_mid_price = sum(mid_prices) / len(mid_prices)
        ax.axhline(y=avg_mid_price, color='white', linestyle='--', linewidth=0.5, alpha=0.5)
        
        ax.text(1.02,
                avg_mid_price,
                f'{label_text}\n{symbol}{avg_mid_price:.2f}', 
                transform=ax.get_yaxis_transform(),
                color='white', 
                fontsize=7,
                verticalalignment='center',
                horizontalalignment='left',
                linespacing=1.5,
                bbox=dict(facecolor='#212121', edgecolor='none', pad=2))
    
    ax.set_ylabel(get_currency_code(), color=theme_color, fontsize=8)
    ax.spines[:].set_color(theme_color)
    ax.tick_params(axis='both', colors=theme_color, labelsize=9)
    
    if current_time_range in ['1h', '6h', '12h', '24h']:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    elif current_time_range in ['3d', '7d', '14d', '1M', '3M']:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%Y'))
    
    ax.grid(color='#676767', linestyle=':', linewidth=1.0, alpha=0.5)
    
    canvas.draw()

def plot_no_data(ax):
    ax.clear()
    ax.set_facecolor('#212121')
    ax.text(0.5, 0.5, 'No data available', color='white', 
            ha='center', va='center', transform=ax.transAxes)
    canvas.draw()

def zoom(event):
    scale_factor = 1.1 if event.delta > 0 else 0.9
    
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    
    x_data, y_data = ax.transData.inverted().transform((event.x, event.y))
    
    ax.set_xlim([x_data - (x_data - xlim[0]) * scale_factor,
                 x_data + (xlim[1] - x_data) * scale_factor])
    
    ax.set_ylim([y_data - (y_data - ylim[0]) * scale_factor,
                 y_data + (ylim[1] - y_data) * scale_factor])
    
    canvas.draw()

def change_time_range(event):
    global current_time_range
    current_time_range = time_range_var.get()
    executor.submit(fetch_historical_prices_thread)

# ====== CONVERSION FUNCTIONS ======
def update_conversion(event=None):
    try:
        btc_amount = float(btc_entry.get())
        
        if last_known_price > 0:
            currency_value = btc_amount * last_known_price
            symbol = get_currency_symbol()
            eur_value_label.config(text=f"{currency_value:.2f} {symbol}")
            
            avg_price = load_avg_price()
            if avg_price > 0:
                profit_percentage = calculate_profit_percentage(avg_price, last_known_price)
                if profit_percentage is not None:
                    profit_color = "#6FAB65" if profit_percentage >= 0 else "#BD5959"
                    percent_label_conversion.config(text=f"{profit_percentage:+.2f}%", fg=profit_color)
                else:
                    percent_label_conversion.config(text="", fg="grey")
            else:
                percent_label_conversion.config(text="", fg="grey")
                
            save_btc_value(btc_amount)
    except ValueError:
        symbol = get_currency_symbol()
        eur_value_label.config(text=f"0.00 {symbol}")
        percent_label_conversion.config(text="")

def update_conversion_reverse(event=None):
    try:
        currency_amount = float(eur_entry.get())
        if last_known_price and last_known_price > 0:
            btc_value = currency_amount / last_known_price
            reverse_conversion_label.config(text=f"{btc_value:.8f} BTC")
        else:
            reverse_conversion_label.config(text="0.000000 BTC")
    except ValueError:
        reverse_conversion_label.config(text="0.000000 BTC")

# ====== THEME FUNCTIONS ======
def pick_theme():
    color_picker = Toplevel(root)
    color_picker.title("Pick Theme Color")
    color_picker.geometry("240x100")
    color_picker.config(bg="#212121")

    def set_theme_color(color):
        global theme_color
        theme_color = color
        save_theme_color(color)
        update_theme()
        color_picker.destroy()

    def save_theme_color(color):
        with open(THEME_COLOR_FILE, "w") as f:
            f.write(color)

    for i, color in enumerate(preset_colors + custom_colors):
        color_button = tk.Button(color_picker, bg=color, width=4, height=2, 
                                command=lambda col=color: set_theme_color(col))
        color_button.grid(row=i // 5, column=i % 5, padx=5, pady=5)

def update_all_button_colors():
    for button in [options_button, notebook_button, close_button]:
        button.config(bg=theme_color)
        button.original_bg = theme_color
    
    if hasattr(root, 'expandable_window'):
        root.expandable_window.expand_button.config(bg=theme_color)
        root.expandable_window.expand_button.original_bg = theme_color
    
    if hasattr(root, 'wallet_tracker'):
        root.wallet_tracker.wallet_button.config(bg=theme_color)
        root.wallet_tracker.wallet_button.original_bg = theme_color
    
    if hasattr(root, 'avg_calculator'):  # Neuer Teil
        root.avg_calculator.avg_button.config(bg=theme_color)
        root.avg_calculator.avg_button.original_bg = theme_color
    
    if hasattr(root, 'portfolio_tracker'):
        root.portfolio_tracker.portfolio_button.config(bg=theme_color)
        root.portfolio_tracker.portfolio_button.original_bg = theme_color

def update_theme():
    price_label.config(fg=theme_color)
    time_range_dropdown.config(bg=theme_color, fg="black")
    close_button.config(bg=theme_color, fg="black")
    theme_button.config(bg=theme_color, fg="black")
    notebook_button.config(bg=theme_color, fg="black")
    options_button.config(bg=theme_color, fg="black")
    
    update_all_button_colors()
    
    if hasattr(root, 'expandable_window') and root.expandable_window.is_expanded:
        root.expandable_window.update_all_data()
        for child in root.expandable_window.expanded_window.winfo_children():
            if isinstance(child, tk.Button):
                child.config(bg=theme_color)
                child.original_bg = theme_color
    
    if hasattr(root, 'wallet_tracker') and root.wallet_tracker.is_expanded:
        for child in root.wallet_tracker.expanded_window.winfo_children():
            if isinstance(child, tk.Button):
                child.config(bg=theme_color)
                child.original_bg = theme_color
    
    if hasattr(root, 'avg_calculator') and root.avg_calculator.is_expanded:  # Neuer Teil
        for child in root.avg_calculator.expanded_window.winfo_children():
            if isinstance(child, tk.Button):
                child.config(bg=theme_color)
                child.original_bg = theme_color
    
    if hasattr(root, 'portfolio_tracker') and root.portfolio_tracker.is_expanded:
        for child in root.portfolio_tracker.expanded_window.winfo_children():
            if isinstance(child, tk.Button):
                child.config(bg=theme_color)
                child.original_bg = theme_color

# ====== UI REFRESH FUNKTION ======
def refresh_ui_for_currency():
    symbol = get_currency_symbol()
    code = get_currency_code()
    
    executor.submit(fetch_bitcoin_price_thread)
    executor.submit(fetch_historical_prices_thread)
    executor.submit(fetch_fx_rate_thread)
    executor.submit(fetch_opposite_currency_price)
    
    eur_label.config(text=f"{code} :")
    
    if CURRENCY == "USD":
        btc_rate_label.config(text="1 BTC = 0.00 €")
    else:
        btc_rate_label.config(text="1 BTC = 0.00 $")
    
    if hasattr(root, 'portfolio_tracker') and root.portfolio_tracker.is_expanded:
        root.portfolio_tracker.update_portfolio_stats()
        root.portfolio_tracker.update_charts()

# ====== ASYNCHRONE UPDATE FUNKTIONEN ======
def update_price_label_async():
    executor.submit(fetch_bitcoin_price_thread)
    executor.submit(fetch_opposite_currency_price)
    root.after(10000, update_price_label_async)

def update_graph_async():
    executor.submit(fetch_historical_prices_thread)
    root.after(60000, update_graph_async)

def update_fear_greed_async():
    executor.submit(fetch_fear_greed_thread)
    root.after(60000, update_fear_greed_async)

def update_rates_async():
    executor.submit(fetch_fx_rate_thread)
    root.after(10000, update_rates_async)

def update_high_low_async():
    executor.submit(fetch_historical_prices_thread)
    root.after(60000, update_high_low_async)

def update_percentage_change_async():
    executor.submit(fetch_historical_prices_thread)
    root.after(10000, update_percentage_change_async)

def update_expanded_data_async():
    if hasattr(root, 'expandable_window') and root.expandable_window.is_expanded:
        root.expandable_window.update_all_data()
    root.after(60000, update_expanded_data_async)

def update_daily_prices_async():
    executor.submit(fetch_daily_prices_for_indicators_thread)
    root.after(300000, update_daily_prices_async)

def update_wallets_async():
    if hasattr(root, 'wallet_tracker') and root.wallet_tracker.is_expanded:
        root.wallet_tracker.update_all_wallets()
    root.after(300000, update_wallets_async)

def update_ip_info_async():
    executor.submit(fetch_ip_info_thread)
    root.after(3600000, update_ip_info_async)

def update_portfolio_async():
    if hasattr(root, 'portfolio_tracker') and root.portfolio_tracker.is_expanded:
        root.portfolio_tracker.update_portfolio_stats()
        root.portfolio_tracker.update_charts()
    root.after(10000, update_portfolio_async)

# ====== DEBOUNCED FUNCTIONS ======
class Debouncer:
    def __init__(self, func, delay=300):
        self.func = func
        self.delay = delay
        self.timer = None
    
    def __call__(self, *args, **kwargs):
        if self.timer:
            root.after_cancel(self.timer)
        self.timer = root.after(self.delay, lambda: self.func(*args, **kwargs))

# ====== CONVERTER FUNCTIONS ======
def get_usd_eur_rate_sync():
    try:
        url = 'https://api.kraken.com/0/public/Ticker?pair=USDTEUR'
        response = requests.get(url, timeout=5)
        data = response.json()
        return float(data['result']['USDTEUR']['c'][0])
    except:
        return 0.92

def update_usd_eur_conversion(event=None):
    try:
        usd_amount = float(usd_entry.get())
        rate = get_usd_eur_rate_sync()
        usd_eur_label.config(text=f"{usd_amount * rate:.2f} EUR")
    except:
        usd_eur_label.config(text="Error")

def update_eur_usd_conversion(event=None):
    try:
        eur_amount = float(eur_usd_entry.get())
        rate = get_usd_eur_rate_sync()
        eur_usd_label.config(text=f"{eur_amount / rate:.2f} USD")
    except:
        eur_usd_label.config(text="Error")

# ====== MAIN WINDOW DRAGGING ======
def on_main_drag_start(event):
    root.x = event.x
    root.y = event.y
    root.dragging = True

def on_main_drag_motion(event):
    if hasattr(root, 'dragging') and root.dragging:
        deltax = event.x - root.x
        deltay = event.y - root.y
        x = root.winfo_x() + deltax
        y = root.winfo_y() + deltay
        root.geometry(f"+{x}+{y}")
        
        if hasattr(root, 'expandable_window') and root.expandable_window.is_expanded:
            try:
                indicators_x = x - 400
                indicators_y = y
                root.expandable_window.expanded_window.geometry(f"+{indicators_x}+{indicators_y}")
            except:
                pass
        
        if hasattr(root, 'wallet_tracker') and root.wallet_tracker.is_expanded:
            try:
                wallet_x = x - 700
                wallet_y = y
                root.wallet_tracker.expanded_window.geometry(f"+{wallet_x}+{wallet_y}")
            except:
                pass
        
        if hasattr(root, 'avg_calculator') and root.avg_calculator.is_expanded:
            try:
                avg_x = x - 550
                avg_y = y
                root.avg_calculator.expanded_window.geometry(f"+{avg_x}+{avg_y}")
            except:
                pass
        
        if hasattr(root, 'portfolio_tracker') and root.portfolio_tracker.is_expanded:
            try:
                portfolio_x = x - 900
                portfolio_y = y
                root.portfolio_tracker.expanded_window.geometry(f"+{portfolio_x}+{portfolio_y}")
            except:
                pass

def on_main_drag_end(event):
    root.dragging = False
    
    if hasattr(root, 'expandable_window') and root.expandable_window.is_expanded:
        try:
            x = root.expandable_window.expanded_window.winfo_x()
            y = root.expandable_window.expanded_window.winfo_y()
            save_attached_window_pos('indicators', x, y)
        except:
            pass
    
    if hasattr(root, 'wallet_tracker') and root.wallet_tracker.is_expanded:
        try:
            x = root.wallet_tracker.expanded_window.winfo_x()
            y = root.wallet_tracker.expanded_window.winfo_y()
            save_attached_window_pos('wallet', x, y)
        except:
            pass
    
    if hasattr(root, 'avg_calculator') and root.avg_calculator.is_expanded:
        try:
            x = root.avg_calculator.expanded_window.winfo_x()
            y = root.avg_calculator.expanded_window.winfo_y()
            save_attached_window_pos('avg', x, y)
        except:
            pass
    
    if hasattr(root, 'portfolio_tracker') and root.portfolio_tracker.is_expanded:
        try:
            x = root.portfolio_tracker.expanded_window.winfo_x()
            y = root.portfolio_tracker.expanded_window.winfo_y()
            save_attached_window_pos('portfolio', x, y)
        except:
            pass

# ====== OPTIMIZED EVENT HANDLING ======
def on_closing():
    executor.shutdown(wait=False)
    save_window_position(root.winfo_x(), root.winfo_y())
    
    if hasattr(root, 'expandable_window') and root.expandable_window.is_expanded:
        try:
            x = root.expandable_window.expanded_window.winfo_x()
            y = root.expandable_window.expanded_window.winfo_y()
            save_attached_window_pos('indicators', x, y)
        except:
            pass
    
    if hasattr(root, 'wallet_tracker') and root.wallet_tracker.is_expanded:
        try:
            x = root.wallet_tracker.expanded_window.winfo_x()
            y = root.wallet_tracker.expanded_window.winfo_y()
            save_attached_window_pos('wallet', x, y)
        except:
            pass
    
    if hasattr(root, 'portfolio_tracker') and root.portfolio_tracker.is_expanded:
        try:
            x = root.portfolio_tracker.expanded_window.winfo_x()
            y = root.portfolio_tracker.expanded_window.winfo_y()
            save_attached_window_pos('portfolio', x, y)
        except:
            pass
    
    if hasattr(root, 'avg_calculator') and root.avg_calculator.is_expanded:
        try:
            x = root.avg_calculator.expanded_window.winfo_x()
            y = root.avg_calculator.expanded_window.winfo_y()
            save_attached_window_pos('avg', x, y)
        except:
            pass
    
    save_options_to_file()
    root.destroy()
    sys.exit(0)
	
# ====== TEST FUNCTIONS ======
def test_offline_mode():
    price_queue.put(('connection_status', False))
    root.after(10000, lambda: price_queue.put(('connection_status', True)))

# ====== MAIN APPLICATION ======
if __name__ == "__main__":
    if os.path.exists(THEME_COLOR_FILE):
        with open(THEME_COLOR_FILE, "r") as f:
            saved_color = f.read().strip()
            if saved_color:
                theme_color = saved_color
    
    load_options_from_file()
    
    root = tk.Tk()
    root.overrideredirect(1)
    root.config(bg="#212121")
    
    last_x, last_y = load_window_position()
    
    window_width = 640
    window_height = 450
    
    if last_x is not None and last_y is not None:
        main_window_x, main_window_y = last_x, last_y
        root.geometry(f"{window_width}x{window_height}+{main_window_x}+{main_window_y}")
    else:
        root.update_idletasks()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        main_window_x = (screen_width // 2) - (window_width // 2)
        main_window_y = (screen_height // 2) - (window_height // 2)
        root.geometry(f"{window_width}x{window_height}+{main_window_x}+{main_window_y}")
    
    loading_screen_x = main_window_x + (window_width - 640) // 2
    loading_screen_y = main_window_y + (window_height - 450) // 2
    
    root.withdraw()
    
    price_label = tk.Label(root, text="₿itcoin: Loading...", 
                          font=('Arial', 22), bg="#212121", fg=theme_color)
    price_label.place(x=197, y=10)

    fig, ax = plt.subplots(figsize=(25, 6), dpi=100)
    fig.patch.set_facecolor('#212121')
    ax.set_facecolor('#212121')
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.place(x=0, y=65, width=620, height=320)
    
    canvas_widget.bind("<MouseWheel>", zoom)

    time_range_var = tk.StringVar(root)
    time_range_var.set(current_time_range)
    time_range_dropdown = tk.OptionMenu(root, time_range_var, *TIME_RANGES.keys(), command=change_time_range)
    time_range_dropdown.config(bg=theme_color, fg="black", font=("Arial", 12), borderwidth=0, highlightthickness=0)
    time_range_dropdown.place(x=10, y=10)

    notebook_button = tk.Button(root, text="Notebook", command=open_notebook, 
                               bg=theme_color, fg="black", font=("Arial", 10))
    notebook_button.place(x=40, y=45)

    options_button = tk.Button(root, text="⸎", command=open_options, 
                              bg=theme_color, fg="black", font=("Arial", 10))
    options_button.place(x=10, y=45)

    btc_value = load_btc_value()
    conversion_frame = tk.Frame(root, bg="#212121")
    conversion_frame.place(x=220, y=50)

    btc_label = tk.Label(conversion_frame, text="BTC :", bg="#212121", fg="grey", font=("Arial", 10))
    btc_label.pack(side="left")

    btc_entry = tk.Entry(conversion_frame, bg="#212121", fg="grey", width=12)
    btc_entry.insert(0, str(btc_value))
    btc_entry.pack(side="left", padx=5)

    eur_value_label = tk.Label(conversion_frame, text="0.00", bg="#212121", fg="grey", font=("Arial", 10))
    eur_value_label.pack(side="left")

    percent_label_conversion = tk.Label(conversion_frame, text="", bg="#212121", fg="grey", font=("Arial", 10))
    percent_label_conversion.pack(side="left", padx=(2, 0))

    debounced_update_conversion = Debouncer(update_conversion, delay=500)
    debounced_update_conversion_reverse = Debouncer(update_conversion_reverse, delay=500)
    
    btc_entry.bind("<KeyRelease>", lambda e: debounced_update_conversion())
    
    high_label = tk.Label(root, text="Top: Loading...", fg="olive", bg="#212121", font=("Next Art", 10))
    high_label.place(x=10, y=76)

    fear_greed_label = tk.Label(root, text="F/G-I Loading...", font=("Next Art", 10), bg="#212121")
    fear_greed_label.place(x=495, y=80)

    percent_label = tk.Label(root, text="", font=("Next Art", 10), bg="#212121")
    percent_label.place(x=460, y=10)

    reverse_conversion_frame = tk.Frame(root, bg="#212121")
    reverse_conversion_frame.place(x=218, y=75)

    currency_code = get_currency_code()
    eur_label = tk.Label(reverse_conversion_frame, text=f"{currency_code} :", bg="#212121", fg="grey", font=("Arial", 10))
    eur_label.pack(side="left")

    eur_entry = tk.Entry(reverse_conversion_frame, bg="#212121", fg="grey", width=12)
    eur_entry.pack(side="left", padx=5)

    reverse_conversion_label = tk.Label(reverse_conversion_frame, text="0.00 BTC", bg="#212121", fg="grey", font=("Arial", 10))
    reverse_conversion_label.pack(side="left")

    eur_entry.bind("<KeyRelease>", lambda e: debounced_update_conversion_reverse())

    close_button = tk.Button(root, text='X', command=on_closing, 
                            bg=theme_color, fg='black', borderwidth=0, font=('Arial', 12))
    close_button.place(x=605, y=15)

    root.expandable_window = ExpandableWindow(root)
    root.wallet_tracker = WalletTracker(root)
    root.avg_calculator = AVGCalculator(root)
    root.portfolio_tracker = PortfolioTracker(root)

    for button in [options_button, notebook_button, close_button]:
        button.bind("<Enter>", lambda event, b=button: on_enter_button(event, b))
        button.bind("<Leave>", lambda event, b=button: on_leave_button(event, b))

    tk.Label(root, text="USD :", bg="#212121", fg="grey").place(x=125, y=380)
    usd_entry = tk.Entry(root, bg="#212121", fg="grey", width=10)
    usd_entry.place(x=160, y=380)
    usd_eur_label = tk.Label(root, text="0.00 EUR", bg="#212121", fg="grey")
    usd_eur_label.place(x=230, y=380)

    tk.Label(root, text="EUR :", bg="#212121", fg="grey").place(x=335, y=380)
    eur_usd_entry = tk.Entry(root, bg="#212121", fg="grey", width=10)
    eur_usd_entry.place(x=370, y=380)
    eur_usd_label = tk.Label(root, text="0.00 USD", bg="#212121", fg="grey")
    eur_usd_label.place(x=440, y=380)

    current_rate_label = tk.Label(root, text="1 USD = 0.0000 EUR", bg="#212121", fg="grey")
    current_rate_label.place(x=255, y=405)

    if CURRENCY == "USD":
        btc_rate_label = tk.Label(root, text="1 BTC = 0.00 €", bg="#212121", fg="grey")
    else:
        btc_rate_label = tk.Label(root, text="1 BTC = 0.00 $", bg="#212121", fg="grey")
    btc_rate_label.place(x=250, y=425)

    usd_entry.bind("<KeyRelease>", update_usd_eur_conversion)
    eur_usd_entry.bind("<KeyRelease>", update_eur_usd_conversion)
    
    root.update_idletasks()
    root.update()
    
    welcome = WelcomeScreen(root, x=main_window_x, y=main_window_y)
    
    root.after(100, lambda: executor.submit(fetch_bitcoin_price_thread))
    root.after(200, lambda: executor.submit(fetch_historical_prices_thread))
    root.after(300, lambda: executor.submit(fetch_fear_greed_thread))
    root.after(400, lambda: executor.submit(fetch_fx_rate_thread))
    root.after(500, lambda: executor.submit(fetch_opposite_currency_price))
    root.after(600, lambda: executor.submit(fetch_mempool_fees_thread))
    root.after(700, lambda: executor.submit(fetch_daily_prices_for_indicators_thread))
    root.after(800, lambda: executor.submit(fetch_market_indicators_thread))
    root.after(900, lambda: executor.submit(fetch_ip_info_thread))
    
    root.after(1000, lambda: load_wallet_addresses())
    root.after(1100, lambda: update_all_wallets())
    
    def show_main_window():
        root.deiconify()
        root.focus_force()
        
        create_offline_indicator()
        
        root.after(50, process_queues)
        
        root.after(1000, update_price_label_async)
        root.after(2000, update_graph_async)
        root.after(3000, update_fear_greed_async)
        root.after(4000, update_rates_async)
        root.after(5000, update_high_low_async)
        root.after(6000, update_percentage_change_async)
        root.after(7000, update_expanded_data_async)
        root.after(8000, update_daily_prices_async)
        root.after(9000, update_wallets_async)
        root.after(10000, update_ip_info_async)
        root.after(11000, update_portfolio_async)
    
    root.show_main_window = show_main_window
    
    root.bind('<Button-1>', on_main_drag_start)
    root.bind('<B1-Motion>', on_main_drag_motion)
    root.bind('<ButtonRelease-1>', on_main_drag_end)
    
    root.protocol("WM_DELETE_WINDOW", on_closing)

    try:
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        ctypes.windll.user32.ShowWindow(hwnd, 1)
    except:
        pass

    root.mainloop()
