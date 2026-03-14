"""
NyayaSetu V2 Table Setup Script

This script creates the V2 tables in Supabase using direct PostgreSQL connection.

Usage:
    py setup_v2_tables.py <database_password>

You can find your database password in Supabase Dashboard:
    Settings -> Database -> Connection string -> Password

Or use the connection string from:
    Settings -> Database -> Connection string (URI)
"""

import sys
import os

# V2 SQL to create all new tables
V2_SQL = """
-- V2 EXPANSION: New tables and columns

ALTER TABLE grievances ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE grievances ADD COLUMN IF NOT EXISTS image_verified BOOLEAN DEFAULT NULL;

CREATE TABLE IF NOT EXISTS railway_clusters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category TEXT, train_number TEXT, railway_zone TEXT, station TEXT,
    member_ids TEXT[], summary TEXT, ai_brief TEXT,
    count INTEGER DEFAULT 0, alert_sent BOOLEAN DEFAULT FALSE,
    next_station TEXT, created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS railway_grievances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    passenger_name TEXT NOT NULL, phone TEXT, train_number TEXT NOT NULL,
    railway_zone TEXT NOT NULL, station TEXT, coach_number TEXT,
    description TEXT NOT NULL, category TEXT, urgency INTEGER,
    credibility_score INTEGER, ai_summary TEXT, status TEXT DEFAULT 'open',
    hash TEXT, cluster_id UUID REFERENCES railway_clusters(id),
    image_url TEXT, image_verified BOOLEAN DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(), resolved_at TIMESTAMPTZ,
    resolution_confirmed BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS railway_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    grievance_id UUID REFERENCES railway_grievances(id),
    action_type TEXT, performed_by TEXT DEFAULT 'system',
    notes TEXT, hash TEXT, created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS budget_allocations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    grievance_id UUID REFERENCES grievances(id),
    cluster_id UUID REFERENCES clusters(id),
    department TEXT NOT NULL, amount_allocated NUMERIC(12,2) DEFAULT 0,
    amount_spent NUMERIC(12,2) DEFAULT 0, description TEXT,
    auditor_flagged BOOLEAN DEFAULT FALSE, flag_reason TEXT,
    flagged_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ward TEXT NOT NULL, category TEXT NOT NULL, month TEXT NOT NULL,
    predicted_count INTEGER, confidence FLOAT, trend TEXT,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- V2 Indexes
CREATE INDEX IF NOT EXISTS idx_railway_grievances_status ON railway_grievances(status);
CREATE INDEX IF NOT EXISTS idx_railway_grievances_train ON railway_grievances(train_number);
CREATE INDEX IF NOT EXISTS idx_railway_grievances_zone ON railway_grievances(railway_zone);
CREATE INDEX IF NOT EXISTS idx_railway_grievances_cluster ON railway_grievances(cluster_id);
CREATE INDEX IF NOT EXISTS idx_railway_actions_grievance ON railway_actions(grievance_id);
CREATE INDEX IF NOT EXISTS idx_budget_grievance ON budget_allocations(grievance_id);
CREATE INDEX IF NOT EXISTS idx_budget_cluster ON budget_allocations(cluster_id);
CREATE INDEX IF NOT EXISTS idx_budget_flagged ON budget_allocations(auditor_flagged);
CREATE INDEX IF NOT EXISTS idx_predictions_ward ON predictions(ward);
CREATE INDEX IF NOT EXISTS idx_predictions_month ON predictions(month);

-- V2 RLS
ALTER TABLE railway_grievances ENABLE ROW LEVEL SECURITY;
ALTER TABLE railway_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE railway_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE budget_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    CREATE POLICY "Allow all on railway_grievances" ON railway_grievances FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Allow all on railway_clusters" ON railway_clusters FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Allow all on railway_actions" ON railway_actions FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Allow all on budget_allocations" ON budget_allocations FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE POLICY "Allow all on predictions" ON predictions FOR ALL USING (true) WITH CHECK (true);
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
"""


def setup_with_password(password: str):
    """Create V2 tables using direct PostgreSQL connection."""
    try:
        import psycopg2
    except ImportError:
        print("Installing psycopg2-binary...")
        os.system(f"{sys.executable} -m pip install psycopg2-binary")
        import psycopg2

    project_ref = "evobwnzwqfrotsttkgok"

    # Try multiple connection endpoints
    endpoints = [
        {"host": f"db.{project_ref}.supabase.co", "port": 5432},
        {"host": "aws-0-ap-south-1.pooler.supabase.com", "port": 5432},
        {"host": "aws-0-ap-south-1.pooler.supabase.com", "port": 6543},
    ]

    conn = None
    for ep in endpoints:
        try:
            print(f"Trying {ep['host']}:{ep['port']}...")
            conn = psycopg2.connect(
                host=ep["host"],
                port=ep["port"],
                dbname="postgres",
                user=f"postgres.{project_ref}" if "pooler" in ep["host"] else "postgres",
                password=password,
                connect_timeout=10,
            )
            print(f"Connected via {ep['host']}:{ep['port']}!")
            break
        except Exception as e:
            print(f"  Failed: {str(e)[:80]}")
            continue

    if not conn:
        print("\nCould not connect to database. Please check your password.")
        print("Find it at: Supabase Dashboard -> Settings -> Database -> Connection string")
        return False

    try:
        conn.autocommit = True
        cur = conn.cursor()
        print("\nRunning V2 schema SQL...")
        cur.execute(V2_SQL)
        print("V2 tables created successfully!")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"SQL execution failed: {e}")
        conn.close()
        return False


def setup_with_connection_string(conn_string: str):
    """Create V2 tables using a full connection string."""
    try:
        import psycopg2
    except ImportError:
        os.system(f"{sys.executable} -m pip install psycopg2-binary")
        import psycopg2

    try:
        print("Connecting...")
        conn = psycopg2.connect(conn_string, connect_timeout=10)
        conn.autocommit = True
        cur = conn.cursor()
        print("Running V2 schema SQL...")
        cur.execute(V2_SQL)
        print("V2 tables created successfully!")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    arg = sys.argv[1]
    if arg.startswith("postgresql://") or arg.startswith("postgres://"):
        success = setup_with_connection_string(arg)
    else:
        success = setup_with_password(arg)

    sys.exit(0 if success else 1)
