-- Migration: Add AI structured prediction fields
-- Apply to both market_odds (championship) and daily_matches (daily) tables

-- market_odds table
ALTER TABLE market_odds ADD COLUMN IF NOT EXISTS ai_prediction TEXT;
ALTER TABLE market_odds ADD COLUMN IF NOT EXISTS ai_probability INTEGER;
ALTER TABLE market_odds ADD COLUMN IF NOT EXISTS ai_market TEXT;
ALTER TABLE market_odds ADD COLUMN IF NOT EXISTS ai_risk VARCHAR(10);
ALTER TABLE market_odds ADD COLUMN IF NOT EXISTS ai_generated_at TIMESTAMP(6);

-- daily_matches table
ALTER TABLE daily_matches ADD COLUMN IF NOT EXISTS ai_prediction TEXT;
ALTER TABLE daily_matches ADD COLUMN IF NOT EXISTS ai_probability INTEGER;
ALTER TABLE daily_matches ADD COLUMN IF NOT EXISTS ai_market TEXT;
ALTER TABLE daily_matches ADD COLUMN IF NOT EXISTS ai_risk VARCHAR(10);
ALTER TABLE daily_matches ADD COLUMN IF NOT EXISTS ai_generated_at TIMESTAMP(6);
