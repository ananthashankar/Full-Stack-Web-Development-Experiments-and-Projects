-- Table definitions for the tournament project.
--
-- Put your SQL 'create table' statements in this file; also 'create view'
-- statements if you choose to use it.
--
-- You can write comments in this file by starting them with two dashes, like
-- these lines here.
-- Deleting existing and Creating new DB with name "tournament"
DROP DATABASE IF EXISTS tournament;
CREATE DATABASE tournament;
\c tournament
-- Creating new Table with name players and respective required columns
-- with datatypes required
CREATE TABLE players (id SERIAL PRIMARY KEY, name TEXT, matchesPlayed INTEGER, 
	wins INTEGER, loss INTEGER, points INTEGER, byes INTEGER);

-- Creating new Table with name matches and respective required columns
-- with datatypes required
CREATE TABLE matches (id SERIAL PRIMARY KEY, player1 INTEGER REFERENCES players, 
	player2 INTEGER REFERENCES players, winner INTEGER, loser INTEGER, round INTEGER);