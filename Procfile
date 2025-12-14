# Procfile - Root orchestration
# Run with: honcho start

data-stack: docker-compose -f docker-compose.data.yml up
integration-mongo: docker-compose -f docker-compose.yml up
openbao: COMPOSE_PROFILES=openbao OPENBAO_DEV_ROOT_TOKEN_ID=${OPENBAO_DEV_ROOT_TOKEN_ID} OPENBAO_PORT=8200 docker-compose -f docker-compose.secrets.yml up
secrets-broker: cd base && SECRETS_BROKER_HOST=0.0.0.0 SECRETS_BROKER_PORT=8700 ../scripts/ami-uv run --python 3.12 scripts/run_secrets_broker.py
searxng: COMPOSE_PROFILES=searxng SEARXNG_PORT=8888 SEARXNG_SECRET=change-me SEARXNG_LIMITER=true docker-compose -f docker-compose.services.yml up
cms: cd ux/cms && NODE_ENV=development npm run dev
git-sshd: SSH_PORT=2222 .venv/bin/sshd-venv start
git-daemon: GIT_EXEC_PATH=.venv/git/libexec/git-core GIT_DAEMON_PORT=9418 bash -c 'BASE_PATH="${GIT_SERVER_BASE_PATH:-$HOME/git-repos}"; exec .venv/bin/git daemon --reuseaddr --base-path="$BASE_PATH/repos" --export-all --enable=receive-pack --verbose "$BASE_PATH/repos"'
