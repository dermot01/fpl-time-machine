import requests
import json
import pandas as pd
import os
import time
import logging
import re
from bs4 import BeautifulSoup
from supabase import create_client, Client
from typing import Dict, List, Any, Optional, Tuple, Union

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UnderstatScraper:
    def __init__(self, season: int = 2016, limit_teams: int = 0):
        """
        Initialize the scraper.
        
        Args:
            season: The starting year of the season (e.g., 2016 for 2016-17)
            limit_teams: For testing, limit to this many teams (0 = no limit)
        """
        self.base_url = "https://understat.com"
        self.season = season
        self.limit_teams = limit_teams
        self.output_dir = "data/understat_data"
        self.session = requests.Session()
        
        # Headers to mimic a browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set up Supabase client if environment variables are set
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        self.supabase = None
        
        if supabase_url and supabase_key:
            self.supabase = create_client(supabase_url, supabase_key)
        else:
            logger.warning("Supabase environment variables not set. Database insertion disabled.")
    
    def _make_request(self, url: str, max_retries: int = 3):
        """
        Make an HTTP request with retry logic.
        
        Args:
            url: The URL to request
            max_retries: Maximum number of retry attempts
        
        Returns:
            Response object if successful, None otherwise
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, headers=self.headers)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    sleep_time = 2 ** attempt + 0.5
                    logger.info(f"Retrying in {sleep_time:.1f} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to retrieve {url} after {max_retries} attempts")
                    return None
    
    def _extract_json_data(self, response, pattern: str):
        """
        Extract JSON data from a script tag in the HTML.
        
        Args:
            response: Response object from requests
            pattern: Regex pattern to match the script containing the JSON data
        
        Returns:
            Parsed JSON data (can be dict, list, or any other JSON type)
        """
        try:
            if response is None:
                return {}
                
            soup = BeautifulSoup(response.text, 'html.parser')
            scripts = soup.find_all('script')
            
            for script in scripts:
                if script.string and re.search(pattern, script.string):
                    # Extract the JSON data from the script
                    json_str = re.search(r'JSON\.parse\(\'(.*)\'\)', script.string)
                    if json_str:
                        # Properly handle escaped characters
                        json_str = json_str.group(1).encode('utf-8').decode('unicode_escape')
                        return json.loads(json_str)
            
            logger.error(f"Could not find JSON data matching pattern {pattern}")
            return {}
        except Exception as e:
            logger.error(f"Error extracting JSON data: {e}")
            return {}
    
    def _save_to_csv(self, df: pd.DataFrame, filename: str):
        """
        Save DataFrame to CSV file.
        
        Args:
            df: DataFrame to save
            filename: Output filename
        """
        try:
            if df is None or df.empty:
                logger.warning(f"DataFrame is empty. Not saving {filename}")
                return
                
            filepath = os.path.join(self.output_dir, filename)
            df.to_csv(filepath, index=False)
            logger.info(f"Saved data to {filepath}")
        except Exception as e:
            logger.error(f"Error saving data to {filename}: {e}")
    
    def _insert_to_supabase(self, table_name: str, data: List[Dict[str, Any]]):
        """
        Insert data into Supabase.
        
        Args:
            table_name: Table name in Supabase
            data: List of records to insert
        """
        if not self.supabase:
            logger.warning("Supabase client not initialized. Skipping database insertion.")
            return
        
        if not data:
            logger.warning(f"No data to insert into {table_name}")
            return
        
        try:
            result = self.supabase.table(table_name).insert(data).execute()
            logger.info(f"Inserted {len(data)} records into {table_name}")
        except Exception as e:
            logger.error(f"Error inserting {table_name} into Supabase: {e}")
    
    def _normalize_team_name(self, name: str) -> str:
        """
        Normalize team names for consistency.
        
        Args:
            name: Original team name
        
        Returns:
            Normalized team name
        """
        name_map = {
            "Manchester United": "Man United",
            "Manchester City": "Man City",
            "Tottenham": "Tottenham Hotspur",
            "Newcastle United": "Newcastle",
            "West Ham": "West Ham United",
            "Leicester": "Leicester City",
            "Wolverhampton Wanderers": "Wolves",
            "Brighton": "Brighton & Hove Albion",
            "Norwich": "Norwich City",
            "Sheffield United": "Sheffield Utd",
            "Leeds": "Leeds United"
        }
        
        return name_map.get(name, name)
    
    def _normalize_data_structure(self, data, id_field: str = 'id'):
        """
        Normalize data structure to ensure consistent processing.
        
        Args:
            data: Data to normalize (could be dict, list, or other)
            id_field: Field name to use as dictionary key if data is a list
            
        Returns:
            Normalized dictionary
        """
        try:
            # If it's None or empty, return empty dict
            if not data:
                return {}
                
            # If it's already a dictionary, return it
            if isinstance(data, dict):
                return data
                
            # If it's a list, convert to dictionary using id_field as key
            if isinstance(data, list):
                result = {}
                for item in data:
                    # Ensure item is a dict and has the id field
                    if isinstance(item, dict) and id_field in item:
                        result[item[id_field]] = item
                    else:
                        # If item doesn't have id_field, generate a key
                        result[f"item_{len(result)}"] = item
                return result
                
            # For other types, wrap in a dictionary
            return {"data": data}
        except Exception as e:
            logger.error(f"Error normalizing data structure: {e}")
            return {}
    
    def _get_history_data(self, team_info: Dict) -> Dict:
        """
        Extract history data safely from team_info.
        
        Args:
            team_info: Team information dictionary
        
        Returns:
            History data dictionary
        """
        try:
            history = team_info.get('history', {})
            
            # Handle different possible history data structures
            if isinstance(history, list):
                # If history is a list, take the first item if available
                return history[0] if history else {}
            elif isinstance(history, dict):
                # If history is already a dictionary, use it directly
                return history
            else:
                # If history is neither list nor dict, return empty dict
                return {}
        except Exception as e:
            logger.error(f"Error processing history data: {e}")
            return {}
    
    def _extract_team_info(self, player_info: Dict) -> Tuple[str, str]:
        """
        Extract team information from player data.
        
        Args:
            player_info: Player information dictionary
            
        Returns:
            Tuple of (team_name, team_id)
        """
        try:
            team_name = ""
            team_id = ""
            
            # Handle different possible structures for team data
            if isinstance(player_info.get('team'), dict):
                team_name = player_info.get('team', {}).get('title', '')
                team_id = player_info.get('team', {}).get('id', '')
            elif player_info.get('team_title'):
                team_name = player_info.get('team_title', '')
                team_id = player_info.get('team_id', '')
            elif player_info.get('team_name'):
                team_name = player_info.get('team_name', '')
                team_id = player_info.get('team_id', '')
                
            return team_name, team_id
        except Exception as e:
            logger.error(f"Error extracting team info: {e}")
            return "", ""
    
    def _get_league_data(self):
        """
        Get league overview data including teams and players.
        
        Returns:
            Tuple of (teams_data, players_data)
        """
        url = f"{self.base_url}/league/epl/{self.season}"
        response = self._make_request(url)
        
        if not response:
            logger.error("Failed to retrieve league data")
            return {}, {}
        
        # Extract teams data
        teams_data = self._extract_json_data(response, r'teamsData')
        
        # Extract players data
        players_data = self._extract_json_data(response, r'playersData')
        
        return teams_data, players_data
    
    def _get_team_data(self, team_name: str, team_id: str):
        """
        Get detailed data for a specific team.
        
        Args:
            team_name: Name of the team
            team_id: Understat team ID
        
        Returns:
            Tuple of (players_data, matches_data)
        """
        url = f"{self.base_url}/team/{team_name}/{team_id}/{self.season}"
        response = self._make_request(url)
        
        if not response:
            logger.error(f"Failed to retrieve data for team {team_name}")
            return {}, {}
        
        # Extract players data
        players_data = self._extract_json_data(response, r'playersData')
        
        # Extract matches data
        matches_data = self._extract_json_data(response, r'datesData')
        
        return players_data, matches_data
    
    def _get_player_data(self, player_id: str) -> Dict:
        """
        Get detailed data for a specific player.
        
        Args:
            player_id: Understat player ID
        
        Returns:
            Player data dictionary
        """
        url = f"{self.base_url}/player/{player_id}/{self.season}"
        response = self._make_request(url)
        
        if not response:
            logger.error(f"Failed to retrieve data for player {player_id}")
            return {}
        
        # Extract player data
        player_data = self._extract_json_data(response, r'shotsData')
        
        # Extract grouped data
        grouped_data = self._extract_json_data(response, r'groupsData')
        
        return {
            'shots': player_data,
            'grouped': grouped_data
        }
    
    def scrape_league_overview(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Scrape league overview data.
        
        Returns:
            Tuple of (teams_df, players_df)
        """
        logger.info(f"Scraping EPL league overview for {self.season} season...")
        
        teams_data, players_data = self._get_league_data()
        
        # Normalize data structures to ensure consistent processing
        teams_data = self._normalize_data_structure(teams_data)
        
        # Process teams data
        teams_list = []
        if teams_data:
            for team_id, team_info in teams_data.items():
                try:
                    # Safely extract history data
                    history = self._get_history_data(team_info)
                    
                    team_dict = {
                        'team_id': team_id,
                        'title': team_info.get('title', ''),
                        'season': self.season,
                        'short_title': team_info.get('short_title', ''),
                        'matches': history.get('matchesPlayed', 0),
                        'wins': history.get('wins', 0),
                        'draws': history.get('draws', 0),
                        'loses': history.get('loses', 0),
                        'goals_for': history.get('goalsFor', 0),
                        'goals_against': history.get('goalsAgainst', 0),
                        'points': history.get('points', 0),
                        'xG': history.get('xG', 0),
                        'xGA': history.get('xGA', 0),
                        'npxG': history.get('npxG', 0),
                        'npxGA': history.get('npxGA', 0),
                        'deep': history.get('deep', 0),
                        'deep_allowed': history.get('deepAllowed', 0),
                        'scored': history.get('scored', 0),
                        'missed': history.get('missed', 0),
                        'xpts': history.get('xpts', 0),
                        'position': history.get('position', 0)
                    }
                    teams_list.append(team_dict)
                except Exception as e:
                    logger.error(f"Error processing team {team_id}: {e}")
        
        teams_df = pd.DataFrame(teams_list)
        if not teams_df.empty:
            logger.info(f"Saved league teams data with {len(teams_df)} teams")
            self._save_to_csv(teams_df, f"league_teams_{self.season}.csv")
            self._insert_to_supabase("understat_teams", teams_list)
        else:
            logger.warning("No teams data found")
        
        # Process players data - handle both list and dictionary formats
        players_list = []
        
        try:
            # Check if players_data is a list or dictionary and process accordingly
            if isinstance(players_data, list):
                # If it's a list, process each player directly
                for player in players_data:
                    try:
                        player_id = player.get('id', '')
                        
                        # Extract team information
                        team_name, team_id = self._extract_team_info(player)
                        
                        player_dict = {
                            'player_id': player_id,
                            'player_name': player.get('player_name', ''),
                            'team_name': team_name,
                            'team_id': team_id,
                            'season': self.season,
                            'games': player.get('games', 0),
                            'time': player.get('time', 0),
                            'goals': player.get('goals', 0),
                            'xG': player.get('xG', 0),
                            'assists': player.get('assists', 0),
                            'xA': player.get('xA', 0),
                            'shots': player.get('shots', 0),
                            'key_passes': player.get('key_passes', 0),
                            'yellow_cards': player.get('yellow_cards', 0),
                            'red_cards': player.get('red_cards', 0),
                            'position': player.get('position', ''),
                            'npg': player.get('npg', 0),
                            'npxG': player.get('npxG', 0),
                            'xGChain': player.get('xGChain', 0),
                            'xGBuildup': player.get('xGBuildup', 0)
                        }
                        players_list.append(player_dict)
                    except Exception as e:
                        logger.error(f"Error processing player in list: {e}")
            
            elif isinstance(players_data, dict):
                # If it's a dictionary, process using items()
                for player_id, player_info in players_data.items():
                    try:
                        # Extract team information
                        team_name, team_id = self._extract_team_info(player_info)
                        
                        player_dict = {
                            'player_id': player_id,
                            'player_name': player_info.get('player_name', ''),
                            'team_name': team_name,
                            'team_id': team_id,
                            'season': self.season,
                            'games': player_info.get('games', 0),
                            'time': player_info.get('time', 0),
                            'goals': player_info.get('goals', 0),
                            'xG': player_info.get('xG', 0),
                            'assists': player_info.get('assists', 0),
                            'xA': player_info.get('xA', 0),
                            'shots': player_info.get('shots', 0),
                            'key_passes': player_info.get('key_passes', 0),
                            'yellow_cards': player_info.get('yellow_cards', 0),
                            'red_cards': player_info.get('red_cards', 0),
                            'position': player_info.get('position', ''),
                            'npg': player_info.get('npg', 0),
                            'npxG': player_info.get('npxG', 0),
                            'xGChain': player_info.get('xGChain', 0),
                            'xGBuildup': player_info.get('xGBuildup', 0)
                        }
                        players_list.append(player_dict)
                    except Exception as e:
                        logger.error(f"Error processing player {player_id}: {e}")
            else:
                logger.error(f"Unexpected players_data type: {type(players_data)}")
        except Exception as e:
            logger.error(f"Error processing players data: {e}")
        
        players_df = pd.DataFrame(players_list)
        if not players_df.empty:
            logger.info(f"Saved league players data with {len(players_df)} players")
            self._save_to_csv(players_df, f"league_players_{self.season}.csv")
            self._insert_to_supabase("understat_players", players_list)
        else:
            logger.warning("No players data found")
        
        return teams_df, players_df
    
    def scrape_team_data(self, team_name: str, team_id: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Scrape detailed data for a specific team.
        
        Args:
            team_name: Team name
            team_id: Understat team ID
        
        Returns:
            Tuple of (players_df, matches_df)
        """
        logger.info(f"Scraping team data for {team_name}...")
        
        players_data, matches_data = self._get_team_data(team_name, team_id)
        
        # Normalize data structures
        players_data = self._normalize_data_structure(players_data)
        
        # Process players data
        players_list = []
        if players_data:
            for player_id, player_info in players_data.items():
                try:
                    player_dict = {
                        'player_id': player_id,
                        'player_name': player_info.get('player_name', ''),
                        'team_name': team_name,  # Use the provided team_name
                        'team_id': team_id,      # Use the provided team_id
                        'season': self.season,
                        'games': player_info.get('games', 0),
                        'time': player_info.get('time', 0),
                        'goals': player_info.get('goals', 0),
                        'xG': player_info.get('xG', 0),
                        'assists': player_info.get('assists', 0),
                        'xA': player_info.get('xA', 0),
                        'shots': player_info.get('shots', 0),
                        'key_passes': player_info.get('key_passes', 0),
                        'yellow_cards': player_info.get('yellow_cards', 0),
                        'red_cards': player_info.get('red_cards', 0),
                        'position': player_info.get('position', ''),
                        'npg': player_info.get('npg', 0),
                        'npxG': player_info.get('npxG', 0),
                        'xGChain': player_info.get('xGChain', 0),
                        'xGBuildup': player_info.get('xGBuildup', 0)
                    }
                    players_list.append(player_dict)
                except Exception as e:
                    logger.error(f"Error processing player {player_id} for team {team_name}: {e}")
        
        players_df = pd.DataFrame(players_list)
        if not players_df.empty:
            logger.info(f"Saved {team_name} players data with {len(players_df)} players")
            self._save_to_csv(players_df, f"team_{team_id}_players_{self.season}.csv")
            self._insert_to_supabase("understat_team_players", players_list)
        else:
            logger.warning(f"No players data found for {team_name}")
        
        # Process matches data - handle both list and dictionary formats
        matches_list = []
        try:
            if isinstance(matches_data, list):
                for match in matches_data:
                    try:
                        match_dict = self._process_match_data(match, team_name, team_id)
                        matches_list.append(match_dict)
                    except Exception as e:
                        logger.error(f"Error processing match for team {team_name}: {e}")
            elif isinstance(matches_data, dict):
                for match_id, match in matches_data.items():
                    try:
                        match['id'] = match_id  # Add id to the match data
                        match_dict = self._process_match_data(match, team_name, team_id)
                        matches_list.append(match_dict)
                    except Exception as e:
                        logger.error(f"Error processing match {match_id} for team {team_name}: {e}")
            else:
                logger.error(f"Unexpected matches_data type: {type(matches_data)}")
        except Exception as e:
            logger.error(f"Error processing matches data for team {team_name}: {e}")
        
        matches_df = pd.DataFrame(matches_list)
        if not matches_df.empty:
            logger.info(f"Saved {team_name} matches data with {len(matches_df)} matches")
            self._save_to_csv(matches_df, f"team_{team_id}_matches_{self.season}.csv")
            self._insert_to_supabase("understat_matches", matches_list)
        else:
            logger.warning(f"No matches data found for {team_name}")
        
        return players_df, matches_df
    
    def _process_match_data(self, match: Dict, team_name: str, team_id: str) -> Dict:
        """
        Process match data into a consistent format.
        
        Args:
            match: Match data dictionary
            team_name: Team name
            team_id: Team ID
            
        Returns:
            Processed match dictionary
        """
        # Handle different possible match data structures
        side = match.get('side', '')
        
        # Safe access to nested dictionaries
        def safe_get(data, *keys, default=0):
            current = data
            for key in keys:
                if not isinstance(current, dict):
                    return default
                current = current.get(key, {})
            return current if current is not None else default
        
        goals = safe_get(match, 'goals', 'h' if side == 'h' else 'a', default=0)
        goals_against = safe_get(match, 'goals', 'a' if side == 'h' else 'h', default=0)
        xG = safe_get(match, 'xG', 'h' if side == 'h' else 'a', default=0)
        xGA = safe_get(match, 'xG', 'a' if side == 'h' else 'h', default=0)
        deep = safe_get(match, 'deep', 'h' if side == 'h' else 'a', default=0)
        deep_against = safe_get(match, 'deep', 'a' if side == 'h' else 'h', default=0)
        ppda = safe_get(match, 'ppda', 'att', 'h' if side == 'h' else 'a', default=0)
        ppda_against = safe_get(match, 'ppda', 'att', 'a' if side == 'h' else 'h', default=0)
        shots = safe_get(match, 'shot', 'h' if side == 'h' else 'a', default=0)
        shots_against = safe_get(match, 'shot', 'a' if side == 'h' else 'h', default=0)
        
        return {
            'match_id': match.get('id', ''),
            'team_id': team_id,
            'team_name': team_name,
            'season': self.season,
            'date': match.get('datetime', ''),
            'side': side,
            'result': match.get('result', ''),
            'opponent_id': match.get('h_id' if side == 'a' else 'a_id', ''),
            'opponent_name': match.get('h_team' if side == 'a' else 'a_team', ''),
            'goals': goals,
            'goals_against': goals_against,
            'xG': xG,
            'xGA': xGA,
            'deep': deep,
            'deep_against': deep_against,
            'ppda': ppda,
            'ppda_against': ppda_against,
            'shots': shots,
            'shots_against': shots_against
        }
    
    def scrape_player_data(self, player_id: str, player_name: str, team_name: str, team_id: str) -> pd.DataFrame:
        """
        Scrape detailed data for a specific player.
        
        Args:
            player_id: Understat player ID
            player_name: Player name
            team_name: Team name
            team_id: Team ID
        
        Returns:
            DataFrame with player shots data
        """
        logger.info(f"Scraping player data for {player_name}...")
        
        player_data = self._get_player_data(player_id)
        
        # Process shots data
        shots_list = []
        try:
            shots_data = player_data.get('shots', [])
            
            # Handle different possible structures
            if isinstance(shots_data, dict):
                # Convert dict to list if necessary
                shots_data = list(shots_data.values())
            
            if isinstance(shots_data, list):
                for shot in shots_data:
                    try:
                        shot_dict = {
                            'player_id': player_id,
                            'player_name': player_name,
                            'team_name': team_name,
                            'team_id': team_id,
                            'season': self.season,
                            'match_id': shot.get('match_id', ''),
                            'minute': shot.get('minute', 0),
                            'result': shot.get('result', ''),
                            'X': shot.get('X', 0),
                            'Y': shot.get('Y', 0),
                            'xG': shot.get('xG', 0),
                            'assisted': shot.get('assisted', ''),
                            'key_pass_id': shot.get('key_pass_id', ''),
                            'shotType': shot.get('shotType', ''),
                            'situation': shot.get('situation', ''),
                            'lastAction': shot.get('lastAction', '')
                        }
                        shots_list.append(shot_dict)
                    except Exception as e:
                        logger.error(f"Error processing shot for player {player_name}: {e}")
            else:
                logger.error(f"Unexpected shots_data type: {type(shots_data)}")
        except Exception as e:
            logger.error(f"Error processing shots data for player {player_name}: {e}")
        
        shots_df = pd.DataFrame(shots_list)
        if not shots_df.empty:
            logger.info(f"Saved {player_name} shots data with {len(shots_df)} shots")
            self._save_to_csv(shots_df, f"player_{player_id}_shots_{self.season}.csv")
            self._insert_to_supabase("understat_player_shots", shots_list)
        else:
            logger.warning(f"No shots data found for {player_name}")
        
        return shots_df
    
    def run(self):
        """
        Run the scraper to collect all data.
        """
        try:
            logger.info(f"Starting Understat data scraping for {self.season} EPL season...")
            
            # Step 1: Scrape league overview data
            teams_df, players_df = self.scrape_league_overview()
            
            # Step 2: Scrape team data for each team
            if not teams_df.empty:
                # Ensure the necessary columns exist
                if 'team_id' not in teams_df.columns or 'title' not in teams_df.columns:
                    logger.error("Teams dataframe is missing required columns. Cannot proceed.")
                    return
                
                teams_processed = 0
                for _, team in teams_df.iterrows():
                    try:
                        team_id = team['team_id']
                        team_name = team['title']
                        
                        # Replace spaces in team name with underscores for URL
                        team_url_name = team_name.replace(' ', '_')
                        
                        # Scrape team data
                        team_players_df, matches_df = self.scrape_team_data(team_url_name, team_id)
                        
                        teams_processed += 1
                        
                        # Check if we've reached the limit
                        if self.limit_teams > 0 and teams_processed >= self.limit_teams:
                            logger.info(f"Reached team limit for testing. Remove limit for full import.")
                            break
                        
                        # Sleep to avoid hammering the server
                        time.sleep(1)
                    except Exception as e:
                        logger.error(f"Error processing team {team.get('title', 'unknown')}: {e}")
                        continue  # Continue with next team even if this one fails
            
            # Step 3: Scrape player data for top players
            if not players_df.empty:
                try:
                    # Sort by xG + xA to find the most productive players
                    # Convert columns to float and handle potential errors
                    players_df['xG'] = pd.to_numeric(players_df['xG'], errors='coerce')
                    players_df['xA'] = pd.to_numeric(players_df['xA'], errors='coerce')
                    
                    # Fill NaN values with 0
                    players_df['xG'] = players_df['xG'].fillna(0)
                    players_df['xA'] = players_df['xA'].fillna(0)
                    
                    # Calculate total contribution
                    players_df['total_contribution'] = players_df['xG'] + players_df['xA']
                    players_df = players_df.sort_values('total_contribution', ascending=False)
                except Exception as e:
                    logger.error(f"Error calculating player contributions: {e}")
                
                # Take top 20 players or fewer if limit_teams restricts it
                top_player_limit = 20 if self.limit_teams == 0 else min(20, self.limit_teams * 5)
                
                try:
                    top_players = players_df.head(top_player_limit)
                    
                    for _, player in top_players.iterrows():
                        try:
                            # Get player info
                            player_id = player['player_id']
                            player_name = player['player_name']
                            
                            # For team info, try different possible column names
                            team_name = ""
                            if 'team_name' in player and player['team_name']:
                                team_name = player['team_name']
                            elif 'team_title' in player and player['team_title']:
                                team_name = player['team_title']
                            else:
                                logger.warning(f"Could not determine team name for player {player_name}. Skipping.")
                                continue
                            
                            # Similarly for team_id
                            team_id = ""
                            if 'team_id' in player and player['team_id']:
                                team_id = player['team_id']
                            else:
                                # Try to find team_id from teams_df
                                team_match = teams_df[teams_df['title'] == team_name]
                                if not team_match.empty:
                                    team_id = team_match.iloc[0]['team_id']
                                else:
                                    logger.warning(f"Could not determine team ID for player {player_name}. Skipping.")
                                    continue
                            
                            # Team name with underscores for URL
                            team_url_name = team_name.replace(' ', '_')
                            
                            # Scrape player data
                            shots_df = self.scrape_player_data(player_id, player_name, team_url_name, team_id)
                            
                            # Sleep to avoid hammering the server
                            time.sleep(1)
                        except Exception as e:
                            logger.error(f"Error processing player {player.get('player_name', 'unknown')}: {e}")
                            continue  # Continue with next player even if this one fails
                except Exception as e:
                    logger.error(f"Error processing top players: {e}")
            
            logger.info(f"Understat data scraping for {self.season} EPL season completed!")
            logger.info(f"Data saved to {self.output_dir}/")
        except Exception as e:
            logger.error(f"Unhandled exception in main run method: {e}")

if __name__ == "__main__":
    try:
        # Set season and limit (limit=0 means no limit)
        scraper = UnderstatScraper(season=2016, limit_teams=3)
        scraper.run()
    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}")