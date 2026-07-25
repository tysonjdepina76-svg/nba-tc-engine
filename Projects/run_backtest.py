from backtest_engine import BacktestEngine
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='Run sports betting backtest')
    parser.add_argument('--sport', type=str, help='Filter by sport (NFL, NBA, MLB, WNBA)')
    parser.add_argument('--from-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--to-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--bet-amount', type=float, default=100.0, help='Bet amount per pick')
    parser.add_argument('--report', action='store_true', help='Generate summary report')

    args = parser.parse_args()

    engine = BacktestEngine()
    results = engine.run_backtest(
        sport=args.sport,
        from_date=args.from_date,
        to_date=args.to_date,
        bet_amount=args.bet_amount
    )

    if 'error' in results:
        print(f"{results['error']}")
        return

    summary = results['summary']

    print("\n" + "="*60)
    print("BACKTEST RESULTS")
    print("="*60)
    print(f"\nOverall:")
    print(f"   Total Picks: {summary['total_picks']}")
    print(f"   Win/Loss/Push: {summary['wins']}/{summary['losses']}/{summary['pushes']}")
    print(f"   Win Rate: {summary['win_rate']}%")
    print(f"   Total Profit: ${summary['total_profit']:.2f}")
    print(f"   ROI: {summary['total_roi']}%")
    print(f"   Avg Profit/Bet: ${summary['avg_profit_per_bet']:.2f}")
    print(f"   Best/Worst Streak: {summary['best_streak']}/{summary['worst_streak']}")

    if args.report:
        print("\n" + engine.generate_report())

    df = engine.get_performance_by_sport()
    if not df.empty:
        print("\nBest Sport:")
        top = df.iloc[0]
        print(f"   {top['sport']}: {top['wins']}W-{top['losses']}L | +${top['total_profit']:.2f}")

    df_conf = engine.get_performance_by_confidence()
    if not df_conf.empty:
        print("\nConfidence Performance:")
        for _, row in df_conf.iterrows():
            print(f"   {row['confidence_level']}: +${row['total_profit']:.2f} ({row['wins']}W-{row['losses']}L)")

if __name__ == "__main__":
    main()
