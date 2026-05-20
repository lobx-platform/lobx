#!/bin/bash

MODE=${1:-dev}

if [ "$MODE" = "dev" ]; then
    echo "🚀 starting in LOCAL DEV mode (both in Docker)..."
    
    # stop containers
    docker compose down
    
    # start backend and frontend
    docker compose up -d back front
    
    echo ""
    echo "✅ backend running at http://localhost:8000"
    echo "✅ frontend running at http://localhost:3000"
    echo "📝 view logs: docker compose logs -f"
    echo "🛑 stop: docker compose down"

elif [ "$MODE" = "dev_stop" ]; then
    echo "🛑 stopping LOCAL DEV services..."
    
    # Stop docker containers
    docker compose down
    
    echo "✅ stopped all services"

elif [ "$MODE" = "prod" ]; then
    echo "🚀 starting in PRODUCTION mode..."
    
    docker compose down
    docker compose build back front-deploy
    docker compose up -d back ngrok
    docker compose up front-deploy
    
    echo ""
    echo "✅ production running"
    echo "  backend: http://localhost:8000"
    echo "  public:  https://dthinkr.ngrok.app"
    echo "  frontend: https://london-trader.web.app"
    echo "📝 view logs: docker compose logs -f"
    
elif [ "$MODE" = "batch" ]; then
    # Usage: ./run.sh batch [sessions] [duration] [key=value ...]
    # Examples:
    #   ./run.sh batch 5 60                              # 5 sessions, 60s each
    #   ./run.sh batch 10 30 num_noise_traders=3         # with 3 noise traders
    #   ./run.sh batch 5 60 num_manipulator_traders=2 num_spoofing_traders=1
    # Any setting from back/core/data_models.py TradingParameters works
    echo "🔬 starting BATCH EXPERIMENT mode..."
    
    NUM_SESSIONS=${2:-5}
    DURATION=${3:-60}
    
    if ! curl -s http://localhost:8000/admin/get_base_settings > /dev/null 2>&1; then
        echo "❌ backend not running. start with: ./run.sh dev"
        exit 1
    fi
    
    echo "✅ backend detected"
    
    SETTINGS="{\"predefined_goals\": [0], \"trading_day_duration\": $DURATION"
    shift 3 2>/dev/null || shift $#
    for arg in "$@"; do
        key="${arg%%=*}"
        val="${arg#*=}"
        if [[ "$val" =~ ^[0-9]+$ ]]; then
            SETTINGS="$SETTINGS, \"$key\": $val"
        elif [[ "$val" =~ ^[0-9]+\.[0-9]+$ ]]; then
            SETTINGS="$SETTINGS, \"$key\": $val"
        else
            SETTINGS="$SETTINGS, \"$key\": \"$val\""
        fi
        echo "  setting: $key=$val"
    done
    SETTINGS="$SETTINGS}"
    
    curl -s -X POST "http://localhost:8000/admin/update_base_settings" \
        -H "Content-Type: application/json" \
        -d "{\"settings\": $SETTINGS}" > /dev/null
    
    echo "🚀 running $NUM_SESSIONS sessions ($DURATION seconds each)..."
    
    for i in $(seq 1 $NUM_SESSIONS); do
        echo "  session $i/$NUM_SESSIONS"
        curl -s -X POST "http://localhost:8000/user/login?PROLIFIC_PID=batch_$i&STUDY_ID=batch&SESSION_ID=s$i" \
            -H "Content-Type: application/json" \
            -d '{"username": "user1", "password": "password1"}' > /dev/null
        curl -s -X POST "http://localhost:8000/trading/start?PROLIFIC_PID=batch_$i&STUDY_ID=batch&SESSION_ID=s$i" \
            -H "Content-Type: application/json" \
            -d '{"username": "user1", "password": "password1"}' > /dev/null
        sleep $((DURATION + 5))
    done
    
    echo ""
    echo "✅ batch complete - logs in back/logs/"
    docker compose exec back ls -la logs/ | tail -$((NUM_SESSIONS + 2))

elif [ "$MODE" = "deploy" ]; then
    set -e
    DEPLOY_BRANCH=${DEPLOY_BRANCH:-main}
    echo "🚀 deploying from origin/${DEPLOY_BRANCH}..."
    
    git fetch origin "$DEPLOY_BRANCH"
    git reset --hard "origin/${DEPLOY_BRANCH}"
    
    docker compose down
    docker compose pull || echo "⚠️  no remote images, using local build"
    docker compose up -d
    
    echo ""
    echo "✅ deployment complete"
    echo "  backend: http://localhost:8000"
    docker compose ps
    
else
    echo "usage: sh run.sh [dev|dev_stop|prod|batch|deploy]"
    echo ""
    echo "  dev              - local development (backend + frontend)"
    echo "  dev_stop         - stop dev services"
    echo "  prod             - production with ngrok"
    echo "  batch [N] [SEC] [key=val...]  - run N experiments with custom settings"
    echo "  deploy           - pull latest & restart containers"
    exit 1
fi
