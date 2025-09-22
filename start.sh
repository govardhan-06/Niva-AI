#!/bin/bash

APP_NAME="niva_ai_backend"
FILE_PATH="docker-compose.yml"

function cleanup {
  docker-compose -f ${FILE_PATH} down
  CONTAINER_ID=$(docker ps -a -q -f name=${APP_NAME})
  if [ -n "${CONTAINER_ID}" ]; then
    # Remove the existing container
    docker rm -f ${CONTAINER_ID}
  fi
}

trap cleanup EXIT
cleanup

# Build all services
docker-compose -f ${FILE_PATH} build

# Run the main service with service ports
docker-compose -f ${FILE_PATH} run \
  --name ${APP_NAME} \
  --service-ports \
  main

# Exit with the status of the last command
exit $?
