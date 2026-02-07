import tkinter as tk
from tkinter import simpledialog, Toplevel, Text, Checkbutton, IntVar
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

# Dateien für Einstellungen
WINDOW_POSITION_FILE = "window_position.txt"
BTC_VALUE_FILE = "btc_value.txt"
THEME_COLOR_FILE = "theme_color.txt"
NOTEBOOK_FILE = "notes.txt"
AVG_PRICE_FILE = "avg_price.txt"
OPTIONS_FILE = "options.txt"

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

# Time ranges for historical data
TIME_RANGES = {
    '12h': {'interval': 1, 'hours': 12},
    '31d': {'interval': 60, 'days': 31},
    '90d': {'interval': 240, 'days': 90},
    '365d': {'interval': 1440, 'days': 365},
    'YTD': {'interval': 1440, 'start_of_year': True},
    'ALL': {'interval': 10080, 'all': True}
}

current_time_range = '12h'
last_price = 0.0
last_price_eur = 0.0
last_price_usd = 0.0

# Queues für Thread-Kommunikation
price_queue = queue.Queue()
historical_queue = queue.Queue()
fear_greed_queue = queue.Queue()
fx_rate_queue = queue.Queue()

# Thread Pool für API Calls
executor = ThreadPoolExecutor(max_workers=4)

# ====== LOADING STATUS SYSTEM ======
class LoadingStatus:
    def __init__(self):
        self.status = {
            'bitcoin_price': False,
            'historical_data': False,
            'fear_greed': False,
            'fx_rate': False
        }
        self.callbacks = []
        self.all_loaded = False
    
    def set_loaded(self, key):
        """Markiert einen Daten-Typ als geladen"""
        self.status[key] = True
        
        # Prüfe ob alle geladen sind
        if all(self.status.values()) and not self.all_loaded:
            self.all_loaded = True
            # Benachrichtige alle Callbacks
            for callback in self.callbacks:
                callback()
    
    def get_progress(self):
        """Gibt Fortschritt als Prozent zurück (0-100)"""
        loaded = sum(1 for v in self.status.values() if v)
        total = len(self.status)
        return (loaded / total) * 100 if total > 0 else 0
    
    def register_callback(self, callback):
        """Registriert Callback für wenn alle Daten geladen sind"""
        self.callbacks.append(callback)

loading_status = LoadingStatus()

