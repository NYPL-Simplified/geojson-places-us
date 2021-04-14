.PHONY: help run clean
.DEFAULT_GOAL := help

help:
	@echo "Usage: make [COMMAND]"
	@echo ""
	@echo "Commands:"
	@echo ""
	@echo "    run    - Build the container and generate the places file"
	@echo "             in docker-output/us-places.ndjson."
	@echo "    clean  - Remove the Docker image"

build:
	docker build -t usplaces-builder:latest .

run: build
	docker run --rm --volume "$$(pwd)":/places usplaces-builder:latest

clean:
	IMAGE_ID=$$(docker image ls usplaces-builder:latest -q) && docker image rm $$IMAGE_ID
