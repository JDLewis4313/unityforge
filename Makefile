.PHONY: help build up down restart logs shell db-upgrade db-migrate clean ssl-certs

# Default target
help:
	@echo "UnityForge Development Commands:"
	@echo ""
	@echo "  make setup      - Initial setup (SSL certs + build + start)"
	@echo "  make ssl-certs  - Generate SSL certificates for HTTPS"
	@echo "  make build      - Build Docker containers"
	@echo "  make up         - Start all services"
	@echo "  make down       - Stop all services"
	@echo "  make restart    - Restart all services"
	@echo "  make logs       - View logs from all services"
	@echo "  make logs-flask - View logs from Flask service only"
	@echo "  make logs-nginx - View logs from nginx service only"
	@echo "  make shell      - Open shell in Flask container"
	@echo "  make db-upgrade - Run database migrations"
	@echo "  make db-migrate - Create new database migration"
	@echo "  make clean      - Remove containers, volumes, and images"
	@echo "  make status     - Show service status"
	@echo ""
	@echo "URLs:"
	@echo "  - Application: https://localhost"
	@echo "  - HTTP Redirect: http://localhost"

# Initial setup for new developers
setup: ssl-certs build up
	@echo "Setup complete! Your app is running at https://localhost"

# Generate SSL certificates
ssl-certs:
	@chmod +x generate-ssl-certs.sh
	@./generate-ssl-certs.sh

# Build containers
build:
	docker-compose build

# Start services
up:
	docker-compose up -d
	@echo "Services started. Access your app at https://localhost"
	@echo "Run 'make logs' to see the logs"

# Stop services
down:
	docker-compose down

# Restart services
restart: down up

# View all logs
logs:
	docker-compose logs -f

# View Flask logs only
logs-flask:
	docker-compose logs -f flask

# View nginx logs only
logs-nginx:
	docker-compose logs -f nginx

# Open shell in Flask container
shell:
	docker-compose exec flask bash

# Run database migrations
db-upgrade:
	docker-compose exec flask flask db upgrade

# Create new migration
db-migrate:
	@read -p "Migration message: " msg; \
	docker-compose exec flask flask db migrate -m "$$msg"

# Show service status
status:
	docker-compose ps

# Clean up everything
clean:
	docker-compose down -v --rmi all --remove-orphans
	docker system prune -f

# Development helpers
dev-setup:
	@echo "Setting up development environment..."
	@if [ ! -f ".env" ]; then echo "Please create .env file first!"; exit 1; fi
	@make ssl-certs
	@make build
	@make up
	@echo "Development environment ready!"

# Production build (for future use)
prod-build:
	docker-compose -f docker-compose.prod.yml build

# Backup database
backup-db:
	@mkdir -p backups
	@docker-compose exec flask cp app.db /tmp/backup.db
	@docker cp $$(docker-compose ps -q flask):/tmp/backup.db backups/app_$(shell date +%Y%m%d_%H%M%S).db
	@echo "Database backed up to backups/"

# Restore database (use with caution)
restore-db:
	@echo "Available backups:"
	@ls -la backups/
	@read -p "Enter backup filename: " backup; \
	docker cp backups/$$backup $$(docker-compose ps -q flask):/tmp/restore.db && \
	docker-compose exec flask cp /tmp/restore.db app.db
	@echo "Database restored. Restart services with 'make restart'"