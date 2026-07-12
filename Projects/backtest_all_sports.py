#!/usr/bin/env python3
"""
backtest_all_sports.py - Historical backtest across all sports.
Reads /home/workspace/Daily_Log/YYYY-MM-DD/{picks.csv, graded_picks.csv}
and compares v1, v2, hybrid, ensemble strategies.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from tc_math_hybrid import (
    determine_pick, apply_correction, hybrid_projection,
    over_under_signal_v1, over_under_signal_v2, SPORT_CONFIGS
)

LEAGUE_FROM_SPORT = {
    "WNBA": "WNBA",
    "MLB": "MLB",
    "NFL": "NFL",
    "NBA": "NBA",
    "NHL": "NHL",
    "WC": "WORLD_CUP",
    "WORLD_CUP": "WORLD_CUP",
}


@dataclass
class BacktestResult:
    sport: str
    strategy: str
    total_picks: int
    wins: int
    losses: int
    hit_rate: float
    roi_pct: float
    total_profit: float
    total_stake: float
    avg_edge: float
    max_drawdown: float
    win_streak: int
    loss_streak: int


class HistoricalBacktest:
    def __init__(self, data_dir: str = "/home/workspace/Daily_Log"):
        self.data_dir = Path(data_dir)
        self.results: List[BacktestResult] = []

    def load_historical_data(self, sport: str,
                             start_date: str = "2024-01-01",
                             end_date: Optional[str] = None) -> pd.DataFrame:
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        league = LEAGUE_FROM_SPORT.get(sport.upper(), sport.upper())
        frames: List[pd.DataFrame] = []
        cur = start
        while cur <= end:
            d = cur.strftime('%Y-%m-%d')
            graded = self.data_dir / d / "graded_picks.csv"
            picks = self.data_dir / d / "picks.csv"
            path = graded if graded.exists() else (picks if picks.exists() else None)
            if path:
                try:
                    df = pd.read_csv(path)
                except Exception:
                    cur += timedelta(days=1)
                    continue
                if 'league' in df.columns:
                    df = df[df['league'].str.upper() == league]
                if 'result' in df.columns:
                    df = df[df['result'].notna() & (df['result'] != 'PENDING')]
                if not df.empty:
                    df['date'] = d
                    frames.append(df)
            cur += timedelta(days=1)

        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    def run_backtest(self, sport: str, df: pd.DataFrame,
                     strategies: List[str] = None) -> List[BacktestResult]:
        if strategies is None:
            strategies = ['v1', 'v2', 'hybrid', 'ensemble']
        if df.empty:
            return self.results
        for strat in strategies:
            r = self._backtest_strategy(sport, df, strat)
            if r:
                self.results.append(r)
        return self.results

    def _grade(self, row: pd.Series) -> Optional[Dict]:
        actual = row.get('actual')
        line = row.get('market_line')
        result = row.get('result')
        if pd.isna(actual) or pd.isna(line) or pd.isna(result):
            return None
        # result is H (hit) or M (miss)
        win = str(result).strip().upper().startswith('H')
        profit = 100 * (100 / 110) if win else -100.0
        return {'win': win, 'profit': profit, 'actual': actual, 'line': line}

    def _backtest_strategy(self, sport: str, df: pd.DataFrame,
                           strategy: str) -> Optional[BacktestResult]:
        rows = []
        for _, r in df.iterrows():
            proj = r.get('tc_projection')
            line = r.get('market_line')
            stat = r.get('stat', 'default')
            if pd.isna(proj) or pd.isna(line):
                continue

            if strategy == 'v1':
                pick = determine_pick(float(proj), float(line), sport, stat, use_v2=False)
            elif strategy == 'v2':
                pick = determine_pick(float(proj), float(line), sport, stat, use_v2=True)
            elif strategy == 'hybrid':
                proj_c = apply_correction(float(proj), sport, stat)
                pick = determine_pick(proj_c, float(line), sport, stat, use_v2=True)
            elif strategy == 'ensemble':
                model_projs = {'xgb': float(proj) * 1.02,
                               'rf':  float(proj) * 1.01,
                               'lr':  float(proj) * 1.005}
                proj_e = hybrid_projection(float(proj), sport, stat, model_projs)
                pick = determine_pick(proj_e, float(line), sport, stat, use_v2=True)
            else:
                continue

            if pick.get('direction') in ('FLAT', 'INVALID', None):
                continue

            g = self._grade(r)
            if not g:
                continue
            rows.append({'direction': pick['direction'],
                         'edge': pick.get('edge', 0.0),
                         'win': g['win'],
                         'profit': g['profit']})

        if not rows:
            return None

        dfr = pd.DataFrame(rows)
        wins = int(dfr['win'].sum())
        total = len(dfr)
        profit = float(dfr['profit'].sum())
        stake = total * 100.0
        roi = (profit / stake) * 100 if stake else 0.0
        cum = dfr['profit'].cumsum()
        max_dd = float((cum - cum.expanding().max()).min())

        win_streak = loss_streak = cw = cl = 0
        for w in dfr['win']:
            if w:
                cw += 1; cl = 0
                win_streak = max(win_streak, cw)
            else:
                cl += 1; cw = 0
                loss_streak = max(loss_streak, cl)

        return BacktestResult(
            sport=sport, strategy=strategy,
            total_picks=total, wins=wins, losses=total - wins,
            hit_rate=wins / total, roi_pct=roi,
            total_profit=profit, total_stake=stake,
            avg_edge=float(dfr['edge'].mean()),
            max_drawdown=max_dd,
            win_streak=win_streak, loss_streak=loss_streak,
        )

    def generate_report(self) -> pd.DataFrame:
        if not self.results:
            return pd.DataFrame()
        return pd.DataFrame([{
            'Sport': r.sport,
            'Strategy': r.strategy,
            'Picks': r.total_picks,
            'Wins': r.wins,
            'Losses': r.losses,
            'Hit Rate': f"{r.hit_rate*100:.1f}%",
            'ROI': f"{r.roi_pct:.1f}%",
            'Profit': f"${r.total_profit:.2f}",
            'Avg Edge': f"{r.avg_edge:.2%}",
            'Max DD': f"${r.max_drawdown:.2f}",
            'Win Streak': r.win_streak,
            'Loss Streak': r.loss_streak,
        } for r in self.results])

    def save_results(self, output_file: str = "backtest_results.csv"):
        df = self.generate_report()
        if not df.empty:
            df.to_csv(output_file, index=False)
            print(f"Saved {output_file}")


def run_all_backtests():
    bt = HistoricalBacktest()
    sports = ['WNBA', 'MLB', 'NFL', 'NBA', 'NHL', 'WORLD_CUP']
    strategies = ['v1', 'v2', 'hybrid', 'ensemble']

    print("=" * 60)
    print("HISTORICAL BACKTEST - ALL SPORTS")
    print("=" * 60)

    for sport in sports:
        print(f"\nRunning backtest for {sport}...")
        df = bt.load_historical_data(sport)
        if df.empty:
            print(f"  No historical data for {sport}")
            continue
        bt.run_backtest(sport, df, strategies)
        rep = bt.generate_report()
        sub = rep[rep['Sport'] == sport]
        if not sub.empty:
            print(f"  {len(sub)} strategies tested ({len(df)} picks)")
            print(sub.to_string(index=False))

    print("\n" + "=" * 60)
    print("SUMMARY REPORT - ALL SPORTS")
    print("=" * 60)
    rep = bt.generate_report()
    if not rep.empty:
        print(rep.to_string(index=False))
        bt.save_results()


if __name__ == "__main__":
    run_all_backtests()
