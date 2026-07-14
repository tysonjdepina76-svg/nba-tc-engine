"""Compute backtest summary directly from the picks table and export."""
import sqlite3
import pandas as pd
import os

DB = "/home/workspace/Projects/backtest_data.db"
conn = sqlite3.connect(DB)

df = pd.read_sql_query("SELECT * FROM picks", conn)
print(f"Total picks in DB: {len(df):,}")
print(f"Columns: {list(df.columns)}")
print(f"Sports: {sorted(df['sport'].dropna().unique())}")
print(f"Date range: {df['date'].min()} -> {df['date'].max()}")

print("\n=== PICKS PER SPORT ===")
print(df.groupby('sport').size().to_string())

print("\n=== CORRECTNESS PER SPORT ===")
print(df.groupby('sport')['correct'].agg(['sum', 'count', 'mean']).to_string())

print("\n=== AVG EDGE / LINE / PROJ BY SPORT ===")
print(df.groupby('sport')[['edge', 'line', 'proj']].mean().round(2).to_string())

print("\n=== RECENT DAYS (2026-07) ===")
recent = df[df['date'].str.startswith('2026-07', na=False)]
print(f"Total July 2026 picks: {len(recent):,}")
if len(recent):
    print(recent.groupby(['date', 'sport']).agg(
        picks=('id', 'count'),
        wins=('correct', 'sum'),
        winrate=('correct', 'mean'),
        avg_edge=('edge', 'mean')
    ).round(3).to_string())

conn.close()
