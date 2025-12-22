import sqlite3
import json
import pandas as pd
import datetime
import os

class DBManager:
    def __init__(self, db_path='storage.db'):
        """
        Initialize DB Manager.
        """
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """
        Create necessary tables if they don't exist.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. Simulations Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS simulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                start_date TEXT,
                end_date TEXT,
                params_json TEXT
            )
        ''')
        
        # 2. Equity Curve Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id INTEGER,
                date TEXT,
                total_value REAL,
                FOREIGN KEY(simulation_id) REFERENCES simulations(id)
            )
        ''')
        
        # 3. Trades Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id INTEGER,
                date TEXT,
                ticker TEXT,
                name TEXT,
                action TEXT,
                price REAL,
                qty INTEGER,
                fee REAL,
                note TEXT,
                FOREIGN KEY(simulation_id) REFERENCES simulations(id)
            )
        ''')

        # 4. Market Data Table (New)
        # Composite PK: ticker + date
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                ticker TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                change REAL,
                PRIMARY KEY (ticker, date)
            )
        ''')
        
        conn.commit()
        conn.close()

    def save_simulation(self, config, equity_df, trades_df):
        """
        Save a full simulation result to DB.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Insert Simulation Metadata
            params_json = json.dumps(config, ensure_ascii=False)
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT INTO simulations (timestamp, start_date, end_date, params_json)
                VALUES (?, ?, ?, ?)
            ''', (timestamp, config.get('start_date'), config.get('end_date'), params_json))
            
            simulation_id = cursor.lastrowid
            
            # 2. Insert Equity Curve
            equity_data = []
            for idx, row in equity_df.iterrows():
                date_str = str(idx.date()) if hasattr(idx, 'date') else str(idx).split()[0]
                equity_data.append((simulation_id, date_str, float(row['TotalValue'])))
            
            cursor.executemany('''
                INSERT INTO equity (simulation_id, date, total_value)
                VALUES (?, ?, ?)
            ''', equity_data)
            
            # 3. Insert Trades
            trades_data = []
            if not trades_df.empty:
                for _, row in trades_df.iterrows():
                    trades_data.append((
                        simulation_id,
                        str(row['Date']),
                        str(row['Ticker']),
                        str(row['Name']),
                        str(row['Action']),
                        float(row['Price']),
                        int(row['Qty']),
                        float(row['Fee']),
                        str(row['Note'])
                    ))
                
                cursor.executemany('''
                    INSERT INTO trades (simulation_id, date, ticker, name, action, price, qty, fee, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', trades_data)
            
            conn.commit()
            print(f"[DB] Simulation saved. ID: {simulation_id}")
            return simulation_id
            
        except Exception as e:
            print(f"[DB] Error saving simulation: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()

    def get_latest_simulation(self):
        """
        Retrieve the latest simulation data.
        Returns: (config_dict, equity_df, trades_df)
        """
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM simulations ORDER BY id DESC LIMIT 1')
            sim_row = cursor.fetchone()
            
            if not sim_row:
                return None, None, None
            
            simulation_id = sim_row['id']
            config = json.loads(sim_row['params_json'])
            
            cursor.execute('SELECT date, total_value as TotalValue FROM equity WHERE simulation_id = ? ORDER BY date', (simulation_id,))
            equity_rows = cursor.fetchall()
            equity_df = pd.DataFrame([dict(row) for row in equity_rows])
            if not equity_df.empty:
                equity_df['Date'] = pd.to_datetime(equity_df['date'])
                equity_df.set_index('Date', inplace=True)
                equity_df.drop(columns=['date'], inplace=True)
            
            cursor.execute('SELECT date as Date, ticker as Ticker, name as Name, action as Action, price as Price, qty as Qty, fee as Fee, note as Note FROM trades WHERE simulation_id = ? ORDER BY date', (simulation_id,))
            trades_rows = cursor.fetchall()
            trades_df = pd.DataFrame([dict(row) for row in trades_rows])
            
            return config, equity_df, trades_df
            
        except Exception as e:
            print(f"[DB] Error loading simulation: {e}")
            return None, None, None
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # Market Data Methods (New)
    # -------------------------------------------------------------------------

    def save_market_data(self, ticker, df):
        """
        Save OHLCV data to DB.
        UPSERT logic: Replace if exists.
        """
        if df is None or df.empty:
            return

        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            data_tuples = []
            for idx, row in df.iterrows():
                # idx is DatetimeIndex
                date_str = idx.strftime('%Y-%m-%d')
                
                # Handle potential missing columns safely
                open_val = float(row.get('Open', 0))
                high_val = float(row.get('High', 0))
                low_val = float(row.get('Low', 0))
                close_val = float(row.get('Close', 0))
                vol_val = float(row.get('Volume', 0))
                amt_val = float(row.get('Amount', 0))
                chg_val = float(row.get('Change', 0))

                data_tuples.append((
                    ticker, date_str, 
                    open_val, high_val, low_val, close_val, 
                    vol_val, amt_val, chg_val
                ))
            
            # Use REPLACE INTO for upsert behavior (requires PK on ticker, date)
            cursor.executemany('''
                REPLACE INTO market_data (ticker, date, open, high, low, close, volume, amount, change)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', data_tuples)
            
            conn.commit()
            
        except Exception as e:
            print(f"[DB] Error saving market data for {ticker}: {e}")
            conn.rollback()
        finally:
            conn.close()

    def load_market_data(self, ticker, start_date=None, end_date=None):
        """
        Load OHLCV data from DB.
        Returns DataFrame with DatetimeIndex or None.
        Optimized using pd.read_sql.
        """
        conn = self.get_connection()
        
        try:
            query = "SELECT * FROM market_data WHERE ticker = ?"
            params = [ticker]
            
            if start_date:
                query += " AND date >= ?"
                params.append(str(start_date))
            if end_date:
                query += " AND date <= ?"
                params.append(str(end_date))
                
            query += " ORDER BY date ASC"
            
            # Optimized: Read directly into DataFrame
            df = pd.read_sql(query, conn, params=params)
            
            if df.empty:
                return None
            
            # Set Index
            df['Date'] = pd.to_datetime(df['date'])
            df.set_index('Date', inplace=True)
            
            # Rename columns to match fdr format (Capitalized)
            # DB has lowercase columns
            df.rename(columns={
                'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close',
                'volume': 'Volume', 'amount': 'Amount', 'change': 'Change'
            }, inplace=True)
            
            return df[['Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Change']]
            
        except Exception as e:
            # print(f"[DB] Error loading market data for {ticker}: {e}")
            return None
        finally:
            conn.close()

    def load_market_data_bulk(self, tickers, start_date=None, end_date=None):
        """
        Load OHLCV data for multiple tickers in ONE query.
        Returns: {ticker: DataFrame}
        """
        conn = self.get_connection()
        
        try:
            if not tickers:
                return {}
            
            placeholders = ','.join(['?'] * len(tickers))
            query = f"SELECT * FROM market_data WHERE ticker IN ({placeholders})"
            params = list(tickers)
            
            if start_date:
                query += " AND date >= ?"
                params.append(str(start_date))
            if end_date:
                query += " AND date <= ?"
                params.append(str(end_date))
                
            query += " ORDER BY ticker, date ASC"
            
            # Read all into one big DF
            df_all = pd.read_sql(query, conn, params=params)
            
            if df_all.empty:
                return {}
            
            df_all['Date'] = pd.to_datetime(df_all['date'])
            # df_all.set_index('Date', inplace=True) # Don't index yet, we need to split
            
            df_all.rename(columns={
                'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close',
                'volume': 'Volume', 'amount': 'Amount', 'change': 'Change'
            }, inplace=True)
            
            # Split by ticker
            result = {}
            # GroupBy is faster than filtering
            for ticker, group in df_all.groupby('ticker'):
                # Set index for individual DF
                sub_df = group[['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Amount', 'Change']].copy()
                sub_df.set_index('Date', inplace=True)
                result[ticker] = sub_df
                
            return result
            
        except Exception as e:
            print(f"[DB] Error loading bulk market data: {e}")
            return {}
        finally:
            conn.close()

    def clear_market_data(self):
        """
        Delete all market data.
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM market_data")
            conn.commit()
            print("[DB] All market data cleared.")
        except Exception as e:
            print(f"[DB] Error clearing market data: {e}")
        finally:
            conn.close()
