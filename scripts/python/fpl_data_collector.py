import requests
import pandas as pd
import os
import json
from supabase import create_client, Client
from typing import Optional, Dict, List, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
BASE_URL = "https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data"
SEASON = "2016-17"
OUTPUT_DIR = "data/fpl_data"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Set up Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

def fetch_data(url: str, encoding: str = 'utf-8') -> pd.DataFrame:
    """Fetch data from a URL and return as a DataFrame."""
    try:
        logger.info(f"Fetching data from {url}")
        response = requests.get(url)
        response.raise_for_status()
        
        # Try different encodings if utf-8 fails
        try:
            return pd.read_csv(response.content.decode(encoding))
        except UnicodeDecodeError:
            # Try with different encodings
            for enc in ['latin-1', 'ISO-8859-1', 'cp1252']:
                try:
                    return pd.read_csv(response.content.decode(enc))
                except UnicodeDecodeError:
                    continue
            
            # If all fail, use pandas with encoding parameter
            return pd.read_csv(response.content, encoding='latin-1')
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from {url}: {e}")
        return pd.DataFrame()

def save_to_csv(df: pd.DataFrame, filename: str) -> None:
    """Save DataFrame to CSV file."""
    filepath = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(filepath, index=False)
    logger.info(f"Saved data to {filepath}")

def insert_to_supabase(table_name: str, data: List[Dict[str, Any]]) -> None:
    """Insert data into Supabase."""
    if not supabase:
        logger.warning("Supabase client not initialized. Skipping database insertion.")
        return
    
    if not data:
        logger.warning(f"No data to insert into {table_name}")
        return
    
    try:
        result = supabase.table(table_name).insert(data).execute()
        logger.info(f"Inserted {len(data)} records into {table_name}")
    except Exception as e:
        logger.error(f"Error inserting {table_name} into Supabase: {e}")

def process_teams_data() -> pd.DataFrame:
    """Process teams data."""
    logger.info("Processing teams data...")
    
    # For 2016-17, the teams.csv might not exist in the expected location
    # Let's create it from another source or use an alternative method
    
    # Alternative 1: Use teams from a more recent season and adjust as needed
    teams_url = f"{BASE_URL}/2017-18/teams.csv"  # Try using next season's data
    teams_df = fetch_data(teams_url)
    
    if teams_df.empty:
        # Alternative 2: Create a basic teams dataframe manually with the 20 EPL teams from 2016-17
        teams_data = [
            {"id": 1, "name": "Arsenal"},
            {"id": 2, "name": "Bournemouth"},
            {"id": 3, "name": "Burnley"},
            {"id": 4, "name": "Chelsea"},
            {"id": 5, "name": "Crystal Palace"},
            {"id": 6, "name": "Everton"},
            {"id": 7, "name": "Hull City"},
            {"id": 8, "name": "Leicester City"},
            {"id": 9, "name": "Liverpool"},
            {"id": 10, "name": "Manchester City"},
            {"id": 11, "name": "Manchester United"},
            {"id": 12, "name": "Middlesbrough"},
            {"id": 13, "name": "Southampton"},
            {"id": 14, "name": "Stoke City"},
            {"id": 15, "name": "Sunderland"},
            {"id": 16, "name": "Swansea City"},
            {"id": 17, "name": "Tottenham Hotspur"},
            {"id": 18, "name": "Watford"},
            {"id": 19, "name": "West Bromwich Albion"},
            {"id": 20, "name": "West Ham United"}
        ]
        teams_df = pd.DataFrame(teams_data)
    
    # Save to CSV
    save_to_csv(teams_df, "teams.csv")
    
    # Insert into Supabase
    if not teams_df.empty:
        insert_to_supabase("teams", teams_df.to_dict(orient="records"))
    
    return teams_df

