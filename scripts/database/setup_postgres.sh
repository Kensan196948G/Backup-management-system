#!/bin/bash
# ==============================================================================
# PostgreSQL Setup Script for Backup Management System
# Phase 12: Database & Infrastructure Enhancement
#
# This script sets up PostgreSQL database for the backup management system.
# ==============================================================================

set -e

# Configuration
DB_NAME="${DB_NAME:-backup_management}"
DB_USER="${DB_USER:-backupmgmt}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running as root for system operations
check_postgres_installed() {
    if command -v psql &> /dev/null; then
        print_status "PostgreSQL client found"
        return 0
    else
        print_error "PostgreSQL client not found"
        return 1
    fi
}

install_postgres() {
    echo "Installing PostgreSQL..."

    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        sudo apt update
        sudo apt install -y postgresql postgresql-contrib libpq-dev
    elif [ -f /etc/redhat-release ]; then
        # CentOS/RHEL
        sudo yum install -y postgresql-server postgresql-contrib postgresql-devel
        sudo postgresql-setup initdb
    else
        print_error "Unsupported OS. Please install PostgreSQL manually."
        exit 1
    fi

    # Start and enable PostgreSQL
    sudo systemctl start postgresql
    sudo systemctl enable postgresql

    print_status "PostgreSQL installed and started"
}

create_database() {
    echo "Creating database and user..."

    # Generate password if not provided
    if [ -z "$DB_PASSWORD" ]; then
        DB_PASSWORD=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 24)
        print_warning "Generated password: $DB_PASSWORD"
        print_warning "Please save this password securely!"
    fi

    # Create user and database
    sudo -u postgres psql <<EOF
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
        CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};

-- Enable extensions
\c ${DB_NAME}
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
EOF

    print_status "Database '${DB_NAME}' created with user '${DB_USER}'"
}

configure_connection() {
    echo "Configuring PostgreSQL connection..."

    # Find pg_hba.conf location
    PG_HBA=$(sudo -u postgres psql -t -P format=unaligned -c "SHOW hba_file")

    # Backup original
    sudo cp "$PG_HBA" "${PG_HBA}.backup"

    # Add local connection rule (if not exists)
    if ! grep -q "${DB_USER}" "$PG_HBA"; then
        echo "# Backup Management System" | sudo tee -a "$PG_HBA"
        echo "local   ${DB_NAME}    ${DB_USER}                              md5" | sudo tee -a "$PG_HBA"
        echo "host    ${DB_NAME}    ${DB_USER}    127.0.0.1/32            md5" | sudo tee -a "$PG_HBA"
        echo "host    ${DB_NAME}    ${DB_USER}    ::1/128                 md5" | sudo tee -a "$PG_HBA"
    fi

    # Reload PostgreSQL
    sudo systemctl reload postgresql

    print_status "Connection configured"
}

test_connection() {
    echo "Testing database connection..."

    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        print_status "Database connection successful"
    else
        print_error "Database connection failed"
        exit 1
    fi
}

generate_env_config() {
    echo "Generating environment configuration..."

    ENV_FILE=".env.postgres"

    cat > "$ENV_FILE" <<EOF
# PostgreSQL Configuration for Backup Management System
# Generated: $(date)

# Database URL
DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}

# Individual components
POSTGRES_HOST=${DB_HOST}
POSTGRES_PORT=${DB_PORT}
POSTGRES_DB=${DB_NAME}
POSTGRES_USER=${DB_USER}
POSTGRES_PASSWORD=${DB_PASSWORD}

# SQLAlchemy configuration
SQLALCHEMY_DATABASE_URI=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}
EOF

    chmod 600 "$ENV_FILE"
    print_status "Environment config saved to $ENV_FILE"
}

print_summary() {
    echo ""
    echo "=============================================="
    echo "PostgreSQL Setup Complete"
    echo "=============================================="
    echo ""
    echo "Database: ${DB_NAME}"
    echo "User:     ${DB_USER}"
    echo "Host:     ${DB_HOST}:${DB_PORT}"
    echo ""
    echo "Connection URL:"
    echo "  postgresql://${DB_USER}:****@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    echo ""
    echo "Next steps:"
    echo "  1. Update your .env file with the DATABASE_URL from .env.postgres"
    echo "  2. Run migration: python scripts/database/migrate_sqlite_to_postgres.py"
    echo "  3. Update app/config.py to use PostgreSQL"
    echo ""
    echo "=============================================="
}

# Main execution
main() {
    echo "=============================================="
    echo "PostgreSQL Setup for Backup Management System"
    echo "=============================================="
    echo ""

    # Check if PostgreSQL is installed
    if ! check_postgres_installed; then
        read -p "Install PostgreSQL? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_postgres
        else
            print_error "PostgreSQL is required. Please install it manually."
            exit 1
        fi
    fi

    # Create database
    create_database

    # Configure connection
    configure_connection

    # Test connection
    test_connection

    # Generate env config
    generate_env_config

    # Print summary
    print_summary
}

# Parse arguments
case "${1:-setup}" in
    setup)
        main
        ;;
    create-db)
        create_database
        ;;
    test)
        test_connection
        ;;
    *)
        echo "Usage: $0 {setup|create-db|test}"
        echo ""
        echo "Commands:"
        echo "  setup     - Full setup (install, create db, configure)"
        echo "  create-db - Create database only"
        echo "  test      - Test database connection"
        echo ""
        echo "Environment variables:"
        echo "  DB_NAME     - Database name (default: backup_management)"
        echo "  DB_USER     - Database user (default: backupmgmt)"
        echo "  DB_PASSWORD - Database password (auto-generated if empty)"
        echo "  DB_HOST     - Database host (default: localhost)"
        echo "  DB_PORT     - Database port (default: 5432)"
        exit 1
        ;;
esac
