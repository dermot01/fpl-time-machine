-- FPL Time Machine Database Schema for 2016/17 Season
-- This script creates all necessary tables in Supabase for the FPL simulator project

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core Tables
---------------------------------------------

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    code INTEGER,
    logo TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Positions table
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY,
    singular_name TEXT NOT NULL,
    plural_name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Players table
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    code INTEGER,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    web_name TEXT NOT NULL,
    team_id INTEGER REFERENCES teams(id),
    position_id INTEGER REFERENCES positions(id),
    photo TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Gameweeks table
CREATE TABLE IF NOT EXISTS gameweeks (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    deadline_time TIMESTAMP WITH TIME ZONE,
    is_current BOOLEAN DEFAULT FALSE,
    is_next BOOLEAN DEFAULT FALSE,
    is_previous BOOLEAN DEFAULT FALSE,
    finished BOOLEAN DEFAULT FALSE,
    data_checked BOOLEAN DEFAULT FALSE,
    highest_score INTEGER,
    average_score INTEGER,
    chip_plays JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Fixtures table
CREATE TABLE IF NOT EXISTS fixtures (
    id INTEGER PRIMARY KEY,
    gameweek_id INTEGER REFERENCES gameweeks(id),
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    kickoff_time TIMESTAMP WITH TIME ZONE,
    home_team_score INTEGER,
    away_team_score INTEGER,
    finished BOOLEAN DEFAULT FALSE,
    minutes INTEGER,
    provisional_start_time BOOLEAN,
    team_h_difficulty INTEGER,
    team_a_difficulty INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Player Performance Data
---------------------------------------------

-- Player gameweek stats table
CREATE TABLE IF NOT EXISTS player_gameweek_stats (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    gameweek_id INTEGER REFERENCES gameweeks(id),
    fixture_id INTEGER REFERENCES fixtures(id),
    minutes INTEGER DEFAULT 0,
    goals_scored INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    clean_sheets INTEGER DEFAULT 0,
    goals_conceded INTEGER DEFAULT 0,
    own_goals INTEGER DEFAULT 0,
    penalties_saved INTEGER DEFAULT 0,
    penalties_missed INTEGER DEFAULT 0,
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    bonus INTEGER DEFAULT 0,
    bps INTEGER DEFAULT 0,
    influence NUMERIC(5,1) DEFAULT 0,
    creativity NUMERIC(5,1) DEFAULT 0,
    threat NUMERIC(5,1) DEFAULT 0,
    ict_index NUMERIC(5,1) DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    xg NUMERIC(5,2),
    xa NUMERIC(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, gameweek_id, fixture_id)
);

-- Player price history table
CREATE TABLE IF NOT EXISTS player_price_history (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    gameweek_id INTEGER REFERENCES gameweeks(id),
    price INTEGER NOT NULL, -- Stored in 10ths, e.g., 75 = £7.5m
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, gameweek_id)
);

-- Player season stats table
CREATE TABLE IF NOT EXISTS player_season_stats (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    points_per_game NUMERIC(3,1) DEFAULT 0,
    minutes INTEGER DEFAULT 0,
    goals_scored INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    clean_sheets INTEGER DEFAULT 0,
    goals_conceded INTEGER DEFAULT 0,
    own_goals INTEGER DEFAULT 0,
    penalties_saved INTEGER DEFAULT 0,
    penalties_missed INTEGER DEFAULT 0,
    yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    bonus INTEGER DEFAULT 0,
    bps INTEGER DEFAULT 0,
    form NUMERIC(4,1) DEFAULT 0,
    selected_by_percent NUMERIC(4,1) DEFAULT 0, -- Snapshot from end of season
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id)
);

-- News & Events
---------------------------------------------

-- Team news table
CREATE TABLE IF NOT EXISTS team_news (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id),
    gameweek_id INTEGER REFERENCES gameweeks(id),
    news_type TEXT NOT NULL, -- e.g., 'injury', 'manager_change', 'transfer'
    headline TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT,
    published_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Player news table
CREATE TABLE IF NOT EXISTS player_news (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    gameweek_id INTEGER REFERENCES gameweeks(id),
    news_type TEXT NOT NULL, -- e.g., 'injury', 'suspension', 'transfer'
    headline TEXT NOT NULL,
    content TEXT NOT NULL,
    chance_of_playing_next_round INTEGER, -- percentage
    chance_of_playing_this_round INTEGER, -- percentage
    expected_return_date TEXT,
    source TEXT,
    published_date TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- FPL events table
CREATE TABLE IF NOT EXISTS fpl_events (
    id SERIAL PRIMARY KEY,
    gameweek_id INTEGER REFERENCES gameweeks(id),
    event_type TEXT NOT NULL, -- e.g., 'double_gameweek', 'blank_gameweek'
    announcement_gameweek_id INTEGER REFERENCES gameweeks(id), -- when it was announced
    headline TEXT NOT NULL,
    content TEXT NOT NULL,
    teams_affected INTEGER[], -- Array of team_ids
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Predicted lineups table
CREATE TABLE IF NOT EXISTS predicted_lineups (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id),
    gameweek_id INTEGER REFERENCES gameweeks(id),
    formation TEXT,
    lineup JSONB, -- Array of player IDs with positions
    source TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_id, gameweek_id)
);

