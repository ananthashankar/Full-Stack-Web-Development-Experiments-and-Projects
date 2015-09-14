-- Table definitions for the tournament project.
--
-- Put your SQL 'create table' statements in this file; also 'create view'
-- statements if you choose to use it.
--
-- You can write comments in this file by starting them with two dashes, like
-- these lines here.
-- Creating new DB with name "tournament"
CREATE DATABASE tournament;

-- Creating new Table with name players and respective required columns
-- with datatypes required
CREATE TABLE players (id SERIAL, name TEXT, matchesPlayed INTEGER, 
	wins INTEGER, loss INTEGER, points INTEGER, byes INTEGER);

-- Creating new Table with name matches and respective required columns
-- with datatypes required
CREATE TABLE matches (id SERIAL, player1 INTEGER, player2 INTEGER,
	 winner INTEGER, loser INTEGER, round INTEGER);