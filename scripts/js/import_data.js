/**
 * FPL Time Machine - Data Import Script
 * 
 * This script imports the collected FPL 2016/17 season data into Supabase.
 * It requires the data files to be present in the specified directories.
 */

require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');
const fs = require('fs');
const path = require('path');
const csv = require('csv-parser');

// Configure Supabase client
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_KEY environment variables.');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

// Configuration
const DATA_DIR = './data';
const FPL_DIR = path.join(DATA_DIR, 'fpl_data');
const UNDERSTAT_DIR = path.join(DATA_DIR, 'understat_data_2016');
const BATCH_SIZE = 100; // Number of records to insert at once

// Helper function to read CSV files
async function readCSV(filePath) {
  return new Promise((resolve, reject) => {
    const results = [];
    fs.createReadStream(filePath)
      .pipe(csv())
      .on('data', (data) => results.push(data))
      .on('end', () => resolve(results))
      .on('error', (error) => reject(error));
  });
}

// Helper function to batch insert data
async function batchInsert(tableName, data, batchSize = BATCH_SIZE) {
  if (!data || data.length === 0) {
    console.log(`No data to insert into ${tableName}`);
    return;
  }

  console.log(`Inserting ${data.length} records into ${tableName} in batches of ${batchSize}...`);
  
  const batches = [];
  for (let i = 0; i < data.length; i += batchSize) {
    batches.push(data.slice(i, i + batchSize));
  }
  
  let insertedCount = 0;
  for (const [index, batch] of batches.entries()) {
    try {
      const { error } = await supabase.from(tableName).insert(batch);
      
      if (error) {
        console.error(`Error inserting batch ${index + 1}/${batches.length} into ${tableName}:`, error);
      } else {
        insertedCount += batch.length;
        console.log(`Inserted batch ${index + 1}/${batches.length} into ${tableName} (${insertedCount}/${data.length})`);
      }
      
      // Add a small delay to avoid rate limiting
      if (batches.length > 1) {
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    } catch (e) {
      console.error(`Exception inserting batch ${index + 1}/${batches.length} into ${tableName}:`, e);
    }
  }
  
  console.log(`Completed inserting data into ${tableName}`);
}

// Import teams
async function importTeams() {
  try {
    console.log('Importing teams...');
    const teamsFile = path.join(FPL_DIR, 'teams.csv');
    
    if (!fs.existsSync(teamsFile)) {
      console.error(`Teams file not found at ${teamsFile}`);
      return;
    }
    
    const teams = await readCSV(teamsFile);
    
    const formattedTeams = teams.map(team => ({
      id: parseInt(team.id),
      name: team.name,
      short_name: team.short_name,
      code: parseInt(team.code || 0),
      logo: `https://resources.premierleague.com/premierleague/badges/t${team.code || 0}.png`
    }));
    
    await batchInsert('teams', formattedTeams);
  } catch (error) {
    console.error('Error importing teams:', error);
  }
}

// Import positions
async function importPositions() {
  try {
    console.log('Importing positions...');
    const positionsFile = path.join(FPL_DIR, 'positions.csv');
    
    if (!fs.existsSync(positionsFile)) {
      console.error(`Positions file not found at ${positionsFile}`);
      // Use hardcoded positions as fallback
      const positions = [
        { id: 1, singular_name: 'Goalkeeper', plural_name: 'Goalkeepers', short_name: 'GKP' },
        { id: 2, singular_name: 'Defender', plural_name: 'Defenders', short_name: 'DEF' },
        { id: 3, singular_name: 'Midfielder', plural_name: 'Midfielders', short_name: 'MID' },
        { id: 4, singular_name: 'Forward', plural_name: 'Forwards', short_name: 'FWD' }
      ];
      
      await batchInsert('positions', positions);
      return;
    }
    
    const positions = await readCSV(positionsFile);
    await batchInsert('positions', positions);
  } catch (error) {
    console.error('Error importing positions:', error);
  }
}

// Import players
async function importPlayers() {
  try {
    console.log('Importing players...');
    const playersFile = path.join(FPL_DIR, 'players.csv');
    
    if (!fs.existsSync(playersFile)) {
      console.error(`Players file not found at ${playersFile}`);
      return;
    }
    
    const players = await readCSV(playersFile);
    
    const formattedPlayers = players.map(player => ({
      id: parseInt(player.id),
      code: parseInt(player.code || 0),
      first_name: player.first_name,
      last_name: player.last_name,
      web_name: player.web_name,
      team_id: parseInt(player.team_id),
      position_id: parseInt(player.position_id),
      photo: player.photo || `https://resources.premierleague.com/premierleague/photos/players/110x140/p${player.code || 0}.png`
    }));
    
    await batchInsert('players', formattedPlayers);
  } catch (error) {
    console.error('Error importing players:', error);
  }
}

// Import gameweeks
async function importGameweeks() {
  try {
    console.log('Importing gameweeks...');
    const gameweeksFile = path.join(FPL_DIR, 'gameweeks.csv');
    
    if (!fs.existsSync(gameweeksFile)) {
      console.error(`Gameweeks file not found at ${gameweeksFile}`);
      // Create basic gameweeks as fallback
      const gameweeks = [];
      for (let i = 1; i <= 38; i++) {
        gameweeks.push({
          id: i,
          name: `Gameweek ${i}`,
          finished: true,
          data_checked: true
        });
      }
      
      await batchInsert('gameweeks', gameweeks);
      return;
    }
    
    const gameweeks = await readCSV(gameweeksFile);
    
    const formattedGameweeks = gameweeks.map(gw => {
      let chipPlays = null;
      try {
        if (gw.chip_plays && gw.chip_plays !== 'null') {
          chipPlays = JSON.parse(gw.chip_plays.replace(/'/g, '"'));
        }
      } catch (e) {
        console.warn(`Could not parse chip_plays for gameweek ${gw.id}: ${e.message}`);
      }
      
      return {
        id: parseInt(gw.id),
        name: gw.name || `Gameweek ${gw.id}`,
        deadline_time: gw.deadline_time,
        is_current: gw.is_current === 'True',
        is_next: gw.is_next === 'True',
        is_previous: gw.is_previous === 'True',
        finished: gw.finished === 'True',
        data_checked: gw.data_checked === 'True',
        highest_score: parseInt(gw.highest_score || 0),
        average_score: parseInt(gw.average_score || 0),
        chip_plays: chipPlays
      };
    });
    
    await batchInsert('gameweeks', formattedGameweeks);
  } catch (error) {
    console.error('Error importing gameweeks:', error);
  }
}

// Import fixtures
async function importFixtures() {
  try {
    console.log('Importing fixtures...');
    const fixturesFile = path.join(FPL_DIR, 'fixtures.csv');
    
    if (!fs.existsSync(fixturesFile)) {
      console.error(`Fixtures file not found at ${fixturesFile}`);
      return;
    }
    
    const fixtures = await readCSV(fixturesFile);
    
    const formattedFixtures = fixtures.map(fixture => ({
      id: parseInt(fixture.id),
      gameweek_id: parseInt(fixture.gameweek_id),
      home_team_id: parseInt(fixture.home_team_id),
      away_team_id: parseInt(fixture.away_team_id),
      kickoff_time: fixture.kickoff_time,
      home_team_score: parseInt(fixture.home_team_score || 0),
      away_team_score: parseInt(fixture.away_team_score || 0),
      finished: fixture.finished === 'True',
      minutes: parseInt(fixture.minutes || 0),
      provisional_start_time: fixture.provisional_start_time === 'True',
      team_h_difficulty: parseInt(fixture.team_h_difficulty || 3),
      team_a_difficulty: parseInt(fixture.team_a_difficulty || 3)
    }));
    
    await batchInsert('fixtures', formattedFixtures);
  } catch (error) {
    console.error('Error importing fixtures:', error);
  }
}

// Import player gameweek stats
async function importPlayerGameweekStats() {
  try {
    console.log('Importing player gameweek stats...');
    const playerStatsFile = path.join(FPL_DIR, 'player_gameweek_stats.csv');
    
    if (!fs.existsSync(playerStatsFile)) {
      console.error(`Player gameweek stats file not found at ${playerStatsFile}`);
      return;
    }
    
    const playerStats = await readCSV(playerStatsFile);
    
    const formattedStats = playerStats.map(stat => ({
      player_id: parseInt(stat.player_id),
      gameweek_id: parseInt(stat.gameweek_id),
      fixture_id: parseInt(stat.fixture_id),
      minutes: parseInt(stat.minutes || 0),
      goals_scored: parseInt(stat.goals_scored || 0),
      assists: parseInt(stat.assists || 0),
      clean_sheets: parseInt(stat.clean_sheets || 0),
      goals_conceded: parseInt(stat.goals_conceded || 0),
      own_goals: parseInt(stat.own_goals || 0),
      penalties_saved: parseInt(stat.penalties_saved || 0),
      penalties_missed: parseInt(stat.penalties_missed || 0),
      yellow_cards: parseInt(stat.yellow_cards || 0),
      red_cards: parseInt(stat.red_cards || 0),
      saves: parseInt(stat.saves || 0),
      bonus: parseInt(stat.bonus || 0),
      bps: parseInt(stat.bps || 0),
      influence: parseFloat(stat.influence || 0),
      creativity: parseFloat(stat.creativity || 0),
      threat: parseFloat(stat.threat || 0),
      ict_index: parseFloat(stat.ict_index || 0),
      total_points: parseInt(stat.total_points || 0)
    }));
    
    await batchInsert('player_gameweek_stats', formattedStats);
  } catch (error) {
    console.error('Error importing player gameweek stats:', error);
  }
}

// Import player price history
async function importPlayerPrices() {
  try {
    console.log('Importing player price history...');
    const priceHistoryFile = path.join(FPL_DIR, 'player_price_history.csv');
    
    if (!fs.existsSync(priceHistoryFile)) {
      console.error(`Player price history file not found at ${priceHistoryFile}`);
      return;
    }
    
    const priceData = await readCSV(priceHistoryFile);
    
    const formattedPrices = priceData.map(price => ({
      player_id: parseInt(price.player_id),
      gameweek_id: parseInt(price.gameweek_id),
      price: parseInt(price.price)
    }));
    
    await batchInsert('player_price_history', formattedPrices);
  } catch (error) {
    console.error('Error importing player price history:', error);
  }
}

// Import player season stats
async function importPlayerSeasonStats() {
  try {
    console.log('Importing player season stats...');
    const seasonStatsFile = path.join(FPL_DIR, 'player_season_stats.csv');
    
    if (!fs.existsSync(seasonStatsFile)) {
      console.error(`Player season stats file not found at ${seasonStatsFile}`);
      return;
    }
    
    const seasonStats = await readCSV(seasonStatsFile);
    
    const formattedStats = seasonStats.map(stat => ({
      player_id: parseInt(stat.player_id),
      points_per_game: parseFloat(stat.points_per_game || 0),
      minutes: parseInt(stat.minutes || 0),
      goals_scored: parseInt(stat.goals_scored || 0),
      assists: parseInt(stat.assists || 0),
      clean_sheets: parseInt(stat.clean_sheets || 0),
      goals_conceded: parseInt(stat.goals_conceded || 0),
      own_goals: parseInt(stat.own_goals || 0),
      penalties_saved: parseInt(stat.penalties_saved || 0),
      penalties_missed: parseInt(stat.penalties_missed || 0),
      yellow_cards: parseInt(stat.yellow_cards || 0),
      red_cards: parseInt(stat.red_cards || 0),
      saves: parseInt(stat.saves || 0),
      bonus: parseInt(stat.bonus || 0),
      bps: parseInt(stat.bps || 0),
      form: parseFloat(stat.form || 0),
      selected_by_percent: parseFloat(stat.selected_by_percent || 0)
    }));
    
    await batchInsert('player_season_stats', formattedStats);
  } catch (error) {
    console.error('Error importing player season stats:', error);
  }
}

// Import xG data from Understat
async function importUnderstatData() {
  try {
    console.log('Importing xG data from Understat...');
    
    const xgImportFile = path.join(UNDERSTAT_DIR, 'fpl_xg_import.csv');
    if (!fs.existsSync(xgImportFile)) {
      console.log('Understat xG import file not found. Skipping xG import.');
      return;
    }
    
    const xgData = await readCSV(xgImportFile);
    
    // First, get all FPL players
    const { data: fplPlayers, error } = await supabase
      .from('players')
      .select('id, web_name, team_id');
      
    if (error) {
      console.error('Error fetching FPL players:', error);
      return;
    }
    
    // Get all teams for mapping
    const { data: teams, error: teamsError } = await supabase
      .from('teams')
      .select('id, name, short_name');
      
    if (teamsError) {
      console.error('Error fetching teams:', teamsError);
      return;
    }
    
    // Create a team name mapping (Understat team name to FPL team ID)
    const teamMapping = {
      'Arsenal': teams.find(t => t.name === 'Arsenal')?.id,
      'Bournemouth': teams.find(t => t.name === 'Bournemouth')?.id,
      'Burnley': teams.find(t => t.name === 'Burnley')?.id,
      'Chelsea': teams.find(t => t.name === 'Chelsea')?.id,
      'Crystal Palace': teams.find(t => t.name === 'Crystal Palace')?.id,
      'Everton': teams.find(t => t.name === 'Everton')?.id,
      'Hull': teams.find(t => t.name === 'Hull City')?.id,
      'Leicester': teams.find(t => t.name === 'Leicester City')?.id,
      'Liverpool': teams.find(t => t.name === 'Liverpool')?.id,
      'Man City': teams.find(t => t.name === 'Manchester City')?.id,
      'Man Utd': teams.find(t => t.name === 'Manchester United')?.id,
      'Middlesbrough': teams.find(t => t.name === 'Middlesbrough')?.id,
      'Southampton': teams.find(t => t.name === 'Southampton')?.id,
      'Stoke': teams.find(t => t.name === 'Stoke City')?.id,
      'Sunderland': teams.find(t => t.name === 'Sunderland')?.id,
      'Swansea': teams.find(t => t.name === 'Swansea City')?.id,
      'Tottenham': teams.find(t => t.name === 'Tottenham Hotspur')?.id,
      'Watford': teams.find(t => t.name === 'Watford')?.id,
      'West Brom': teams.find(t => t.name === 'West Bromwich Albion')?.id,
      'West Ham': teams.find(t => t.name === 'West Ham United')?.id
    };
    
    // Function to find FPL player ID based on name and team
    function findFplPlayerId(understatName, understatTeam) {
      // Clean and normalize player name for matching
      const normalizeName = (name) => name.toLowerCase().replace(/[^a-z]/g, '');
      const normalizedUnderstatName = normalizeName(understatName);
      
      // Get FPL team ID from understat team name
      const fplTeamId = teamMapping[understatTeam];
      
      if (!fplTeamId) {
        console.log(`Could not map Understat team: ${understatTeam}`);
        return null;
      }
      
      // Find players on the same team first
      const teamPlayers = fplPlayers.filter(p => p.team_id === fplTeamId);
      
      // Try direct name matching first
      for (const player of teamPlayers) {
        const normalizedFplName = normalizeName(player.web_name);
        
        // Check if one name contains the other
        if (normalizedFplName.includes(normalizedUnderstatName) || 
            normalizedUnderstatName.includes(normalizedFplName)) {
          return player.id;
        }
      }
      
      // If no match found, try fuzzy matching using string similarity
      let bestMatchId = null;
      let bestMatchScore = 0;
      
      for (const player of teamPlayers) {
        const normalizedFplName = normalizeName(player.web_name);
        
        // Simple similarity score: count of common characters
        let matchScore = 0;
        for (const char of normalizedUnderstatName) {
          if (normalizedFplName.includes(char)) {
            matchScore++;
          }
        }
        
        // Normalize by length of longer name
        const normalizedScore = matchScore / Math.max(normalizedFplName.length, normalizedUnderstatName.length);
        
        if (normalizedScore > bestMatchScore && normalizedScore > 0.5) {  // Threshold
          bestMatchScore = normalizedScore;
          bestMatchId = player.id;
        }
      }
      
      return bestMatchId;
    }
    
    // Process xG data
    console.log('Mapping Understat players to FPL players and updating xG data...');
    
    const updates = [];
    for (const playerData of xgData) {
      const fplPlayerId = findFplPlayerId(playerData.player_name, playerData.team);
      
      if (fplPlayerId) {
        updates.push({
          player_id: fplPlayerId,
          gameweek_id: parseInt(playerData.gameweek),
          xg: parseFloat(playerData.xg || 0),
          xa: parseFloat(playerData.xa || 0)
        });
      }
    }
    
    console.log(`Found ${updates.length} player-gameweek xG/xA mappings`);
    
    // Update player_gameweek_stats with xG data
    if (updates.length > 0) {
      for (const update of updates) {
        try {
          const { data, error } = await supabase
            .from('player_gameweek_stats')
            .update({ 
              xg: update.xg, 
              xa: update.xa 
            })
            .match({ 
              player_id: update.player_id, 
              gameweek_id: update.gameweek_id 
            });
          
          if (error) {
            console.error(`Error updating xG data for player ${update.player_id}, gameweek ${update.gameweek_id}:`, error);
          }
        } catch (e) {
          console.error(`Exception updating xG data:`, e);
        }
        
        // Add a small delay to avoid rate limiting
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      console.log(`Updated ${updates.length} player-gameweek records with xG/xA data`);
    }
  } catch (error) {
    console.error('Error importing Understat data:', error);
  }
}

// Import simulated news data
async function importSimulatedNewsData() {
  try {
    console.log('Importing simulated news data...');
    
    // Team news examples
    const teamNews = [
      {
        team_id: 1, // Arsenal
        gameweek_id: 1,
        news_type: 'pre_match',
        headline: 'Arsenal ready for season opener against Liverpool',
        content: 'Arsene Wenger confirms the team is ready for the first match of the season against Liverpool.',
        source: 'BBC Sport',
        published_date: '2016-08-12T10:00:00Z'
      },
      {
        team_id: 9, // Liverpool
        gameweek_id: 1,
        news_type: 'pre_match',
        headline: 'Klopp excited for opening fixture',
        content: 'Jurgen Klopp says his Liverpool side is ready for a challenging start against Arsenal.',
        source: 'Liverpool FC',
        published_date: '2016-08-12T12:30:00Z'
      },
      {
        team_id: 4, // Chelsea
        gameweek_id: 3,
        news_type: 'manager_change',
        headline: 'Conte implementing new formation',
        content: 'Antonio Conte is considering switching to a 3-4-3 formation following mixed start to the season.',
        source: 'Sky Sports',
        published_date: '2016-08-26T09:15:00Z'
      }
    ];
    
    // Player news examples (update player IDs to match your data)
    const { data: players } = await supabase
      .from('players')
      .select('id, web_name, team_id')
      .limit(10);
      
    const playerNews = [
      {
        player_id: players[0]?.id || 1,
        gameweek_id: 2,
        news_type: 'injury',
        headline: 'Out for 2 weeks with hamstring injury',
        content: 'Expected to return in Gameweek 4',
        chance_of_playing_next_round: 0,
        chance_of_playing_this_round: 0,
        expected_return_date: 'GW4',
        source: 'Premier League Injury News',
        published_date: '2016-08-19T15:30:00Z'
      },
      {
        player_id: players[1]?.id || 200,
        gameweek_id: 5,
        news_type: 'suspension',
        headline: 'Suspended for one match',
        content: 'Will miss the next game due to accumulation of yellow cards',
        chance_of_playing_next_round: 0,
        chance_of_playing_this_round: 100,
        expected_return_date: 'GW6',
        source: 'FA Disciplinary',
        published_date: '2016-09-18T18:00:00Z'
      }
    ];
    
    // FPL events examples
    const fplEvents = [
      {
        gameweek_id: 20,
        event_type: 'double_gameweek',
        announcement_gameweek_id: 18,
        headline: 'Double Gameweek 20 announced',
        content: 'Four teams will play twice in Gameweek 20 due to fixture rescheduling',
        teams_affected: [1, 4, 9, 10] // Arsenal, Chelsea, Liverpool, Man City
      },
      {
        gameweek_id: 28,
        event_type: 'blank_gameweek',
        announcement_gameweek_id: 26,
        headline: 'Blank Gameweek 28 announced',
        content: 'Four matches postponed due to FA Cup quarter-finals',
        teams_affected: [1, 4, 9, 10, 11, 17] // Multiple teams affected
      }
    ];
    
    // Insert the data
    await batchInsert('team_news', teamNews);
    await batchInsert('player_news', playerNews);
    await batchInsert('fpl_events', fplEvents);
    
    console.log('Imported simulated news data');
  } catch (error) {
    console.error('Error importing news data:', error);
  }
}

// Import simulated predicted lineups
async function importSimulatedLineups() {
  try {
    console.log('Importing simulated predicted lineups...');
    
    // Get some real player IDs for Arsenal
    const { data: arsenalPlayers, error: arsenalError } = await supabase
      .from('players')
      .select('id, web_name, position_id')
      .eq('team_id', 1); // Arsenal
      
    if (arsenalError) {
      console.error('Error fetching Arsenal players:', arsenalError);
      return;
    }
    
    // Get some real player IDs for Chelsea
    const { data: chelseaPlayers, error: chelseaError } = await supabase
      .from('players')
      .select('id, web_name, position_id')
      .eq('team_id', 4); // Chelsea
      
    if (chelseaError) {
      console.error('Error fetching Chelsea players:', chelseaError);
      return;
    }
    
    // Create sample predicted lineups
    const predictedLineups = [];
    
    // Only proceed if we have enough players
    if (arsenalPlayers?.length >= 11 && chelseaPlayers?.length >= 11) {
      // Sort players by position
      const sortedArsenalPlayers = arsenalPlayers.sort((a, b) => a.position_id - b.position_id);
      const sortedChelseaPlayers = chelseaPlayers.sort((a, b) => a.position_id - b.position_id);
      
      // Arsenal lineup for GW1
      predictedLineups.push({
        team_id: 1, // Arsenal
        gameweek_id: 1,
        formation: '4-2-3-1',
        lineup: {
          goalkeeper: [sortedArsenalPlayers.find(p => p.position_id === 1)?.id],
          defenders: sortedArsenalPlayers.filter(p => p.position_id === 2).slice(0, 4).map(p => p.id),
          midfielders: sortedArsenalPlayers.filter(p => p.position_id === 3).slice(0, 5).map(p => p.id),
          forwards: sortedArsenalPlayers.filter(p => p.position_id === 4).slice(0, 1).map(p => p.id)
        },
        source: 'Fantasy Football Scout'
      });
      
      // Chelsea lineup for GW1
      predictedLineups.push({
        team_id: 4, // Chelsea
        gameweek_id: 1,
        formation: '4-3-3',
        lineup: {
          goalkeeper: [sortedChelseaPlayers.find(p => p.position_id === 1)?.id],
          defenders: sortedChelseaPlayers.filter(p => p.position_id === 2).slice(0, 4).map(p => p.id),
          midfielders: sortedChelseaPlayers.filter(p => p.position_id === 3).slice(0, 3).map(p => p.id),
          forwards: sortedChelseaPlayers.filter(p => p.position_id === 4).slice(0, 3).map(p => p.id)
        },
        source: 'Fantasy Football Scout'
      });
    }
    
    // Insert the data
    if (predictedLineups.length > 0) {
      await batchInsert('predicted_lineups', predictedLineups);
      console.log('Imported simulated predicted lineups');
    } else {
      console.log('Could not create predicted lineups due to insufficient player data');
    }
  } catch (error) {
    console.error('Error importing predicted lineups:', error);
  }
}

// Main function to orchestrate the import process
async function main() {
  console.log('Starting FPL 2016/17 season data import...');
  
  // Step 1: Import core data
  await importTeams();
  await importPositions();
  await importPlayers();
  await importGameweeks();
  await importFixtures();
  
  // Step 2: Import player performance data
  await importPlayerGameweekStats();
  await importPlayerPrices();
  await importPlayerSeasonStats();
  
  // Step 3: Import additional data
  await importUnderstatData();
  
  // Step 4: Import simulated news and event data
  await importSimulatedNewsData();
  await importSimulatedLineups();
  
  console.log('FPL 2016/17 season data import completed!');
}

// Run the main function
main().catch(error => {
  console.error('Error in main import process:', error);
  process.exit(1);
});