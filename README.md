# queue-guard



## .env содержит

    APP_MODE=dev
    APP_HOST=0.0.0.0
    APP_PORT=8000
    APP_DEBUG_HOST=0.0.0.0
    APP_DEBUG_PORT=5678
    APP_WORKERS_NUM=2
    APP_ACCESS_KEY=123
    APP_PREFIX=/some/prefix
    APP_LOGS_HOST_PATH=./logs/app
    APP_LOGS_CONTR_PATH=/usr/src/logs/app
    APP_MODEL_NAME="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


    REDIS_HOSTNAME=redis
    REDIS_PORT=6379
    REDIS_DATABASE=4
    
    LLM_GLOBAL_SEM_REDIS_DSN=${REDIS_DSN}
    LLM_GLOBAL_SEM_KEY=llm:{global}:sem
    LLM_GLOBAL_SEM_LIMIT=2
    LLM_GLOBAL_SEM_TTL_MS=120000
    LLM_GLOBAL_SEM_WAIT_TIMEOUT_MS=30000
    LLM_GLOBAL_SEM_HEARTBEAT_MS=30000
    
    # === Очередь LLM (для отложенной генерации, если нет слота семафора) ===
    LLM_QUEUE_LIST_KEY=llm:queue:list
    LLM_TICKET_HASH_PREFIX=llm:ticket:
    LLM_QUEUE_MAX_SIZE=100
    LLM_QUEUE_TICKET_TTL=3600
    LLM_QUEUE_DRAIN_INTERVAL_SEC=1