def process_positions_data() -> pd.DataFrame:
    """Process positions data."""
    logger.info("Processing positions data...")
    
    # Positions are generally consistent across seasons
    positions_data = [
        {"id": 1, "name": "Goalkeeper", "short_name": "GKP"},
        {"id": 2, "name": "Defender", "short_name": "DEF"},
        {"id": 3, "name": "Midfielder", "short_name": "MID"},
        {"id": 4, "name": "Forward", "short_name": "FWD"}
    ]
    positions_df = pd.DataFrame(positions_data)
    
    # Save to CSV
    save_to_csv(positions_df, "positions.csv")
    
    # Insert into Supabase
    insert_to_supabase("positions", positions_df.to_dict(orient="records"))
    
    return positions_df

def process_players_data() -> pd.DataFrame:
    """Process players data."""
    logger.info("Processing players data...")
    
    # Try to fetch players data
    url = f"{BASE_URL}/{SEASON}/players_raw.csv"
    players_df = fetch_data(url)
    
    if not players_df.empty:
        # Save to CSV
        save_to_csv(players_df, "players.csv")
        
        # Insert into Supabase
        # This will work now because we've inserted teams first
        insert_to_supabase("players", players_df.to_dict(orient="records"))
    else:
        logger.error("Failed to fetch players data")
    
    return players_df

def process_gameweeks_data() -> pd.DataFrame:
    """Process gameweeks data."""
    logger.info("Processing gameweeks data...")
    
    # For 2016-17, we might need to create gameweeks manually if we can't fetch them
    url = f"{BASE_URL}/{SEASON}/events.csv"
    gameweeks_df = fetch_data(url)
    
    if gameweeks_df.empty:
        # Create basic gameweeks data manually
        gameweeks_data = []
        for i in range(1, 39):  # 38 gameweeks in a season
            gameweeks_data.append({
                "id": i,
                "name": f"Gameweek {i}",
                "deadline_time": f"2016-{8 + (i // 4)}-{1 + (i % 4) * 7}"  # Approximate dates
            })
        gameweeks_df = pd.DataFrame(gameweeks_data)
    
    # Save to CSV
    save_to_csv(gameweeks_df, "gameweeks.csv")
    
    # Insert into Supabase
    insert_to_supabase("gameweeks", gameweeks_df.to_dict(orient="records"))
    
    return gameweeks_df

def process_fixtures_data() -> pd.DataFrame:
    """Process fixtures data."""
    logger.info("Processing fixtures data...")
    
    url = f"{BASE_URL}/{SEASON}/fixtures.csv"
    fixtures_df = fetch_data(url)
    
    if not fixtures_df.empty:
        # Save to CSV
        save_to_csv(fixtures_df, "fixtures.csv")
        
        # Insert into Supabase
        insert_to_supabase("fixtures", fixtures_df.to_dict(orient="records"))
    else:
        logger.error("Failed to fetch fixtures data")
    
    return fixtures_df

def process_player_gameweek_history(players_df: pd.DataFrame) -> pd.DataFrame:
    """Process player gameweek history."""
    logger.info("Processing player gameweek history...")
    
    all_gw_data = []
    
    # Limit to a smaller subset of players for testing
    player_ids = players_df['id'].tolist() if not players_df.empty else range(1, 21)
    
    for player_id in player_ids:
        player_name = players_df[players_df['id'] == player_id]['web_name'].values[0] if not players_df.empty else f"Player_{player_id}"
        logger.info(f"Processing player {player_id} ({player_name})")
        
        # Try to fetch player's gameweek data
        url = f"{BASE_URL}/{SEASON}/players/{player_id}/gw.csv"
        
        try:
            # Handle different encodings
            player_gw_df = fetch_data(url, encoding='latin-1')
            
            if not player_gw_df.empty:
                # Add player ID to the data
                player_gw_df['player_id'] = player_id
                all_gw_data.append(player_gw_df)
            else:
                logger.warning(f"No gameweek data for player {player_id}")
        except Exception as e:
            logger.error(f"Error processing gameweek data for player {player_id}: {e}")
    
    # Combine all player gameweek data
    if all_gw_data:
        combined_gw_df = pd.concat(all_gw_data, ignore_index=True)
        save_to_csv(combined_gw_df, "player_gameweek_stats.csv")
        insert_to_supabase("player_gameweek_stats", combined_gw_df.to_dict(orient="records"))
        return combined_gw_df
    else:
        logger.warning("No player gameweek data collected")
        return pd.DataFrame()