# ====== WELCOME SCREEN ======
class WelcomeScreen:
    def __init__(self, parent, x=None, y=None):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        
        # Einstellungen für Display-Dauer
        self.MIN_DISPLAY_TIME = 2.0  # Mindestzeit in Sekunden
        self.MAX_DISPLAY_TIME = 5.5  # Maximale Zeit in Sekunden
        self.FADE_OUT_TIME = 0.2     # Sehr kurze Ausblend-Dauer
        
        self.start_time = time.time()
        self.all_data_loaded = False
        self.fade_out_started = False
        
        # Window dimensions
        window_width = 640
        window_height = 450
        
        # Position: Wenn x und y gegeben sind, diese verwenden, sonst zentrieren
        if x is not None and y is not None:
            # Positioniere genau an den gegebenen Koordinaten (zentriert über Hauptfenster)
            loading_x = x + (640 - window_width) // 2  # Hauptfenster ist 640px breit
            loading_y = y + (450 - window_height) // 2  # Hauptfenster ist 450px hoch
            window_geometry = f"{window_width}x{window_height}+{loading_x}+{loading_y}"
        else:
            # Fallback: Zentriere auf Bildschirm
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            x = (screen_width // 2) - (window_width // 2)
            y = (screen_height // 2) - (window_height // 2)
            window_geometry = f"{window_width}x{window_height}+{x}+{y}"
        
        self.window.geometry(window_geometry)
        
        # Canvas für Animationen
        self.canvas = tk.Canvas(self.window, width=window_width, height=window_height, 
                               highlightthickness=0, bg="#0a0a0a")
        self.canvas.pack(fill="both", expand=True)
        
        # Animation Variablen
        self.animation_running = True
        
        # Minimalistische Elemente
        self.create_background()
        self.create_title()
        self.create_loading_indicator()
        self.create_btc_logo_animation()
        
        # Starte Animation
        self.animate()
        
        # Registriere Callback für wenn alle Daten geladen sind
        loading_status.register_callback(self.on_all_data_loaded)
        
        # Starte Timer für maximale Anzeigezeit
        self.max_time_timer = self.window.after(
            int(self.MAX_DISPLAY_TIME * 1000), 
            self.start_fade_out
        )
    
    def create_background(self):
        """Erstellt einen minimalistischen, dunklen Hintergrund mit schimmernden BTC Unicode Zeichen"""
        self.background_chars = []
        btc_symbols = ["₿"]  # BTC Unicode Symbol
        
        # Erstelle viele kleine BTC Symbole im Hintergrund mit unterschiedlichen Eigenschaften
        for i in range(20):  # Genug für Schimmer-Effekt, aber nicht zu viele
            x = random.randint(0, 640)
            y = random.randint(0, 450)
            
            # Zufällige Größe für Variation
            font_size = random.randint(8, 14)
            
            # Anfangs-Transparenz und Phase für Schimmer-Animation
            base_opacity = random.uniform(0.02, 0.06)
            shimmer_speed = random.uniform(0.5, 2.0)  # Geschwindigkeit des Schimmerns
            shimmer_phase = random.uniform(0, 2 * math.pi)  # Startphase für Variation
            shimmer_intensity = random.uniform(0.03, 0.08)  # Stärke des Schimmerns
            
            # Erstelle BTC Symbol
            char_id = self.canvas.create_text(
                x, y,
                text=random.choice(btc_symbols),
                font=("Arial", font_size),
                fill=self.rgba_to_hex(247, 147, 26, base_opacity),
                anchor="center"
            )
            
            # Speichere Eigenschaften für Animation
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
                    (247, 147, 26),  # Standard BTC Orange
                    (255, 165, 0),   # Hellere Orange
                    (218, 165, 32),  # Gold-Ton
                    (255, 200, 0),   # Gelblicher Ton
                ])
            })
    
    def rgba_to_hex(self, r, g, b, a=1.0):
        """Konvertiert RGBA zu Hex mit Alpha (für Canvas)"""
        # Für Tkinter Canvas müssen wir Alpha anders handhaben
        # Da Canvas keine RGBA unterstützt, verwenden wir einfach die Farbe
        # und simulieren Alpha durch Helligkeit
        if a < 0.5:
            # Für niedrige Alpha-Werte, mache die Farbe dunkler
            brightness_factor = a * 2
            r = int(r * brightness_factor)
            g = int(g * brightness_factor)
            b = int(b * brightness_factor)
        
        return f'#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}'
    
    def create_title(self):
        """Erstellt den minimalistischen Schriftzug"""
        # BTC Symbol oben
        self.btc_symbol = self.canvas.create_text(
            300, 100,
            text="₿",
            font=("Arial", 72, "bold"),
            fill="#F7931A"
        )
        
        # App Name
        self.title_text = self.canvas.create_text(
            300, 170,
            text="BTC PRACKER",
            font=("Arial", 28, "bold"),
            fill="#FFFFFF"
        )
        
        # Untertitel
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
        
        # Haupt-Logo (wird animiert)
        self.main_logo = self.canvas.create_oval(
            self.logo_center_x - self.logo_size//2,
            self.logo_center_y - self.logo_size//2,
            self.logo_center_x + self.logo_size//2,
            self.logo_center_y + self.logo_size//2,
            fill="#F7931A",
            outline="#FF9900",
            width=2
        )
        
        # BTC Symbol im Logo
        self.logo_text = self.canvas.create_text(
            self.logo_center_x,
            self.logo_center_y,
            text="₿",
            font=("Arial", 24, "bold"),
            fill="black"
        )
        
        # Konzentrische Ringe (für Wellen-Effekt)
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
        # Fortschrittsbalken (dünn und elegant)
        self.progress_bg = self.canvas.create_rectangle(
            150, 300, 450, 304,  # Sehr dünn
            fill="#333333",
            outline="",
            width=0
        )
        
        # Fortschrittsbalken Vordergrund
        self.progress_fg = self.canvas.create_rectangle(
            150, 300, 150, 304,  # Startet bei 0%
            fill="#F7931A",
            outline="",
            width=0
        )
        
        # Lade-Text (minimal)
        self.loading_text = self.canvas.create_text(
            300, 280,
            text="Loading Kraken API Calls...",
            font=("Arial", 11),
            fill="#888888"
        )
        
        # Status-Anzeige (sehr minimalistisch)
        self.status_text = self.canvas.create_text(
            300, 320,
            text="• • • •",
            font=("Arial", 10),
            fill="#555555"
        )
        
        # Version/Info Text (unten, sehr unauffällig)
        self.version_text = self.canvas.create_text(
            300, 380,
            text="Created by FS",
            font=("Arial", 9),
            fill="#a3a3a3"
        )
    
    def update_progress(self):
        """Aktualisiert den Fortschrittsbalken und Status"""
        progress = loading_status.get_progress()
        
        # Aktualisiere Fortschrittsbalken (sanfte Animation)
        progress_width = 150 + (progress / 100) * 300
        current_coords = self.canvas.coords(self.progress_fg)
        if len(current_coords) >= 4:
            # Sanfte Interpolation für flüssigere Bewegung
            target_width = progress_width
            current_width = current_coords[2]
            new_width = current_width + (target_width - current_width) * 0.3
            
            self.canvas.coords(self.progress_fg, 150, 300, new_width, 304)
        
        # Aktualisiere Status-Punkte basierend auf Fortschritt
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
        
        # Aktualisiere Lade-Text basierend auf Fortschritt
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
        
        # Berechne verbleibende Mindestzeit
        elapsed = time.time() - self.start_time
        remaining_min_time = max(0, self.MIN_DISPLAY_TIME - elapsed)
        
        # Starte Fade-Out nach Mindestzeit
        self.window.after(int(remaining_min_time * 1000), self.start_fade_out)
    
    def start_fade_out(self):
        """Startet das Ausblenden des Welcome Screens"""
        if self.fade_out_started:
            return
        
        self.fade_out_started = True
        
        # Zeige "Ready" Zustand
        self.canvas.itemconfig(self.loading_text, text="Ready!", fill="#82ef82")
        self.canvas.itemconfig(self.status_text, text="● ● ● ●", fill="#82ef82")
        
        # Setze Fortschrittsbalken auf 100%
        self.canvas.coords(self.progress_fg, 150, 300, 450, 304)
        
        # Finale Puls-Animation bevor Ausblenden
        self.window.after(200, self.perform_final_animation)
    
    def perform_final_animation(self):
        """Führt eine finale Animation durch bevor Fade-Out"""
        self.animation_running = False
        
        # Flash-Effekt beim BTC Logo
        for i in range(3):
            self.window.after(i * 100, lambda flash=i: 
                self.canvas.itemconfig(self.main_logo, 
                    fill="#FFD700" if flash % 2 == 0 else "#F7931A"))
        
        # Kurze Pause dann ausblenden
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
        """Hauptanimation-Loop mit Schimmer-Effekt für Hintergrund"""
        if not self.animation_running:
            return
        
        current_time = time.time()
        
        # Aktualisiere Fortschritt
        self.update_progress()
        
        # Pulsierende Logo-Animation
        self.logo_pulse = (self.logo_pulse + 0.05) % (2 * math.pi)
        pulse_scale = 1.0 + math.sin(self.logo_pulse) * 0.1
        
        # Skaliere das Haupt-Logo
        new_size = int(self.logo_size * pulse_scale)
        self.canvas.coords(self.main_logo,
                          self.logo_center_x - new_size//2,
                          self.logo_center_y - new_size//2,
                          self.logo_center_x + new_size//2,
                          self.logo_center_y + new_size//2)
        
        # Hintergrund-BTC Zeichen mit Schimmer-Effekt animieren
        for char in self.background_chars:
            # Sanfte Drift-Bewegung (Orbit-Effekt)
            time_factor = current_time * 0.3 + char['time_offset']
            drift_x = math.sin(time_factor * char['drift_speed_x']) * char['drift_radius_x']
            drift_y = math.cos(time_factor * char['drift_speed_y']) * char['drift_radius_y']
            
            char['x'] = char['original_x'] + drift_x
            char['y'] = char['original_y'] + drift_y
            
            # SCHIMMER-EFFEKT: Transparenz pulsiert
            shimmer_value = math.sin(current_time * char['shimmer_speed'] + char['shimmer_phase'])
            
            # Unterschiedliche Schimmer-Muster
            if random.random() > 0.7:  # 30% haben unterschiedlichen Schimmer
                # Pulsierender Effekt
                char['current_opacity'] = char['base_opacity'] + (
                    (shimmer_value * 0.5 + 0.5) * char['shimmer_intensity']
                )
            else:
                # Sanfteres Auf- und Abblenden
                char['current_opacity'] = char['base_opacity'] + (
                    math.sin(shimmer_value) * char['shimmer_intensity']
                )
            
            # Begrenze Transparenz
            char['current_opacity'] = max(0.01, min(0.1, char['current_opacity']))
            
            # Farbe variieren basierend auf Schimmer
            r, g, b = char['color_variant']
            
            # Bei höherer Transparenz etwas heller machen
            brightness_factor = 1.0 + char['current_opacity'] * 2
            adjusted_r = min(255, int(r * brightness_factor))
            adjusted_g = min(255, int(g * brightness_factor))
            adjusted_b = min(255, int(b * brightness_factor))
            
            # Farbe mit aktualisierter Transparenz anwenden
            new_color = self.rgba_to_hex(adjusted_r, adjusted_g, adjusted_b, char['current_opacity'])
            
            # Aktualisiere Position und Farbe
            self.canvas.coords(char['id'], char['x'], char['y'])
            self.canvas.itemconfig(char['id'], fill=new_color)
            
            # Gelegentlich leichte Größenänderung für zusätzlichen Schimmer-Effekt
            if random.random() > 0.95:  # 5% Chance pro Frame
                size_variation = math.sin(current_time * 2) * 0.5 + 1.0
                new_font_size = max(6, min(16, int(char['size'] * size_variation)))
                self.canvas.itemconfig(char['id'], font=("Arial", new_font_size))
        
        # Animiere die konzentrischen Ringe
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
                
                # Aktualisiere Ring
                color = self.rgba_to_hex(247, 147, 26, ring['opacity'])
                self.canvas.coords(ring['id'],
                                  self.logo_center_x - ring['size']//2,
                                  self.logo_center_y - ring['size']//2,
                                  self.logo_center_x + ring['size']//2,
                                  self.logo_center_y + ring['size']//2)
                self.canvas.itemconfig(ring['id'], outline=color)
        
        # Sanftes Pulsieren des Titels mit leichtem Schimmer
        title_pulse = math.sin(current_time * 1.5) * 0.02 + 0.98
        
        # Titel leicht schimmern lassen
        title_shimmer = math.sin(current_time * 0.7) * 0.1 + 0.9
        combined_pulse = title_pulse * title_shimmer
        
        title_color = self.rgba_to_hex(255, 255, 255, combined_pulse)
        self.canvas.itemconfig(self.title_text, fill=title_color)
        
        # Untertitel auch leicht schimmern
        subtitle_shimmer = math.sin(current_time * 0.9 + 0.5) * 0.05 + 0.95
        subtitle_color = self.rgba_to_hex(136, 136, 136, subtitle_shimmer)
        self.canvas.itemconfig(self.subtitle, fill=subtitle_color)
        
        # Nächster Frame
        self.window.after(40, self.animate)
    
    def rgba_to_hex(self, r, g, b, a=1.0):
        """Konvertiert RGBA zu Hex mit Alpha"""
        return f'#{int(r):02x}{int(g):02x}{int(b):02x}'
    
    def close(self):
        """Schließt den Welcome Screen und zeigt Hauptfenster"""
        if hasattr(self, 'max_time_timer'):
            self.window.after_cancel(self.max_time_timer)
        
        self.window.destroy()
        # Rufe show_main_window direkt auf
        if hasattr(self.parent, 'show_main_window'):
            self.parent.show_main_window()

# ====== THREADED API FUNCTIONS ======
def fetch_bitcoin_price_thread():
    """Holt Bitcoin-Preis in der gewählten Währung"""
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
        else:
            price_queue.put(('bitcoin_price', None))
    except Exception as e:
        price_queue.put(('bitcoin_price', None))
    finally:
        loading_status.set_loaded('bitcoin_price')

def fetch_historical_prices_thread():
    """Holt historische Preise in einem separaten Thread"""
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
                    historical_data.append((
                        datetime.fromtimestamp(int(price[0])),
                        float(price[1]),
                        float(price[2]),
                        float(price[3]),
                        float(price[4])
                    ))
                except (ValueError, IndexError):
                    continue
            
            historical_queue.put(('historical_data', historical_data))
        else:
            historical_queue.put(('historical_data', []))
            
    except Exception as e:
        historical_queue.put(('historical_data', []))
    finally:
        loading_status.set_loaded('historical_data')

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
        # Immer USD/EUR Wechselkurs holen
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

def fetch_opposite_currency_price():
    """Holt den Preis in der gegenteiligen Währung direkt von der API"""
    try:
        if CURRENCY == "USD":
            # Wenn USD ausgewählt, hole EUR Preis
            url = 'https://api.kraken.com/0/public/Ticker?pair=XBTEUR'
            pair_key = 'XXBTZEUR'
        else:
            # Wenn EUR ausgewählt, hole USD Preis
            url = 'https://api.kraken.com/0/public/Ticker?pair=XBTUSD'
            pair_key = 'XXBTZUSD'
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if 'result' in data and pair_key in data['result']:
            opposite_price = float(data['result'][pair_key]['c'][0])
            
            # Update das btc_rate_label mit dem direkten API-Preis
            if CURRENCY == "USD":
                btc_rate_label.config(text=f"1 BTC = {opposite_price:.2f} €")
            else:
                btc_rate_label.config(text=f"1 BTC = {opposite_price:.2f} $")
        else:
            # Fallback auf Wechselkurs-Berechnung
            update_btc_rate_with_fx()
    except Exception as e:
        # Fallback auf Wechselkurs-Berechnung
        update_btc_rate_with_fx()

def update_btc_rate_with_fx():
    """Fallback: Berechnet gegenteiligen Preis mit Wechselkurs"""
    try:
        # Hole Wechselkurs
        url = 'https://api.kraken.com/0/public/Ticker?pair=USDTEUR'
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if 'result' in data and 'USDTEUR' in data['result']:
            usd_eur_rate = float(data['result']['USDTEUR']['c'][0])
            
            if CURRENCY == "USD" and last_price > 0:
                btc_in_eur = last_price * usd_eur_rate
                btc_rate_label.config(text=f"1 BTC = {btc_in_eur:.2f} €")
            elif CURRENCY == "EUR" and last_price > 0:
                btc_in_usd = last_price / usd_eur_rate
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
        
        # Währung setzen
        if 'currency' in options:
            CURRENCY = options['currency']
        
        # Theme Farbe setzen
        if 'theme_color' in options:
            theme_color = options['theme_color']
        
        # Time Range setzen
        if 'time_range' in options:
            current_time_range = options['time_range']
        
        # Startup setzen
        if 'startup' in options:
            set_startup(int(options['startup']) == 1)
        
        # AVG Price laden
        if 'avg_price' in options:
            try:
                save_avg_price(float(options['avg_price']))
            except ValueError:
                pass
        
        # BTC Amount laden
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
    """Speichere den AVG Price in einer Datei."""
    with open(AVG_PRICE_FILE, "w") as f:
        f.write(str(price))

def load_avg_price():
    """Lade den gespeicherten AVG Price."""
    if os.path.exists(AVG_PRICE_FILE):
        with open(AVG_PRICE_FILE, "r") as f:
            try:
                return float(f.read().strip())
            except:
                return 0.0
    return 0.0

def calculate_profit_percentage(avg_price, current_price):
    """Berechne den prozentualen Gewinn/Verlust."""
    if avg_price == 0:
        return None
    return ((current_price - avg_price) / avg_price) * 100

# ====== PERCENTAGE CHANGE ======
def calculate_percentage_change(start_price, current_price):
    """Calculate the percentage change between two prices."""
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
    """Plottet historische Daten (schnelle Version)"""
    if not historical_data:
        plot_no_data(ax)
        return
    
    dates = [x[0] for x in historical_data]
    opens = [x[1] for x in historical_data]
    highs = [x[2] for x in historical_data]
    lows = [x[3] for x in historical_data]
    closes = [x[4] for x in historical_data]
    
    ax.clear()
    ax.set_facecolor('#212121')
    
    # Optimiertes Zeichnen
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
    
    # Heikin-Ashi Linie
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
    
    # Mittelpreis-Berechnung
    symbol = get_currency_symbol()
    time_delta = timedelta(hours=12)
    
    if current_time_range == '12h':
        label_text = f'  12h Mid:\n{symbol}' + '{:.2f}'
        time_delta = timedelta(hours=12)
    elif current_time_range == '31d':
        label_text = f'  31d Mid:\n{symbol}' + '{:.2f}'
        time_delta = timedelta(days=31)
    elif current_time_range == '90d':
        label_text = f'  90d Mid:\n{symbol}' + '{:.2f}'
        time_delta = timedelta(days=90)
    elif current_time_range == '365d':
        label_text = f'  1y Mid:\n{symbol}' + '{:.2f}'
        time_delta = timedelta(days=365)
    elif current_time_range == 'YTD':
        start_of_year = datetime(datetime.now().year, 1, 1)
        time_delta = datetime.now() - start_of_year
        label_text = f'  YTD Mid:\n{symbol}' + '{:.2f}'
    elif current_time_range == 'ALL':
        time_delta = dates[-1] - dates[0] if dates else timedelta(days=365)
        label_text = f'  All Mid:\n{symbol}' + '{:.2f}'
    
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
                f'{label_text.format(avg_mid_price)}', 
                transform=ax.get_yaxis_transform(),
                color='white', 
                fontsize=7, alpha=1.0,
                verticalalignment='center',
                horizontalalignment='left',
                bbox=dict(facecolor='#212121', edgecolor='none', pad=2))
    
    # Formatierung
    ax.set_ylabel(get_currency_code(), color=theme_color, fontsize=8)
    ax.spines[:].set_color(theme_color)
    ax.tick_params(axis='both', colors=theme_color, labelsize=9)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M' if current_time_range == '12h' else '%d-%m'))
    ax.grid(color='#676767', linestyle=':', linewidth=1.0, alpha=0.5)
    
    canvas.draw()

def plot_no_data(ax):
    """Zeigt Fehlermeldung wenn keine Daten"""
    ax.clear()
    ax.set_facecolor('#212121')
    ax.text(0.5, 0.5, 'No data available', color='white', 
            ha='center', va='center', transform=ax.transAxes)
    canvas.draw()

def zoom(event):
    """Zoom function for the graph."""
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
    """Aktualisiert die BTC zu Währung Umrechnung"""
    try:
        btc_amount = float(btc_entry.get())
        
        # Verwende den letzten bekannten Preis
        if last_price > 0:
            currency_value = btc_amount * last_price
            symbol = get_currency_symbol()
            eur_value_label.config(text=f"{currency_value:.2f} {symbol}")
            
            avg_price = load_avg_price()
            if avg_price > 0:
                profit_percentage = calculate_profit_percentage(avg_price, last_price)
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
    """Aktualisiert die Währung zu BTC Umrechnung"""
    try:
        currency_amount = float(eur_entry.get())
        if last_price and last_price > 0:
            btc_value = currency_amount / last_price
            reverse_conversion_label.config(text=f"{btc_value:.6f} BTC")
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

# Hover effects
HOVER_COLOR = "white"

def on_enter_button(event, button):
    button.config(bg=HOVER_COLOR)

def on_leave_button(event, button):
    button.config(bg=theme_color)

def update_theme():
    price_label.config(fg=theme_color)
    time_range_dropdown.config(bg=theme_color, fg="black")
    close_button.config(bg=theme_color, fg="black")
    theme_button.config(bg=theme_color, fg="black")
    notebook_button.config(bg=theme_color, fg="black")
    options_button.config(bg=theme_color, fg="black")

# ====== OPTIONS WINDOW ======
def open_options():
    global theme_color, current_time_range, CURRENCY
    
    options_window = Toplevel(root)
    options_window.overrideredirect(1)
    options_window.geometry("400x550")
    options_window.config(bg="#212121")

    # Draggable functionality
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

    # Close button
    close_button = tk.Button(options_window, text='X', command=options_window.destroy, 
                            bg=theme_color, fg="black", borderwidth=0, font=('Arial', 12))
    close_button.place(x=365, y=10)

    # Währungsoption
    tk.Label(options_window, text="Currency:", bg="#212121", fg="white").pack(pady=(20, 5))
    
    currency_var = tk.StringVar(value=CURRENCY)
    
    currency_frame = tk.Frame(options_window, bg="#212121")
    currency_frame.pack()
    
    eur_radio = tk.Radiobutton(currency_frame, text="EUR (€)", variable=currency_var, value="EUR",
                              bg="#2A2A2A", fg="white", selectcolor=theme_color)
    eur_radio.pack(side="left", padx=10)
    
    usd_radio = tk.Radiobutton(currency_frame, text="USD ($)", variable=currency_var, value="USD",
                              bg="#2A2A2A", fg="white", selectcolor=theme_color)
    usd_radio.pack(side="left", padx=10)

    # Theme Button
    theme_button = tk.Button(options_window, text="Pick Theme", command=pick_theme, 
                            bg=theme_color, fg="black", font=("Arial", 10))
    theme_button.pack(pady=10)

    # AVG Price
    tk.Label(options_window, text="AVG Price:", bg="#212121", fg="white").pack(pady=5)
    avg_price_var = tk.StringVar(value=str(load_avg_price()))
    avg_price_entry = tk.Entry(options_window, textvariable=avg_price_var, 
                              bg="#212121", fg="white", insertbackground="white")
    avg_price_entry.pack(pady=5)

    def save_avg_price_from_options():
        try:
            avg_price = float(avg_price_var.get())
            save_avg_price(avg_price)
        except ValueError:
            pass

    save_avg_button = tk.Button(options_window, text="Save AVG Price", 
                               command=save_avg_price_from_options, 
                               bg=theme_color, fg="black")
    save_avg_button.pack(pady=5)

    # Time Range
    tk.Label(options_window, text="Time Range @startup", bg="#212121", fg="white").pack(pady=10)
    time_range_options_var = tk.StringVar(value=current_time_range)
    for range_name in TIME_RANGES.keys():
        tk.Radiobutton(options_window, text=range_name, variable=time_range_options_var, value=range_name,
                       bg="#2A2A2A", fg="white", selectcolor=theme_color).pack(pady=2)

    # Startup Checkbox
    start_with_windows_var = IntVar(value=1 if is_startup_enabled() else 0)
    start_with_windows_checkbox = Checkbutton(options_window, text="Start with Windows", 
                                             variable=start_with_windows_var,
                                             bg="#212121", fg="white", selectcolor="grey",
                                             command=lambda: set_startup(start_with_windows_var.get()))
    start_with_windows_checkbox.pack(pady=10)

    # Save Button
    def save_options():
        global theme_color, current_time_range, CURRENCY
        
        current_time_range = time_range_options_var.get()
        CURRENCY = currency_var.get()
        set_startup(start_with_windows_var.get())
        save_avg_price_from_options()
        
        save_options_to_file()
        refresh_ui_for_currency()
        options_window.destroy()

    save_button = tk.Button(options_window, text="Save All Settings", 
                           command=save_options, bg=theme_color, fg="black")
    save_button.place(x=20, y=470)

    # BTC Donation
    btc_address = "bc1q4df4r739n0rrqdrcdx0dlj7ukklpykgxe7ekm2"
    tk.Label(options_window, text="BTC Donations:", bg="#212121", fg="grey", 
            font=("Arial", 9)).place(x=20, y=500)
    
    btc_address_entry = tk.Entry(options_window, width=34, font=("Arial", 9), 
                                bg="#212121", fg="black", bd=0, insertbackground="#212121")
    btc_address_entry.insert(0, btc_address)
    btc_address_entry.config(state="readonly")
    btc_address_entry.place(x=120, y=500)

    # Author
    tk.Label(options_window, text="a program by F.S (2024)", bg="#212121", fg="grey", 
            font=("Arial", 9, "bold")).place(x=20, y=525)

    # Hover Effects
    for button in [close_button, theme_button, save_avg_button, save_button]:
        button.bind("<Enter>", lambda event, b=button: on_enter_button(event, b))
        button.bind("<Leave>", lambda event, b=button: on_leave_button(event, b))

# ====== UI REFRESH FUNKTION ======
def refresh_ui_for_currency():
    """Aktualisiert alle UI-Elemente für die neue Währung"""
    symbol = get_currency_symbol()
    code = get_currency_code()
    
    # Aktualisiere alle Preise neu
    executor.submit(fetch_bitcoin_price_thread)
    executor.submit(fetch_historical_prices_thread)
    executor.submit(fetch_fx_rate_thread)
    executor.submit(fetch_opposite_currency_price)  # Gegenteiligen Preis auch
    
    # Converter Labels aktualisieren
    eur_label.config(text=f"{code} :")
    
    # BTC Rate Label vorläufig setzen
    if CURRENCY == "USD":
        btc_rate_label.config(text="1 BTC = 0.00 €")
    else:  # EUR
        btc_rate_label.config(text="1 BTC = 0.00 $")

# ====== ASYNCHRONE UPDATE FUNKTIONEN ======
def update_price_label_async():
    """Aktualisiert den Preis-Label asynchron"""
    executor.submit(fetch_bitcoin_price_thread)
    # Auch gegenteiligen Preis aktualisieren
    executor.submit(fetch_opposite_currency_price)
    root.after(10000, update_price_label_async)

def update_graph_async():
    """Aktualisiert den Graphen asynchron"""
    executor.submit(fetch_historical_prices_thread)
    root.after(60000, update_graph_async)

def update_fear_greed_async():
    """Aktualisiert Fear & Greed asynchron"""
    executor.submit(fetch_fear_greed_thread)
    root.after(60000, update_fear_greed_async)

def update_rates_async():
    """Aktualisiert Wechselkurse asynchron"""
    executor.submit(fetch_fx_rate_thread)
    root.after(10000, update_rates_async)

def update_high_low_async():
    """Aktualisiert High/Low asynchron"""
    executor.submit(fetch_historical_prices_thread)
    root.after(60000, update_high_low_async)

def update_percentage_change_async():
    """Aktualisiert Prozent-Änderung asynchron"""
    executor.submit(fetch_historical_prices_thread)
    root.after(10000, update_percentage_change_async)

# ====== QUEUE PROCESSING ======
def process_queues():
    """Verarbeitet alle verfügbaren Queue-Nachrichten"""
    # Preis Queue
    try:
        while True:
            msg_type, data = price_queue.get_nowait()
            if msg_type == 'bitcoin_price' and data is not None:
                global last_price
                if last_price == 0:
                    last_price = data
                    symbol = get_currency_symbol()
                    price_label.config(text=f"₿itcoin: {symbol}{data:.2f}")
                elif data != last_price:
                    animate_price_change(price_label, last_price, data)
                    last_price = data
                
                # Speichere Preis basierend auf aktueller Währung
                if CURRENCY == "USD":
                    last_price_usd = data
                else:
                    last_price_eur = data
                
                # Update Converter mit neuem Preis
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
    except queue.Empty:
        pass
    
    # Historical Queue
    try:
        while True:
            msg_type, data = historical_queue.get_nowait()
            if msg_type == 'historical_data':
                if data:
                    plot_historical_prices_data(ax, data)
                    
                    # Update High/Low
                    if data:
                        prices = [price[1] for price in data]
                        highest_price = max(prices)
                        symbol = get_currency_symbol()
                        high_label.config(text=f"Top: {symbol}{highest_price:.2f}")
                    
                    # Update Percentage Change
                    if data and len(data) > 0:
                        start_price = data[0][1]
                        if last_price > 0:
                            percentage_change = calculate_percentage_change(start_price, last_price)
                            color = "#82ef82" if percentage_change >= 0 else "#ff4d4d"
                            percent_label.config(text=f"{percentage_change:.2f}%", fg=color)
                else:
                    plot_no_data(ax)
    except queue.Empty:
        pass
    
    # Fear & Greed Queue
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
    
    # FX Rate Queue
    try:
        while True:
            msg_type, data = fx_rate_queue.get_nowait()
            if msg_type == 'fx_rate':
                usd_eur_rate = data
                if usd_eur_rate:
                    # Wechselkurs anzeigen
                    current_rate_label.config(text=f"1 USD = {usd_eur_rate:.4f} €")
    except queue.Empty:
        pass
    
    # Nächste Verarbeitung planen
    root.after(100, process_queues)

# ====== DEBOUNCED FUNCTIONS ======
class Debouncer:
    """Verhindert zu häufige Funktionsaufrufe"""
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
    """Synchroner Wechselkurs für Converter"""
    try:
        url = 'https://api.kraken.com/0/public/Ticker?pair=USDTEUR'
        response = requests.get(url, timeout=5)
        data = response.json()
        return float(data['result']['USDTEUR']['c'][0])
    except:
        return 0.92

def update_usd_eur_conversion(event=None):
    """Aktualisiert USD zu EUR Converter"""
    try:
        usd_amount = float(usd_entry.get())
        rate = get_usd_eur_rate_sync()
        usd_eur_label.config(text=f"{usd_amount * rate:.2f} EUR")
    except:
        usd_eur_label.config(text="Error")

def update_eur_usd_conversion(event=None):
    """Aktualisiert EUR zu USD Converter"""
    try:
        eur_amount = float(eur_usd_entry.get())
        rate = get_usd_eur_rate_sync()
        eur_usd_label.config(text=f"{eur_amount / rate:.2f} USD")
    except:
        eur_usd_label.config(text="Error")

# ====== OPTIMIZED EVENT HANDLING ======
def on_closing():
    """Sauberes Beenden"""
    executor.shutdown(wait=False)
    save_window_position(root.winfo_x(), root.winfo_y())
    save_options_to_file()
    root.destroy()
    sys.exit(0)

# ====== MAIN APPLICATION ======
if __name__ == "__main__":
    # Load saved theme color
    if os.path.exists(THEME_COLOR_FILE):
        with open(THEME_COLOR_FILE, "r") as f:
            saved_color = f.read().strip()
            if saved_color:
                theme_color = saved_color
    
    # Load all options
    load_options_from_file()
    
    # Initialize main window (aber noch NICHT sichtbar machen!)
    root = tk.Tk()
    root.overrideredirect(1)
    root.config(bg="#212121")
    
    # WICHTIG: Zuerst die Fenstergröße und Position setzen
    # Lade gespeicherte Position oder berechne Zentrierung
    last_x, last_y = load_window_position()
    
    # Setze die Fenstergröße (640x450 für das Hauptfenster)
    window_width = 640
    window_height = 450
    
    if last_x is not None and last_y is not None:
        # Verwende gespeicherte Position für Hauptfenster
        main_window_x, main_window_y = last_x, last_y
        root.geometry(f"{window_width}x{window_height}+{main_window_x}+{main_window_y}")
    else:
        # Zentriere auf Bildschirm
        root.update_idletasks()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        main_window_x = (screen_width // 2) - (window_width // 2)
        main_window_y = (screen_height // 2) - (window_height // 2)
        root.geometry(f"{window_width}x{window_height}+{main_window_x}+{main_window_y}")
    
    # JETZT haben wir die Position des Hauptfensters!
    # Berechne Position für Loading Screen (zentriert über Hauptfenster)
    # Loading Screen ist 640x450, Hauptfenster ist 640x450
    loading_screen_x = main_window_x + (window_width - 640) // 2
    loading_screen_y = main_window_y + (window_height - 450) // 2
    
    # WICHTIG: Verstecke das Hauptfenster bevor wir den Loading Screen zeigen
    root.withdraw()
    
    # CRITICAL: Erstelle ALLE UI-Elemente JETZT (während das Fenster versteckt ist)
    # ====== UI ELEMENTS ======
    # Price Label
    price_label = tk.Label(root, text="₿itcoin: Loading...", 
                          font=('Arial', 22), bg="#212121", fg=theme_color)
    price_label.place(x=197, y=10)

    # Graph
    fig, ax = plt.subplots(figsize=(25, 6), dpi=100)
    fig.patch.set_facecolor('#212121')
    ax.set_facecolor('#212121')
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.place(x=0, y=65, width=620, height=320)
    
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
    
    canvas_widget.bind("<MouseWheel>", zoom)

    # Time Range Dropdown
    time_range_var = tk.StringVar(root)
    time_range_var.set(current_time_range)
    time_range_dropdown = tk.OptionMenu(root, time_range_var, *TIME_RANGES.keys(), command=change_time_range)
    time_range_dropdown.config(bg=theme_color, fg="black", font=("Arial", 12), borderwidth=0, highlightthickness=0)
    time_range_dropdown.place(x=10, y=10)

    # Notebook Button
    notebook_button = tk.Button(root, text="Notebook", command=open_notebook, 
                               bg=theme_color, fg="black", font=("Arial", 10))
    notebook_button.place(x=40, y=45)

    # Options Button
    options_button = tk.Button(root, text="⸎", command=open_options, 
                              bg=theme_color, fg="black", font=("Arial", 10))
    options_button.place(x=10, y=45)

    # BTC to Currency Converter
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

    # Debounced bindings für Converter
    debounced_update_conversion = Debouncer(update_conversion, delay=500)
    debounced_update_conversion_reverse = Debouncer(update_conversion_reverse, delay=500)
    
    btc_entry.bind("<KeyRelease>", lambda e: debounced_update_conversion())
    
    # High Price Label
    high_label = tk.Label(root, text="Top: Loading...", fg="olive", bg="#212121", font=("Next Art", 10))
    high_label.place(x=10, y=76)

    # Fear and Greed Index
    fear_greed_label = tk.Label(root, text="F/G-I Loading...", font=("Next Art", 10), bg="#212121")
    fear_greed_label.place(x=495, y=80)

    # Percentage Change Label
    percent_label = tk.Label(root, text="", font=("Next Art", 10), bg="#212121")
    percent_label.place(x=460, y=10)

    # Currency to BTC Converter
    reverse_conversion_frame = tk.Frame(root, bg="#212121")
    reverse_conversion_frame.place(x=218, y=75)

    currency_code = get_currency_code()
    eur_label = tk.Label(reverse_conversion_frame, text=f"{currency_code} :", bg="#212121", fg="grey", font=("Arial", 10))
    eur_label.pack(side="left")

    eur_entry = tk.Entry(reverse_conversion_frame, bg="#212121", fg="grey", width=12)
    eur_entry.pack(side="left", padx=5)

    reverse_conversion_label = tk.Label(reverse_conversion_frame, text="0.000000 BTC", bg="#212121", fg="grey", font=("Arial", 10))
    reverse_conversion_label.pack(side="left")

    eur_entry.bind("<KeyRelease>", lambda e: debounced_update_conversion_reverse())

    # Close Button
    close_button = tk.Button(root, text='X', command=on_closing, 
                            bg=theme_color, fg='black', borderwidth=0, font=('Arial', 12))
    close_button.place(x=605, y=15)

    # Hover effects
    for button in [options_button, notebook_button, close_button]:
        button.bind("<Enter>", lambda event, b=button: on_enter_button(event, b))
        button.bind("<Leave>", lambda event, b=button: on_leave_button(event, b))

    # ====== WÄHRUNGSCONVERTER ======
    # USD/EUR Converter
    tk.Label(root, text="USD :", bg="#212121", fg="grey").place(x=125, y=380)
    usd_entry = tk.Entry(root, bg="#212121", fg="grey", width=10)
    usd_entry.place(x=160, y=380)
    usd_eur_label = tk.Label(root, text="0.0000 EUR", bg="#212121", fg="grey")
    usd_eur_label.place(x=230, y=380)

    # EUR/USD Converter
    tk.Label(root, text="EUR :", bg="#212121", fg="grey").place(x=335, y=380)
    eur_usd_entry = tk.Entry(root, bg="#212121", fg="grey", width=10)
    eur_usd_entry.place(x=370, y=380)
    eur_usd_label = tk.Label(root, text="0.0000 USD", bg="#212121", fg="grey")
    eur_usd_label.place(x=440, y=380)

    # Current Rates
    current_rate_label = tk.Label(root, text="1 USD = 0.0000 EUR", bg="#212121", fg="grey")
    current_rate_label.place(x=255, y=405)

    # BTC in gegenteiliger Währung - Initialisiere basierend auf aktueller Währung
    if CURRENCY == "USD":
        btc_rate_label = tk.Label(root, text="1 BTC = 0.00 €", bg="#212121", fg="grey")
    else:  # EUR
        btc_rate_label = tk.Label(root, text="1 BTC = 0.00 $", bg="#212121", fg="grey")
    btc_rate_label.place(x=250, y=425)

    # Converter bindings
    usd_entry.bind("<KeyRelease>", update_usd_eur_conversion)
    eur_usd_entry.bind("<KeyRelease>", update_eur_usd_conversion)
    
    # ====== WICHTIG: Zwinge COMPLETE RENDERING vor dem Welcome Screen ======
    root.update_idletasks()  # Zeichne alle Widgets
    root.update()           # Verarbeite alle Events
    
    # Zeige Welcome Screen AN DER GLEICHEN POSITION wie Hauptfenster
    welcome = WelcomeScreen(root, x=main_window_x, y=main_window_y)
    
    # Starte API Calls SOFORT
    root.after(100, lambda: executor.submit(fetch_bitcoin_price_thread))
    root.after(200, lambda: executor.submit(fetch_historical_prices_thread))
    root.after(300, lambda: executor.submit(fetch_fear_greed_thread))
    root.after(400, lambda: executor.submit(fetch_fx_rate_thread))
    root.after(500, lambda: executor.submit(fetch_opposite_currency_price))
    
    # Funktion um Hauptfenster zu zeigen
    def show_main_window():
        # JETZT erst sichtbar machen (ist schon komplett gezeichnet)
        root.deiconify()
        root.focus_force()
        
        # Starte Queue Processing
        root.after(50, process_queues)
        
        # Starte regelmäßige Updates
        root.after(1000, update_price_label_async)
        root.after(2000, update_graph_async)
        root.after(3000, update_fear_greed_async)
        root.after(4000, update_rates_async)
        root.after(5000, update_high_low_async)
        root.after(6000, update_percentage_change_async)
    
    root.show_main_window = show_main_window
    
    # Dragging functionality
    def on_drag_start(event):
        root.x = event.x
        root.y = event.y
        root.dragging = True

    def on_drag_motion(event):
        if hasattr(root, 'dragging') and root.dragging:
            deltax = event.x - root.x
            deltay = event.y - root.y
            x = root.winfo_x() + deltax
            y = root.winfo_y() + deltay
            root.geometry(f"+{x}+{y}")

    def on_drag_end(event):
        root.dragging = False

    root.bind('<Button-1>', on_drag_start)
    root.bind('<B1-Motion>', on_drag_motion)
    root.bind('<ButtonRelease-1>', on_drag_end)
    
    # ====== FINAL SETUP ======
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Window taskbar fix
    try:
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        ctypes.windll.user32.ShowWindow(hwnd, 1)
    except:
        pass

    root.mainloop()