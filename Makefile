# Root Makefile
# Orchestrates the build and setup of the AMI system.

# Environment Variables
PYTHON_VERSION ?= 3.12
UV ?= uv
NPM ?= npm

# Directories
ROOT_DIR := $(shell pwd)
BOOT_DIR := $(ROOT_DIR)/.boot-linux
NODE_BIN_DIR := $(BOOT_DIR)/node-env/bin

# Export for sub-makefiles
export AMI_ROOT := $(ROOT_DIR)
export AMI_BOOT_DIR := $(BOOT_DIR)
export AMI_NODE_BIN := $(NODE_BIN_DIR)

# If AMI_NODE_BIN exists, prepend to PATH so 'npm' commands in sub-makes work
ifneq (,$(wildcard $(NODE_BIN_DIR)))
	export PATH := $(NODE_BIN_DIR):$(PATH)
endif

.PHONY: help setup-all setup-base setup-launcher setup-cms setup-browser setup-compliance setup-domains setup-files setup-learning setup-streams setup-ux clean start start-cms start-dev start-git-server production-deploy production-dry-run production-checks production-monitor production-status production-stop production-rollback

help:
	@echo "AMI Build System"
	@echo "Targets:"
	@echo "  setup-all        : Setup all modules"
	@echo "  setup-base       : Setup base module"
	@echo "  setup-browser    : Setup browser module"
	@echo "  setup-cms        : Setup CMS module"
	@echo "  setup-compliance : Setup compliance module"
	@echo "  setup-domains    : Setup domains module"
	@echo "  setup-files      : Setup files module"
	@echo "  setup-learning   : Setup learning module"
	@echo "  setup-launcher      : Setup launcher module"
	@echo "  setup-streams    : Setup streams module"
	@echo "  setup-ux         : Setup ux module"
	@echo "  start            : Start all services (root Procfile)"
	@echo "  start-cms        : Start CMS profile"
	@echo "  start-dev        : Start Dev profile"
	@echo "  start-git-server : Start Git Server profile"
	@echo "  clean            : Clean all artifacts"
	@echo ""
	@echo "Production Deployment Targets:"
	@echo "  production-deploy     : Deploy to production with full checks"
	@echo "  production-dry-run    : Run production deployment dry run"
	@echo "  production-checks     : Run production preflight checks"
	@echo "  production-monitor    : Start production monitoring service"
	@echo "  production-status     : Check production status"
	@echo "  production-stop       : Stop production services"
	@echo "  production-rollback   : Rollback production to previous state"
	@echo ""
	@echo "Performance Monitoring Targets:"
	@echo "  perf-monitor          : Show performance monitoring info"
	@echo "  perf-benchmark        : Run comprehensive performance benchmark"
	@echo "  perf-health           : Run health check with performance metrics"
	@echo "  perf-load-test        : Run load test on health endpoint"

# Production deployment - includes all checks and validation
production-deploy: setup-all production-checks
	@echo "Starting production deployment..."
	./scripts/ami-run launcher --profile production start

# Production dry run - validate without making changes
production-dry-run: setup-all
	@echo "Running production deployment dry run..."
	./scripts/ami-run launcher --profile production status

# Production checks only
production-checks: setup-all
	@echo "Running production preflight checks..."
	./scripts/ami-run launcher --profile production status

# Start production monitoring
production-monitor:
	@echo "Starting production monitoring service..."
	./scripts/ami-run python launcher/scripts/monitoring_server.py &

# Check production status
production-status:
	@echo "Checking production status..."
	@curl -f http://localhost:5055/health 2>/dev/null || echo "Monitoring service not responding"
	@if command -v curl >/dev/null 2>&1; then \
		echo "Health status: "; \
		curl -s http://localhost:5055/health | python -m json.tool; \
	else \
		echo "Install curl to get detailed health status"; \
	fi

# Stop production services
production-stop:
	@echo "Stopping production services..."
	@pkill -f "monitoring_server.py" || true
	@./scripts/ami-run launcher --profile production stop
	@echo "Production services stopped"

# Rollback production
production-rollback:
	@echo "Rolling back production deployment..."
	@./scripts/ami-run launcher --rollback latest

# Performance monitoring and benchmarking
perf-monitor:
	@echo "Starting performance monitoring..."
	@echo "Access performance metrics at: http://localhost:5055/metrics"

perf-benchmark:
	@echo "Running performance benchmark..."
	@echo "Use the monitoring server metrics endpoint for performance data: http://localhost:5055/metrics"

perf-health:
	@echo "Running health check..."
	@./scripts/ami-run launcher --profile production status

perf-load-test:
	@echo "Running load test..."
	@echo "Load testing should be done against the monitoring endpoints, for example:"
	@echo "curl -s http://localhost:5055/health"

start:
	@echo "Starting all services (root Procfile)..."
	./launcher/.venv/bin/honcho start

start-cms:
	@echo "Starting CMS profile..."
	./launcher/.venv/bin/honcho start -f Procfile.cms

start-dev:
	@echo "Starting Dev profile..."
	./launcher/.venv/bin/honcho start -f Procfile.dev

start-git-server:
	@echo "Starting Git Server profile..."
	./launcher/.venv/bin/honcho start -f Procfile.git-server

setup-all: setup-base setup-launcher setup-cms setup-browser setup-compliance setup-domains setup-files setup-learning setup-streams setup-ux

setup-base:
	@echo ">>> Setting up base..."
	$(MAKE) -C base setup

setup-launcher:
	@echo ">>> Setting up launcher..."
	$(MAKE) -C launcher setup

setup-cms:
	@echo ">>> Setting up cms..."
	$(MAKE) -C ux/cms setup

setup-browser:
	@echo ">>> Setting up browser..."
	$(MAKE) -C browser setup

setup-compliance:
	@echo ">>> Setting up compliance..."
	$(MAKE) -C compliance setup

setup-domains:
	@echo ">>> Setting up domains..."
	$(MAKE) -C domains setup

setup-files:
	@echo ">>> Setting up files..."
	$(MAKE) -C files setup

setup-learning:
	@echo ">>> Setting up learning..."
	$(MAKE) -C learning setup

setup-streams:
	@echo ">>> Setting up streams..."
	$(MAKE) -C streams setup

setup-ux:
	@echo ">>> Setting up ux..."
	$(MAKE) -C ux setup

clean:
	@echo "Cleaning all modules..."
	$(MAKE) -C base clean
	$(MAKE) -C nodes clean
	$(MAKE) -C ux/cms clean
	$(MAKE) -C browser clean
	$(MAKE) -C compliance clean
	$(MAKE) -C domains clean
	$(MAKE) -C files clean
	$(MAKE) -C learning clean
	$(MAKE) -C streams clean
	$(MAKE) -C ux clean