def process_player_season_stats(players_df: pd.DataFrame) -> pd.DataFrame:
    """Process player season stats."""
    logger.info("Processing player season stats...")
    
    all_season_data = []
    
    # Limit to a smaller subset of players for testing
    player_ids = players_df['id'].tolist() if not players_df.empty else range(1, 21)
    
    for player_id in player_ids:
        # Try to fetch player's season history
        url = f"{BASE_URL}/{SEASON}/players/{player_id}/history.csv"
        
        try:
            player_history_df = fetch_data(url, encoding='latin-1')
            
            if not player_history_df.empty:
                # Add player ID to the data
                player_history_df['player_id'] = player_id
                all_season_data.append(player_history_df)
            else:
                logger.warning(f"No season history file for player {player_id}")
        except Exception as e:
            logger.error(f"Error processing season history for player {player_id}: {e}")
    
    # Combine all player season data
    if all_season_data:
        combined_season_df = pd.concat(all_season_data, ignore_index=True)
        save_to_csv(combined_season_df, "player_season_stats.csv")
        
        # Fix column names for Supabase insertion
        if not combined_season_df.empty:
            # Remove any empty columns
            combined_season_df = combined_season_df.dropna(axis=1, how='all')
            
            # Insert into Supabase
            insert_to_supabase("player_season_stats", combined_season_df.to_dict(orient="records"))
        
        return combined_season_df
    else:
        logger.warning("No player season data collected")
        empty_df = pd.DataFrame()
        save_to_csv(empty_df, "player_season_stats.csv")
        return empty_df

def process_player_price_history() -> pd.DataFrame:
    """Process player price history."""
    logger.info("Processing player price history...")
    
    all_price_data = []
    
    for gw in range(1, 39):  # 38 gameweeks in a season
        logger.info(f"Processing prices for gameweek {gw}...")
        
        # Try to fetch gameweek data
        url = f"{BASE_URL}/{SEASON}/gws/gw{gw}.csv"
        
        try:
            # Try different encodings
            gw_df = fetch_data(url, encoding='latin-1')
            
            if not gw_df.empty:
                # Add gameweek number to the data
                gw_df['gameweek'] = gw
                
                # Extract player ID and price
                price_df = gw_df[['id', 'gameweek', 'value']].rename(columns={'id': 'player_id', 'value': 'price'})
                all_price_data.append(price_df)
            else:
                logger.warning(f"No data for gameweek {gw}")
        except Exception as e:
            logger.error(f"Error processing gameweek {gw}: {e}")
    
    # Combine all price data
    if all_price_data:
        combined_price_df = pd.concat(all_price_data, ignore_index=True)
        save_to_csv(combined_price_df, "player_price_history.csv")
        insert_to_supabase("player_price_history", combined_price_df.to_dict(orient="records"))
        return combined_price_df
    else:
        logger.warning("No player price data collected")
        empty_df = pd.DataFrame()
        save_to_csv(empty_df, "player_price_history.csv")
        return empty_df

def main():
    """Main function to run the data collection process."""
    logger.info(f"Starting FPL data collection for {SEASON} season...")
    
    # Process teams data first (required for player foreign key constraint)
    teams_df = process_teams_data()
    
    # Process positions data
    positions_df = process_positions_data()
    
    # Process players data
    players_df = process_players_data()
    
    # Process gameweeks data
    gameweeks_df = process_gameweeks_data()
    
    # Process fixtures data
    fixtures_df = process_fixtures_data()
    
    # Process player gameweek history
    player_gw_df = process_player_gameweek_history(players_df)
    
    # Process player season stats
    player_season_df = process_player_season_stats(players_df)
    
    # Process player price history
    player_price_df = process_player_price_history()
    
    logger.info(f"FPL data collection for {SEASON} completed!")
    logger.info(f"Data saved to {OUTPUT_DIR}/")

if __name__ == "__main__":
    main()