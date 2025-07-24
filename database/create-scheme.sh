#!/bin/bash

# Create Database Schema Script
# This script creates the PostgreSQL schema file for the baseball simulation system

echo "📊 Creating PostgreSQL schema file..."

# Create directory if it doesn't exist
mkdir -p database/init

# Create the schema file
cat > database/init/01-schema.sql << 'EOF'
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS raw_data;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS simulations;

-- Teams table
CREATE TABLE IF NOT EXISTS teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    abbreviation VARCHAR(5) NOT NULL,
    league VARCHAR(10),
    division VARCHAR(20),
    stadium_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Stadiums table with park factors
CREATE TABLE IF NOT EXISTS stadiums (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stadium_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    location VARCHAR(200),
    capacity INTEGER,
    dimensions JSONB, -- left field, center field, right field distances
    park_factors JSONB, -- batting average, home runs, etc.
    altitude INTEGER,
    surface VARCHAR(50),
    roof_type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Players table
CREATE TABLE IF NOT EXISTS players (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    player_id VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    birth_date DATE,
    position VARCHAR(10),
    bats VARCHAR(10),
    throws VARCHAR(10),
    team_id UUID REFERENCES teams(id),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Umpires table
CREATE TABLE IF NOT EXISTS umpires (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    umpire_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    tendencies JSONB, -- strike zone tendencies, K%, BB%, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Games table
CREATE TABLE IF NOT EXISTS games (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    game_id VARCHAR(50) UNIQUE NOT NULL,
    game_date DATE NOT NULL,
    game_time TIME,
    home_team_id UUID REFERENCES teams(id),
    away_team_id UUID REFERENCES