-- Competition Data
---------------------------------------------

-- European matches table
CREATE TABLE IF NOT EXISTS european_matches (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id),
    competition TEXT NOT NULL, -- e.g., 'UCL', 'UEL'
    match_date TIMESTAMP WITH TIME ZONE,
    opponent TEXT NOT NULL,
    is_home BOOLEAN,
    result TEXT, -- e.g., 'W', 'L', 'D'
    score TEXT,
    gameweek_before INTEGER REFERENCES gameweeks(id), -- FPL gameweek just before this match
    gameweek_after INTEGER REFERENCES gameweeks(id), -- FPL gameweek just after this match
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Domestic cup matches table
CREATE TABLE IF NOT EXISTS domestic_cup_matches (
    id SERIAL PRIMARY KEY,
    team_id INTEGER REFERENCES teams(id),
    competition TEXT NOT NULL, -- e.g., 'FA Cup', 'League Cup'
    match_date TIMESTAMP WITH TIME ZONE,
    opponent TEXT NOT NULL,
    is_home BOOLEAN,
    result TEXT, -- e.g., 'W', 'L', 'D'
    score TEXT,
    round TEXT,
    gameweek_before INTEGER REFERENCES gameweeks(id), -- FPL gameweek just before this match
    gameweek_after INTEGER REFERENCES gameweeks(id), -- FPL gameweek just after this match
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User Management & Game State
---------------------------------------------

-- User teams table
CREATE TABLE IF NOT EXISTS user_teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id),
    team_name TEXT NOT NULL,
    season_year TEXT NOT NULL, -- e.g., '2016-17'
    current_gameweek_id INTEGER REFERENCES gameweeks(id),
    budget INTEGER DEFAULT 1000, -- £100.0m in tenths
    bank INTEGER DEFAULT 0, -- Available funds in tenths
    total_points INTEGER DEFAULT 0,
    overall_rank INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User team gameweeks table
CREATE TABLE IF NOT EXISTS user_team_gameweeks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_team_id UUID REFERENCES user_teams(id),
    gameweek_id INTEGER REFERENCES gameweeks(id),
    active_chip TEXT, -- 'wildcard', 'bench_boost', 'free_hit', 'triple_captain', null
    points INTEGER DEFAULT 0,
    transfers INTEGER DEFAULT 0,
    transfer_cost INTEGER DEFAULT 0,
    points_on_bench INTEGER DEFAULT 0,
    rank INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_team_id, gameweek_id)
);

-- User team players table
CREATE TABLE IF NOT EXISTS user_team_players (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_team_id UUID REFERENCES user_teams(id),
    gameweek_id INTEGER REFERENCES gameweeks(id),
    player_id INTEGER REFERENCES players(id),
    position INTEGER NOT NULL, -- 1-15, where 1-11 are starters
    is_captain BOOLEAN DEFAULT FALSE,
    is_vice_captain BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_team_id, gameweek_id, player_id)
);

-- User transfers table
CREATE TABLE IF NOT EXISTS user_transfers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_team_id UUID REFERENCES user_teams(id),
    gameweek_id INTEGER REFERENCES gameweeks(id),
    player_in_id INTEGER REFERENCES players(id),
    player_out_id INTEGER REFERENCES players(id),
    price_in INTEGER NOT NULL,
    price_out INTEGER NOT NULL,
    transfer_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Additional utility views
---------------------------------------------

-- View to get current gameweek player prices
CREATE OR REPLACE VIEW current_player_prices AS
SELECT 
    p.id,
    p.web_name,
    p.team_id,
    p.position_id,
    ph.price,
    ph.gameweek_id
FROM 
    players p
JOIN 
    player_price_history ph ON p.id = ph.player_id
JOIN 
    (SELECT player_id, MAX(gameweek_id) as max_gameweek 
     FROM player_price_history 
     GROUP BY player_id) latest 
ON 
    ph.player_id = latest.player_id AND ph.gameweek_id = latest.max_gameweek;

