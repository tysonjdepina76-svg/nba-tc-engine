-- TC Sports App Database Schema

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    team TEXT NOT NULL,
    sport TEXT NOT NULL,
    position TEXT,
    age INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, team, sport)
);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sport TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    game_date DATE NOT NULL,
    status TEXT DEFAULT 'scheduled',
    home_score INTEGER,
    away_score INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sport, home_team, away_team, game_date)
);

CREATE TABLE IF NOT EXISTS player_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    game_id INTEGER NOT NULL,
    points REAL,
    rebounds REAL,
    assists REAL,
    fg_pct REAL,
    fg3 REAL,
    steals REAL,
    blocks REAL,
    turnovers REAL,
    minutes REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (game_id) REFERENCES games(id),
    UNIQUE(player_id, game_id)
);

CREATE TABLE IF NOT EXISTS projections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    game_id INTEGER NOT NULL,
    stat_type TEXT NOT NULL,
    projection REAL NOT NULL,
    line REAL,
    edge REAL,
    signal TEXT,
    confidence REAL,
    model_version TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (game_id) REFERENCES games(id)
);

CREATE TABLE IF NOT EXISTS accuracy_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    stat_type TEXT NOT NULL,
    mae REAL,
    rmse REAL,
    mape REAL,
    volatility REAL,
    confidence_interval_low REAL,
    confidence_interval_high REAL,
    sample_size INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE TABLE IF NOT EXISTS bet_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    game_id INTEGER NOT NULL,
    stat_type TEXT NOT NULL,
    line REAL NOT NULL,
    stake REAL NOT NULL,
    odds INTEGER NOT NULL,
    platform TEXT,
    status TEXT DEFAULT 'pending',
    result REAL,
    profit REAL,
    roi REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (game_id) REFERENCES games(id)
);

CREATE TABLE IF NOT EXISTS player_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    game_id INTEGER NOT NULL,
    points REAL,
    rebounds REAL,
    assists REAL,
    fg_pct REAL,
    fg3 REAL,
    steals REAL,
    blocks REAL,
    turnovers REAL,
    minutes REAL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (game_id) REFERENCES games(id)
);

CREATE VIEW IF NOT EXISTS recent_accuracy AS
SELECT p.name, p.team, am.stat_type, am.mae, am.rmse, am.mape, am.volatility, am.sample_size
FROM accuracy_metrics am JOIN players p ON am.player_id = p.id
ORDER BY am.created_at DESC LIMIT 100;

CREATE VIEW IF NOT EXISTS performance_vs_projections AS
SELECT p.name, p.team, pr.stat_type, pr.projection, ps.points as actual, (ps.points - pr.projection) as diff
FROM projections pr
JOIN players p ON pr.player_id = p.id
JOIN player_stats ps ON pr.player_id = ps.player_id AND pr.game_id = ps.game_id
WHERE ps.points IS NOT NULL;

CREATE VIEW IF NOT EXISTS betting_roi AS
SELECT p.name, bt.stat_type, COUNT(*) as bets_placed, SUM(bt.profit) as total_profit, AVG(bt.roi) as avg_roi,
SUM(CASE WHEN bt.status = 'won' THEN 1 ELSE 0 END) as wins
FROM bet_tracking bt JOIN players p ON bt.player_id = p.id
GROUP BY p.name, bt.stat_type;

CREATE INDEX IF NOT EXISTS idx_players_name ON players(name);
CREATE INDEX IF NOT EXISTS idx_players_team ON players(team);
CREATE INDEX IF NOT EXISTS idx_players_sport ON players(sport);
CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date);
CREATE INDEX IF NOT EXISTS idx_games_status ON games(status);
CREATE INDEX IF NOT EXISTS idx_projections_player ON projections(player_id);
CREATE INDEX IF NOT EXISTS idx_projections_game ON projections(game_id);
CREATE INDEX IF NOT EXISTS idx_bet_tracking_player ON bet_tracking(player_id);
CREATE INDEX IF NOT EXISTS idx_bet_tracking_game ON bet_tracking(game_id);
CREATE INDEX IF NOT EXISTS idx_player_tracking_player ON player_tracking(player_id);
CREATE INDEX IF NOT EXISTS idx_player_tracking_game ON player_tracking(game_id);