-- View to get player total points by gameweek
CREATE OR REPLACE VIEW player_gameweek_points AS
SELECT 
    p.id,
    p.web_name,
    p.team_id,
    p.position_id,
    pgs.gameweek_id,
    SUM(pgs.total_points) as total_points
FROM 
    players p
JOIN 
    player_gameweek_stats pgs ON p.id = pgs.player_id
GROUP BY 
    p.id, p.web_name, p.team_id, p.position_id, pgs.gameweek_id;

-- View to get fixture difficulty rating
CREATE OR REPLACE VIEW fixture_difficulty AS
SELECT
    f.id as fixture_id,
    f.gameweek_id,
    f.home_team_id,
    f.away_team_id,
    ht.short_name as home_team,
    at.short_name as away_team,
    f.team_h_difficulty as home_difficulty,
    f.team_a_difficulty as away_difficulty,
    f.kickoff_time
FROM
    fixtures f
JOIN
    teams ht ON f.home_team_id = ht.id
JOIN
    teams at ON f.away_team_id = at.id;

-- View for player form over 3 gameweeks
CREATE OR REPLACE VIEW player_form AS
WITH player_points AS (
    SELECT
        player_id,
        gameweek_id,
        SUM(total_points) as gw_points
    FROM
        player_gameweek_stats
    GROUP BY
        player_id, gameweek_id
)
SELECT
    p.id as player_id,
    p.web_name,
    p.team_id,
    t.short_name as team,
    pos.short_name as position,
    pp.gameweek_id,
    pp.gw_points as current_gw_points,
    ROUND(AVG(pp.gw_points) OVER (
        PARTITION BY p.id 
        ORDER BY pp.gameweek_id 
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 1) as form_3gw
FROM
    players p
JOIN
    teams t ON p.team_id = t.id
JOIN
    positions pos ON p.position_id = pos.id
JOIN
    player_points pp ON p.id = pp.player_id;

-- Functions for the FPL Game Engine
---------------------------------------------

-- Function to calculate points for a user team in a gameweek
CREATE OR REPLACE FUNCTION calculate_user_team_points(
    p_user_team_id UUID,
    p_gameweek_id INTEGER
)
RETURNS INTEGER AS $
DECLARE
    v_total_points INTEGER := 0;
    v_captain_points INTEGER := 0;
    v_active_chip TEXT;
    v_captain_id INTEGER;
    v_vice_captain_id INTEGER;
    v_captain_played BOOLEAN := FALSE;
BEGIN
    -- Get active chip
    SELECT active_chip INTO v_active_chip
    FROM user_team_gameweeks
    WHERE user_team_id = p_user_team_id AND gameweek_id = p_gameweek_id;
    
    -- Get captain and vice-captain
    SELECT player_id INTO v_captain_id
    FROM user_team_players
    WHERE user_team_id = p_user_team_id 
    AND gameweek_id = p_gameweek_id
    AND is_captain = TRUE;
    
    SELECT player_id INTO v_vice_captain_id
    FROM user_team_players
    WHERE user_team_id = p_user_team_id 
    AND gameweek_id = p_gameweek_id
    AND is_vice_captain = TRUE;
    
    -- Check if captain played
    SELECT EXISTS(
        SELECT 1 
        FROM player_gameweek_stats 
        WHERE player_id = v_captain_id 
        AND gameweek_id = p_gameweek_id
        AND minutes > 0
    ) INTO v_captain_played;
    
    -- Calculate total points for starting 11 players
    SELECT COALESCE(SUM(
        CASE 
            -- Triple captain: captain points x3
            WHEN utp.is_captain AND v_active_chip = 'triple_captain' THEN pgs.total_points * 3
            -- Regular captain: captain points x2
            WHEN utp.is_captain THEN pgs.total_points * 2
            -- Vice captain points x2 if captain didn't play
            WHEN utp.is_vice_captain AND NOT v_captain_played THEN pgs.total_points * 2
            -- Regular players
            ELSE pgs.total_points
        END
    ), 0)
    INTO v_total_points
    FROM user_team_players utp
    JOIN player_gameweek_stats pgs 
        ON utp.player_id = pgs.player_id 
        AND utp.gameweek_id = pgs.gameweek_id
    WHERE utp.user_team_id = p_user_team_id
    AND utp.gameweek_id = p_gameweek_id
    AND utp.position <= 11;  -- Starting players only
    
    -- If bench boost is active, add points from bench
    IF v_active_chip = 'bench_boost' THEN
        SELECT COALESCE(SUM(pgs.total_points), 0)
        INTO v_captain_points
        FROM user_team_players utp
        JOIN player_gameweek_stats pgs 
            ON utp.player_id = pgs.player_id 
            AND utp.gameweek_id = pgs.gameweek_id
        WHERE utp.user_team_id = p_user_team_id
        AND utp.gameweek_id = p_gameweek_id
        AND utp.position > 11;  -- Bench players
        
        v_total_points := v_total_points + v_captain_points;
    END IF;
    
    RETURN v_total_points;
END;
$ LANGUAGE plpgsql;

-- Function to get a user's team for a specific gameweek
CREATE OR REPLACE FUNCTION get_user_team(
    p_user_team_id UUID,
    p_gameweek_id INTEGER
)
RETURNS TABLE (
    player_id INTEGER,
    web_name TEXT,
    team_short_name TEXT,
    position_name TEXT,
    price INTEGER,
    total_points INTEGER,
    is_captain BOOLEAN,
    is_vice_captain BOOLEAN,
    team_position INTEGER
) AS $
BEGIN
    RETURN QUERY
    SELECT
        p.id as player_id,
        p.web_name,
        t.short_name as team_short_name,
        pos.short_name as position_name,
        pph.price,
        COALESCE(pgs.total_points, 0) as total_points,
        utp.is_captain,
        utp.is_vice_captain,
        utp.position as team_position
    FROM
        user_team_players utp
    JOIN
        players p ON utp.player_id = p.id
    JOIN
        teams t ON p.team_id = t.id
    JOIN
        positions pos ON p.position_id = pos.id
    LEFT JOIN
        player_price_history pph ON p.id = pph.player_id AND pph.gameweek_id = p_gameweek_id
    LEFT JOIN
        player_gameweek_stats pgs ON p.id = pgs.player_id AND pgs.gameweek_id = p_gameweek_id
    WHERE
        utp.user_team_id = p_user_team_id
        AND utp.gameweek_id = p_gameweek_id
    ORDER BY
        utp.position;
END;
$ LANGUAGE plpgsql;

-- Function to create a new user team
CREATE OR REPLACE FUNCTION create_user_team(
    p_user_id UUID,
    p_team_name TEXT,
    p_season_year TEXT DEFAULT '2016-17'
)
RETURNS UUID AS $
DECLARE
    v_team_id UUID;
BEGIN
    -- Create the team
    INSERT INTO user_teams (user_id, team_name, season_year, current_gameweek_id, budget)
    VALUES (p_user_id, p_team_name, p_season_year, 1, 1000)
    RETURNING id INTO v_team_id;
    
    -- Create initial gameweek record
    INSERT INTO user_team_gameweeks (user_team_id, gameweek_id, transfers)
    VALUES (v_team_id, 1, 0);
    
    RETURN v_team_id;
END;
$ LANGUAGE plpgsql;

-- Row-Level Security Policies
---------------------------------------------

-- Enable RLS on user-related tables
ALTER TABLE user_teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_team_gameweeks ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_team_players ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_transfers ENABLE ROW LEVEL SECURITY;

-- Create policies to restrict access to a user's own data
CREATE POLICY user_teams_policy ON user_teams
    FOR ALL
    USING (auth.uid() = user_id);

CREATE POLICY user_team_gameweeks_policy ON user_team_gameweeks
    FOR ALL
    USING (user_team_id IN (SELECT id FROM user_teams WHERE user_id = auth.uid()));

CREATE POLICY user_team_players_policy ON user_team_players
    FOR ALL
    USING (user_team_id IN (SELECT id FROM user_teams WHERE user_id = auth.uid()));

CREATE POLICY user_transfers_policy ON user_transfers
    FOR ALL
    USING (user_team_id IN (SELECT id FROM user_teams WHERE user_id = auth.uid()));

-- Indices for performance
---------------------------------------------

-- Add indices for commonly queried fields
CREATE INDEX IF NOT EXISTS idx_pgw_player_gameweek ON player_gameweek_stats(player_id, gameweek_id);
CREATE INDEX IF NOT EXISTS idx_player_price_history ON player_price_history(player_id, gameweek_id);
CREATE INDEX IF NOT EXISTS idx_fixtures_gameweek ON fixtures(gameweek_id);
CREATE INDEX IF NOT EXISTS idx_players_team ON players(team_id);
CREATE INDEX IF NOT EXISTS idx_user_team_gameweeks ON user_team_gameweeks(user_team_id, gameweek_id);
CREATE INDEX IF NOT EXISTS idx_user_team_players ON user_team_players(user_team_id, gameweek_id);

-- Add composite indices for performance on complex queries
CREATE INDEX IF NOT EXISTS idx_fixture_teams ON fixtures(home_team_id, away_team_id);
CREATE INDEX IF NOT EXISTS idx_player_team_position ON players(team_id, position_id);
CREATE INDEX IF NOT EXISTS idx_user_transfers_gameweek ON user_transfers(user_team_id, gameweek_id);